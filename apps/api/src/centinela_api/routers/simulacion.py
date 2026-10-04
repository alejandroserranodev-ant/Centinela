import asyncio
import datetime
import logging

import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from .. import alertas as alertas_repo
from .. import bitacora, ciclo_vida, configuracion, consultas, simulacion
from ..agentes import (
    STATUS_A_ESTADO,
    absorbed_alert,
    alert_id_of,
    brief_of_alert,
    brief_of_detection,
    get_context,
    get_orchestrator,
    merged_summary,
    prioritized,
    state_to_alert,
    status_path,
    with_thresholds,
)
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import ActorAgent, AdvanceEnd, AgentStep, Alert, SimulatedDay
from ..sse import flujo

from centinela_agents.walk import detect

router = APIRouter(dependencies=[Depends(persona_actual)])
logger = logging.getLogger(__name__)

day_run = asyncio.Lock()
UNIBLES = frozenset({"new", "analyzing", "proposed"})
VIGIA = ActorAgent(agent="vigia")
ANALISTA = ActorAgent(agent="analista")


def _unir(conn: psycopg.Connection, alerta: Alert, dia: datetime.date) -> tuple[Alert, Alert | None]:
    destino = alertas_repo.obtener(conn, alerta.merged_into, bloquear=True)
    if destino is None or destino.status not in UNIBLES:
        estado = destino.status if destino else "inexistente"
        logger.warning("Merge of %s into %s refused: the target is %s", alerta.id, alerta.merged_into, estado)
        propia = alerta.model_copy(update={"status": "analyzing", "merged_into": None})
        alertas_repo.guardar(conn, propia)
        bitacora.registrar(
            conn, propia.id, "alert", ANALISTA,
            f"Alerta detectada: {propia.title.text}. No se unió a la alerta {alerta.merged_into}, que está {estado}",
            dia, propia.pesos_at_risk.query_id,
        )
        return propia, None
    alertas_repo.guardar(conn, alerta)
    destino = destino.model_copy(update={"merged_alerts": [*destino.merged_alerts, merged_summary(alerta)]})
    alertas_repo.guardar(conn, destino)
    bitacora.registrar(
        conn, alerta.id, "alert", ANALISTA,
        f"Unida a la alerta {destino.id}: la misma causa. {alerta.title.text}",
        dia, alerta.pesos_at_risk.query_id,
    )
    return alerta, destino


def _absorber(conn, alerta: Alert, nombradas: list[str], pendientes: dict, day_str: str, dia: datetime.date) -> tuple[Alert, list[Alert]]:
    unidas: list[Alert] = []
    for otra in nombradas:
        if otra in pendientes:
            unida = absorbed_alert(otra, pendientes.pop(otra), alerta.id, day_str)
        else:
            guardada = alertas_repo.obtener(conn, otra, bloquear=True)
            if guardada is None or guardada.status != "new":
                logger.warning("Absorption of %s into %s refused: it is no alert in new", otra, alerta.id)
                continue
            ciclo_vida.transicionar(guardada.status, "merged")
            unida = guardada.model_copy(update={"status": "merged", "merged_into": alerta.id})
        alertas_repo.guardar(conn, unida)
        bitacora.registrar(
            conn, unida.id, "alert", ANALISTA,
            f"Unida a la alerta {alerta.id}: la misma causa. {unida.title.text}",
            dia, unida.pesos_at_risk.query_id,
        )
        unidas.append(unida)
    if unidas:
        alerta = alerta.model_copy(update={"merged_alerts": [*alerta.merged_alerts, *map(merged_summary, unidas)]})
        alertas_repo.guardar(conn, alerta)
    return alerta, unidas


@router.get("/simulacion/dia-actual", response_model=SimulatedDay)
async def dia_actual(conn: psycopg.Connection = Depends(obtener_conexion)) -> SimulatedDay:
    """
    Get the current simulated day.
    Used by Vigía to know what date to filter queries by.
    """
    dia = simulacion.dia_actual(conn)
    return SimulatedDay(dia=dia.isoformat())


@router.post("/simulacion/avanzar")
async def avanzar(
    dias: int = Query(1, ge=1), conn: psycopg.Connection = Depends(obtener_conexion)
) -> StreamingResponse:
    if day_run.locked():
        raise HTTPException(status_code=409, detail="Ya hay un día en curso")
    await day_run.acquire()
    held = True

    def release() -> None:
        nonlocal held
        if held:
            held = False
            day_run.release()

    async def eventos():
        try:
            async for evento in corrida():
                yield evento
        finally:
            release()

    async def corrida():
        with conn.transaction():
            nuevo_dia = simulacion.avanzar(conn, dias)

        day_str = nuevo_dia.isoformat()
        new_alert_ids: list[str] = []

        try:
            with conn.transaction():
                ajustes = configuracion.leer(conn)
                known = alertas_repo.ids(conn)
                abiertas = alertas_repo.abiertas(conn)
            umbrales = configuracion.umbrales(ajustes)
            ctx = with_thresholds(get_context(), umbrales)
            detections = prioritized(detect(ctx, day_str), known, configuracion.vigiladas(ajustes))
            orq = get_orchestrator()
            orq.use_thresholds(umbrales)
            earlier = {a.id: STATUS_A_ESTADO[a.status] for a in abiertas}
            briefs = {a.id: brief_of_alert(a) for a in abiertas}
            pendientes = {alert_id_of(d): d for d in detections}

            for detection in detections:
                alert_id = alert_id_of(detection)
                if pendientes.pop(alert_id, None) is None:
                    continue

                inicio = datetime.datetime.now(datetime.UTC).isoformat()
                yield "step", AgentStep(
                    alert_id=alert_id,
                    agent="vigia",
                    status="running",
                    description=f"Detectada anomalía en {detection.metric}",
                    start=inicio,
                )

                try:
                    state = await asyncio.to_thread(
                        orq.start,
                        detection,
                        alert_id=alert_id,
                        day=day_str,
                        earlier_alerts={**earlier, **{otra: "nueva" for otra in pendientes}},
                        alert_briefs={**briefs, **{otra: brief_of_detection(d) for otra, d in pendientes.items()}},
                    )
                    alerta = state_to_alert(alert_id, state, detection, day_str)
                    ciclo_vida.recorrer(status_path(alert_id, state))

                    destino, unidas = None, []
                    with conn.transaction():
                        if alerta.status == "merged":
                            alerta, destino = _unir(conn, alerta, nuevo_dia)
                        else:
                            alertas_repo.guardar(conn, alerta)
                            bitacora.registrar(
                                conn, alert_id, "alert",
                                VIGIA,
                                f"Alerta detectada: {alerta.title.text}",
                                nuevo_dia,
                                alerta.pesos_at_risk.query_id,
                            )
                            alerta, unidas = _absorber(conn, alerta, list(state.get("merged_alerts") or []), pendientes, day_str, nuevo_dia)
                        consultas.registrar(conn, state.get("queries") or [])
                        for query in state.get("queries") or []:
                            bitacora.registrar(
                                conn, alert_id, "evidence",
                                ActorAgent(agent="analista"),
                                f"{query['kpi']} el {query['dia']}: {query['consulta']}",
                                nuevo_dia,
                                query["queryId"],
                            )

                    for unida in unidas:
                        earlier.pop(unida.id, None)
                        briefs.pop(unida.id, None)
                    if alerta.status in ciclo_vida.FINALES:
                        earlier.pop(alert_id, None)
                        briefs.pop(alert_id, None)
                    else:
                        earlier[alert_id] = STATUS_A_ESTADO[alerta.status]
                        briefs[alert_id] = brief_of_alert(alerta)
                    if alerta.status != "merged":
                        new_alert_ids.append(alert_id)

                    yield "alert", alerta
                    for otra in (destino, *unidas):
                        if otra is not None:
                            yield "alert", otra

                    yield "step", AgentStep(
                        alert_id=alert_id,
                        agent="estratega",
                        status="done",
                        description=(
                            f"Unida a la alerta {alerta.merged_into}: la misma causa."
                            if alerta.status == "merged"
                            else f"Propuestas {len(alerta.actions)} acción(es). Esperando decisión."
                            if alerta.actions
                            else "Procesado. Sin acciones automáticas."
                        ),
                        start=inicio,
                        end=datetime.datetime.now(datetime.UTC).isoformat(),
                    )

                except Exception as e:
                    logger.error(f"Error processing detection {alert_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Detection phase failed: {e}", exc_info=True)

        yield "end", AdvanceEnd(simulated_day=day_str, new_alerts=new_alert_ids)

    cierre = BackgroundTasks()
    cierre.add_task(release)
    return StreamingResponse(flujo(eventos()), media_type="text/event-stream", background=cierre)
