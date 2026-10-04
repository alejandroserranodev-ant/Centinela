import asyncio
import datetime
import logging

import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from .. import alertas as alertas_repo
from .. import bitacora, ciclo_vida, configuracion, consultas, permisos, simulacion
from ..agentes import (
    STATUS_A_ESTADO,
    absorbed_alert,
    detalle_de_consulta,
    etiqueta,
    alert_id_of,
    brief_of_alert,
    brief_of_detection,
    con_consulta,
    consulta_del_kpi,
    nombre,
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
from ..modelos import ActorAgent, AdvanceEnd, AgentStep, Alert, Persona, SimulatedDay
from ..sse import flujo

from centinela_agents.walk import detect

router = APIRouter(dependencies=[Depends(persona_actual)])
logger = logging.getLogger(__name__)

day_run = asyncio.Lock()
UNIBLES = frozenset({"proposed"})
VIGIA = ActorAgent(agent="vigia")
ANALISTA = ActorAgent(agent="analista")


def _unir(conn: psycopg.Connection, alerta: Alert, dia: datetime.date, nota: str) -> Alert | None:
    destino = alertas_repo.obtener(conn, alerta.merged_into, bloquear=True)
    if destino is None or destino.status not in UNIBLES:
        return None
    alerta = alertas_repo.guardar(conn, alerta)
    destino = alertas_repo.guardar(conn, destino.model_copy(update={"merged_alerts": [*destino.merged_alerts, merged_summary(alerta)]}))
    bitacora.registrar(
        conn, alerta.id, "alert", ANALISTA,
        f"Unida a la alerta {nombre(destino)}: la misma causa. {alerta.title.text}{nota}",
        dia, alerta.pesos_at_risk.query_id, alerta.title.figures,
    )
    return destino


def _absorber(conn, alerta: Alert, nombradas: dict[str, dict], pendientes: dict, day_str: str, dia: datetime.date) -> tuple[Alert, list[Alert]]:
    unidas: list[Alert] = []
    for otra, consulta in nombradas.items():
        if otra not in pendientes:
            logger.warning("Absorption of %s into %s refused: it is no detection of the day still to run", otra, alerta.id)
            continue
        ciclo_vida.transicionar("new", "merged")
        unida = alertas_repo.guardar(conn, absorbed_alert(otra, pendientes.pop(otra), alerta.id, day_str, consulta))
        consultas.registrar(conn, [consulta])
        bitacora.registrar(
            conn, unida.id, "alert", ANALISTA,
            f"Unida a la alerta {nombre(alerta)}: la misma causa. {unida.title.text}",
            dia, unida.pesos_at_risk.query_id, unida.title.figures,
        )
        unidas.append(unida)
    if unidas:
        alerta = alertas_repo.guardar(conn, alerta.model_copy(update={"merged_alerts": [*alerta.merged_alerts, *map(merged_summary, unidas)]}))
    return alerta, unidas


PASOS = {
    "vigia": "Detectada anomalía en {sujeto}",
    "analista": "Buscando la causa de {sujeto}",
    "estratega": "Proponiendo acciones para {sujeto}",
}


def _sujeto(detection) -> str:
    return " · ".join([etiqueta(detection.metric), *map(str, detection.entity)])


async def _con_pasos(llamada):
    cola: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    tarea = asyncio.ensure_future(asyncio.to_thread(llamada, lambda agente, nodo: loop.call_soon_threadsafe(cola.put_nowait, agente)))
    while True:
        espera = asyncio.ensure_future(cola.get())
        hechas, _ = await asyncio.wait({espera, tarea}, return_when=asyncio.FIRST_COMPLETED)
        if espera in hechas:
            yield "paso", espera.result()
            continue
        espera.cancel()
        while not cola.empty():
            yield "paso", cola.get_nowait()
        yield "estado", tarea.result()
        return


def _paso_final(alerta: Alert, destino: Alert | None) -> str:
    if alerta.status == "merged":
        return f"Unida a la alerta {nombre(destino) if destino else 'que queda'}: la misma causa."
    if alerta.actions:
        return f"Propuestas {len(alerta.actions)} acción(es). Esperando decisión."
    return "Procesado. Sin acciones automáticas."


@router.get("/simulacion/dia-actual", response_model=SimulatedDay)
async def dia_actual(conn: psycopg.Connection = Depends(obtener_conexion)) -> SimulatedDay:
    """
    Get the current simulated day.
    Used by Vigía to know what date to filter queries by.
    """
    dia = simulacion.dia_actual(conn)
    return SimulatedDay(dia=dia.isoformat(), ultimo_dia=simulacion.ultimo_dia(conn).isoformat())


@router.post("/simulacion/avanzar")
async def avanzar(
    dias: int = Query(1, ge=1),
    persona: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> StreamingResponse:
    if day_run.locked():
        raise HTTPException(status_code=409, detail="Ya hay un día en curso")
    motivo = simulacion.sin_datos(conn, dias)
    if motivo is not None:
        raise HTTPException(status_code=409, detail=motivo)
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
            earlier = {a.id: STATUS_A_ESTADO[a.status] for a in abiertas if a.status in UNIBLES}
            briefs = {a.id: brief_of_alert(a) for a in abiertas if a.status in UNIBLES}
            pendientes = {alert_id_of(d): d for d in detections}

            for detection in detections:
                alert_id = alert_id_of(detection)
                if pendientes.pop(alert_id, None) is None:
                    continue

                inicio = datetime.datetime.now(datetime.UTC).isoformat()
                sujeto = _sujeto(detection)
                agente = "vigia"
                yield "step", AgentStep(alert_id=alert_id, agent=agente, status="running", description=PASOS[agente].format(sujeto=sujeto), start=inicio)

                try:
                    excluidas: dict[str, tuple[str, str]] = {}
                    while True:
                        opciones = {
                            "alert_id": alert_id,
                            "day": day_str,
                            "earlier_alerts": {**earlier, **{otra: "nueva" for otra in pendientes}},
                            "alert_briefs": {**briefs, **{otra: brief_of_detection(d) for otra, d in pendientes.items()}},
                        }
                        async for tipo, valor in _con_pasos(lambda on_step: orq.start(detection, on_step=on_step, **opciones)):
                            if tipo == "estado":
                                state = valor
                            elif valor in PASOS and valor != agente:
                                agente = valor
                                yield "step", AgentStep(alert_id=alert_id, agent=agente, status="running", description=PASOS[agente].format(sujeto=sujeto), start=inicio)
                        state = await asyncio.to_thread(con_consulta, state, detection.metric, day_str)
                        nombradas = {
                            otra: await asyncio.to_thread(consulta_del_kpi, pendientes[otra].metric, day_str) if otra in pendientes else {}
                            for otra in state.get("merged_alerts") or []
                        }
                        alerta = state_to_alert(alert_id, state, detection, day_str)
                        ciclo_vida.recorrer(status_path(alert_id, state))
                        nota = "".join(f" No se unió a la alerta {otra}, que está {estado}." for otra, estado in excluidas.values())

                        destino, unidas = None, []
                        with conn.transaction():
                            if alerta.status == "merged":
                                destino = _unir(conn, alerta, nuevo_dia, nota)
                                if destino is None:
                                    actual = alertas_repo.obtener(conn, alerta.merged_into)
                                    estado = STATUS_A_ESTADO.get(actual.status, actual.status) if actual else "inexistente"
                                    excluidas[alerta.merged_into] = (nombre(actual) if actual else alerta.merged_into, estado)
                                    logger.warning("Merge of %s into %s refused: the target is %s; the alert runs again without it", alert_id, alerta.merged_into, estado)
                                    earlier.pop(alerta.merged_into, None)
                                    briefs.pop(alerta.merged_into, None)
                                    continue
                            else:
                                alerta = alertas_repo.guardar(conn, alerta)
                                bitacora.registrar(
                                    conn, alert_id, "alert",
                                    VIGIA,
                                    f"Alerta detectada: {alerta.title.text}{nota}",
                                    nuevo_dia,
                                    alerta.pesos_at_risk.query_id,
                                    alerta.title.figures,
                                )
                                alerta, unidas = _absorber(conn, alerta, nombradas, pendientes, day_str, nuevo_dia)
                            consultas.registrar(conn, state.get("queries") or [])
                            for query in state.get("queries") or []:
                                bitacora.registrar(
                                    conn, alert_id, "evidence",
                                    ActorAgent(agent="analista"),
                                    detalle_de_consulta(query),
                                    nuevo_dia,
                                    query["queryId"],
                                )
                        break

                    for unida in unidas:
                        earlier.pop(unida.id, None)
                        briefs.pop(unida.id, None)
                    if alerta.status in UNIBLES:
                        earlier[alert_id] = STATUS_A_ESTADO[alerta.status]
                        briefs[alert_id] = brief_of_alert(alerta)
                        new_alert_ids.append(alert_id)

                    for otra in (alerta, destino, *unidas):
                        if otra is not None:
                            yield "alert", permisos.vista_con(ajustes, persona, otra)

                    yield "step", AgentStep(
                        alert_id=alert_id,
                        agent="estratega",
                        status="done",
                        description=_paso_final(alerta, destino),
                        start=inicio,
                        end=datetime.datetime.now(datetime.UTC).isoformat(),
                    )

                except Exception as e:
                    logger.error(f"Error processing detection {alert_id}: {e}", exc_info=True)
                    yield "step", AgentStep(
                        alert_id=alert_id,
                        agent=agente,
                        status="done",
                        description=f"El análisis de {sujeto} no terminó.",
                        start=inicio,
                        end=datetime.datetime.now(datetime.UTC).isoformat(),
                    )

        except Exception as e:
            logger.error(f"Detection phase failed: {e}", exc_info=True)

        yield "end", AdvanceEnd(simulated_day=day_str, new_alerts=new_alert_ids)

    cierre = BackgroundTasks()
    cierre.add_task(release)
    return StreamingResponse(flujo(eventos()), media_type="text/event-stream", background=cierre)
