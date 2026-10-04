import asyncio
import datetime
import logging
import os
from dataclasses import dataclass, field

import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from .. import alertas as alertas_repo
from .. import bitacora, ciclo_vida, configuracion, consultas, permisos, simulacion
from ..agentes import (
    ALERTS_PER_DAY,
    STATUS_A_ESTADO,
    absorbed_alert,
    detalle_de_consulta,
    earlier_of,
    etiqueta,
    metricas_del_dia,
    nombre,
    get_context,
    get_orchestrator,
    merged_summary,
    state_to_alert,
    status_path,
    with_thresholds,
)
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import ActorAgent, AdvanceEnd, AgentStep, Alert, Persona, SimulatedDay
from ..sse import flujo

from centinela_agents.day import AlertFailed, AlertRun, Step, Verdict

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


def _absorber(conn, alerta: Alert, absorbidas, day_str: str, dia: datetime.date) -> tuple[Alert, list[Alert]]:
    unidas: list[Alert] = []
    for otra, deteccion in absorbidas.items():
        ciclo_vida.transicionar("new", "merged")
        unida = alertas_repo.guardar(conn, absorbed_alert(otra, deteccion, alerta.id, day_str))
        alertas_repo.fijar_entidad(conn, otra, deteccion.entity)
        consultas.registrar(conn, [dict(deteccion.query)] if deteccion.query else [])
        bitacora.registrar(
            conn, unida.id, "alert", ANALISTA,
            f"Unida a la alerta {nombre(alerta)}: la misma causa. {unida.title.text}",
            dia, unida.pesos_at_risk.query_id, unida.title.figures,
        )
        unidas.append(unida)
    if unidas:
        alerta = alertas_repo.guardar(conn, alerta.model_copy(update={"merged_alerts": [*alerta.merged_alerts, *map(merged_summary, unidas)]}))
    return alerta, unidas


def _sujeto(metric: str, entity) -> str:
    return " · ".join([etiqueta(metric), *map(str, entity)])


def _siguiente(dia_en_curso, veredicto: Verdict | None):
    try:
        return dia_en_curso.send(veredicto)
    except StopIteration:
        return None


def _ahora() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _paso(paso: Step, inicios: dict) -> AgentStep:
    clave = (paso.alert_id, paso.node)
    if paso.status == "running":
        inicios[clave] = _ahora()
    inicio = inicios.pop(clave, None) if paso.status == "done" else inicios[clave]
    return AgentStep(
        alert_id=paso.alert_id,
        agent=paso.agent,
        node=paso.node,
        status=paso.status,
        description=f"{paso.description} de {_sujeto(paso.metric, paso.entity)}",
        start=inicio or _ahora(),
        end=_ahora() if paso.status == "done" else None,
    )


@dataclass
class Registro:
    veredicto: Verdict
    alerta: Alert | None = None
    destino: Alert | None = None
    unidas: list[Alert] = field(default_factory=list)
    nota: str = ""


def _registrar(conn, corrida: AlertRun, dia: datetime.date, day_str: str, nota: str) -> Registro:
    alert_id, state, detection = corrida.alert_id, dict(corrida.state), corrida.detection
    try:
        ciclo_vida.recorrer(status_path(alert_id, state))
    except ciclo_vida.TransicionInvalida as error:
        logger.warning("The run of %s proposes %s, which the lifecycle refuses: %s", alert_id, status_path(alert_id, state), error)
        return Registro(Verdict(recorded=False))
    alerta = state_to_alert(alert_id, state, detection, day_str)
    with conn.transaction():
        destino, unidas = None, []
        if alerta.status == "merged":
            destino = _unir(conn, alerta, dia, nota)
            if destino is None:
                actual = alertas_repo.obtener(conn, alerta.merged_into)
                estado = STATUS_A_ESTADO.get(actual.status, actual.status) if actual else "inexistente"
                logger.warning("Merge of %s into %s refused: the target is %s; the alert runs again without it", alert_id, alerta.merged_into, estado)
                return Registro(Verdict(recorded=False, refused_merge=alerta.merged_into), nota=f" No se unió a la alerta {nombre(actual) if actual else alerta.merged_into}, que está {estado}.")
        else:
            alerta = alertas_repo.guardar(conn, alerta)
            bitacora.registrar(conn, alert_id, "alert", VIGIA, f"Alerta detectada: {alerta.title.text}{nota}", dia, alerta.pesos_at_risk.query_id, alerta.title.figures)
            alerta, unidas = _absorber(conn, alerta, corrida.absorbed, day_str, dia)
        alertas_repo.fijar_entidad(conn, alert_id, detection.entity)
        alertas_repo.fijar_costo(conn, alert_id, state.get("cost") or {})
        bitacora.registrar_prompts(conn, alert_id, state.get("prompts") or [], dia)
        consultas.registrar(conn, state.get("queries") or [])
        for query in state.get("queries") or []:
            bitacora.registrar(conn, alert_id, "evidence", ANALISTA, detalle_de_consulta(query), dia, query["queryId"])
    return Registro(Verdict(recorded=True, absorbed=tuple(unida.id for unida in unidas)), alerta, destino, unidas)


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
                anteriores = alertas_repo.anteriores(conn)
            umbrales = configuracion.umbrales(ajustes)
            ctx = with_thresholds(get_context(), umbrales)
            orq = get_orchestrator()
            orq.use_thresholds(umbrales)
            dia_en_curso = orq.run_day(
                ctx, day_str,
                earlier=[earlier_of(alerta, entidad) for alerta, entidad in anteriores],
                watched=metricas_del_dia(ajustes),
                limit=int(os.environ.get(ALERTS_PER_DAY, "3")),
            )
            veredicto: Verdict | None = None
            notas: dict[str, str] = {}
            inicios: dict = {}
            while True:
                evento = await asyncio.to_thread(_siguiente, dia_en_curso, veredicto)
                if evento is None:
                    break
                veredicto = None
                if isinstance(evento, Step):
                    yield "step", _paso(evento, inicios)
                    continue
                sujeto = _sujeto(evento.detection.metric, evento.detection.entity)
                if isinstance(evento, AlertFailed):
                    yield "step", AgentStep(alert_id=evento.alert_id, agent="vigia", status="done", description=f"El análisis de {sujeto} no terminó.", start=_ahora(), end=_ahora())
                    continue
                try:
                    registro = _registrar(conn, evento, nuevo_dia, day_str, notas.get(evento.alert_id, ""))
                except Exception as error:
                    logger.error("Recording %s failed: %s", evento.alert_id, error, exc_info=True)
                    registro = Registro(Verdict(recorded=False))
                veredicto = registro.veredicto
                if veredicto.refused_merge is not None:
                    notas[evento.alert_id] = notas.get(evento.alert_id, "") + registro.nota
                    continue
                if registro.alerta is None:
                    yield "step", AgentStep(alert_id=evento.alert_id, agent="vigia", status="done", description=f"El análisis de {sujeto} no terminó.", start=_ahora(), end=_ahora())
                    continue
                if registro.alerta.status in UNIBLES:
                    new_alert_ids.append(evento.alert_id)
                for otra in (registro.alerta, registro.destino, *registro.unidas):
                    if otra is not None:
                        yield "alert", permisos.vista_con(ajustes, persona, otra)
                yield "step", AgentStep(alert_id=evento.alert_id, agent="estratega", status="done", description=_paso_final(registro.alerta, registro.destino), start=_ahora(), end=_ahora())

        except Exception as e:
            logger.error(f"Detection phase failed: {e}", exc_info=True)

        yield "end", AdvanceEnd(simulated_day=day_str, new_alerts=new_alert_ids)

    cierre = BackgroundTasks()
    cierre.add_task(release)
    return StreamingResponse(flujo(eventos()), media_type="text/event-stream", background=cierre)
