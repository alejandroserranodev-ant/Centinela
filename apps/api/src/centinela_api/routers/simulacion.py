import asyncio
import datetime
import logging

import psycopg
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from .. import alertas as alertas_repo
from .. import bitacora, ciclo_vida, consultas, simulacion
from ..agentes import alert_id_of, get_context, get_orchestrator, prioritized, state_to_alert, status_path
from ..db import obtener_conexion
from ..modelos import ActorAgent, AdvanceEnd, AgentStep, SimulatedDay
from ..sse import flujo

from centinela_agents.walk import detect

router = APIRouter()
logger = logging.getLogger(__name__)


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
    async def eventos():
        with conn.transaction():
            nuevo_dia = simulacion.avanzar(conn, dias)

        day_str = nuevo_dia.isoformat()
        new_alert_ids: list[str] = []

        try:
            ctx = get_context()
            with conn.transaction():
                known = alertas_repo.ids(conn)
            detections = prioritized(detect(ctx, day_str), known)
            orq = get_orchestrator()

            for detection in detections:
                alert_id = alert_id_of(detection)

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
                    )
                    alerta = state_to_alert(alert_id, state, detection, day_str)
                    ciclo_vida.recorrer(status_path(alert_id, state))

                    with conn.transaction():
                        alertas_repo.guardar(conn, alerta)
                        bitacora.registrar(
                            conn, alert_id, "alert",
                            ActorAgent(agent="vigia"),
                            f"Alerta detectada: {alerta.title.text}",
                            nuevo_dia,
                            alerta.pesos_at_risk.query_id,
                        )
                        consultas.registrar(conn, state.get("queries") or [])
                        for query in state.get("queries") or []:
                            bitacora.registrar(
                                conn, alert_id, "evidence",
                                ActorAgent(agent="analista"),
                                f"{query['kpi']} el {query['dia']}: {query['consulta']}",
                                nuevo_dia,
                                query["queryId"],
                            )

                    new_alert_ids.append(alert_id)

                    yield "step", AgentStep(
                        alert_id=alert_id,
                        agent="estratega",
                        status="done",
                        description=(
                            f"Propuestas {len(alerta.actions)} acción(es). Esperando decisión."
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

    return StreamingResponse(flujo(eventos()), media_type="text/event-stream")
