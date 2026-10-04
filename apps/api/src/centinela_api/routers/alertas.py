import asyncio
import logging
import uuid
from typing import Annotated
from urllib.parse import unquote

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from centinela_agents import query_registry

from .. import alertas as alertas_repo
from .. import bitacora, ciclo_vida, decisiones, simulacion
from ..agentes import get_orchestrator
from ..ciclo_vida import ESTADO_A_STATUS
from ..config import ROLES_CON_DECISION
from ..db import obtener_conexion
from ..modelos import (
    ActorAgent,
    ActorPerson,
    Alert,
    AlertEstadoEnum,
    Decision,
    DecisionApprove,
    DecisionEdit,
    DecisionReject,
    ExecutedAction,
)

router = APIRouter(tags=["alerts"])
logger = logging.getLogger(__name__)


@router.get("/alertas", response_model=list[Alert])
async def listar(
    estado: Annotated[AlertEstadoEnum | None, Query(description="Filter by alert estado (Spanish name for status)")] = None,
    conn: psycopg.Connection = Depends(obtener_conexion)
) -> list[Alert]:
    """
    List all alerts, optionally filtered by estado.

    Valid valores: nueva, en_analisis, propuesta, aprobada, rechazada, ejecutada
    """
    status = None
    if estado is not None:
        status = ESTADO_A_STATUS.get(estado)
        if status is None:
            raise HTTPException(422, f"estado desconocido: {estado}")
    return alertas_repo.listar(conn, status)


@router.get("/alertas/{id}", response_model=Alert)
async def obtener(id: str, conn: psycopg.Connection = Depends(obtener_conexion)) -> Alert:
    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "No existe esa alerta")
    return alerta


@router.post("/alertas/{id}/decision", response_model=Alert)
async def decidir(
    id: str,
    decision: Decision,
    x_user_name: str = Header(...),
    x_user_role: str = Header(...),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> Alert:
    if x_user_role not in ROLES_CON_DECISION:
        raise HTTPException(403, "Este rol no puede decidir sobre una alerta")
    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "No existe esa alerta")

    try:
        nueva, eventos = decisiones.aplicar(alerta, decision)
    except decisiones.ConflictoEstado as e:
        raise HTTPException(409, str(e)) from e
    except decisiones.DecisionInvalida as e:
        raise HTTPException(422, str(e)) from e

    actor = ActorPerson(name=unquote(x_user_name), role=x_user_role)
    dia = simulacion.dia_actual(conn)

    with conn.transaction():
        alertas_repo.guardar(conn, nueva)
        for tipo, detalle in eventos:
            bitacora.registrar(conn, nueva.id, tipo, actor, detalle, dia)

    if isinstance(decision, (DecisionApprove, DecisionEdit)):
        try:
            orq = get_orchestrator()
            orch_decision: dict = {
                "id": f"dec_{uuid.uuid4().hex[:8]}",
                "kind": decision.kind,
                "actionId": decision.action_id,
                "simulated_day": dia.isoformat(),
            }
            if isinstance(decision, DecisionEdit):
                orch_decision["parameters"] = decision.parameters

            state = await asyncio.to_thread(orq.resume, id, orch_decision)

            ea = state.get("executed_action")
            if ea and isinstance(ea, dict):
                ciclo_vida.transicionar(nueva.status, "executed")
                nueva = nueva.model_copy(update={
                    "status": "executed",
                    "executed_action": ExecutedAction(
                        action_id=ea.get("actionId") or ea.get("action_id") or "",
                        result=str(ea.get("result") or ""),
                    ),
                })
                with conn.transaction():
                    alertas_repo.guardar(conn, nueva)
                    bitacora.registrar(
                        conn, nueva.id, "result",
                        ActorAgent(agent="ejecutor"),
                        f"Acción ejecutada: {nueva.executed_action.result}",
                        dia,
                    )

        except Exception as e:
            logger.error(f"Orchestrator resume failed for {id}: {e}", exc_info=True)
            with conn.transaction():
                bitacora.registrar(
                    conn, nueva.id, "result",
                    ActorAgent(agent="ejecutor"),
                    f"La acción aprobada no se ejecutó: {e}",
                    dia,
                )

    elif isinstance(decision, DecisionReject):
        try:
            orq = get_orchestrator()
            await asyncio.to_thread(orq.resume, id, {
                "id": f"dec_{uuid.uuid4().hex[:8]}",
                "kind": "reject",
                "reason": decision.reason,
                "simulated_day": dia.isoformat(),
            })
        except Exception as e:
            logger.error(f"Orchestrator reject failed for {id}: {e}", exc_info=True)

    return nueva


@router.get("/queries/{id}")
async def obtener_query(id: str, conn: psycopg.Connection = Depends(obtener_conexion)):
    """
    Return query metadata + data rows for figure traceability ("Ver de dónde sale").
    """
    # Summary IDs are computed dynamically from the current alerts
    if id in ("q-summary-risk", "q-summary-pending", "q-summary-recoverable"):
        alerts = alertas_repo.listar(conn, "proposed")
        if id == "q-summary-risk":
            rows = [
                {"id": a.id, "metric": a.metric, "title": a.title.text,
                 "pesos_at_risk": a.pesos_at_risk.value}
                for a in alerts
            ]
            desc = (
                f"Suma de pesos en riesgo de {len(alerts)} alerta{'s' if len(alerts) != 1 else ''} "
                "pendientes de decisión."
            )
            sql = "SELECT id, cuerpo->>'metric' AS metric, cuerpo->'title'->>'text' AS title, (cuerpo->'pesosAtRisk'->>'value')::numeric AS pesos_at_risk FROM api.alertas WHERE status = 'proposed'"
        elif id == "q-summary-pending":
            rows = [
                {"id": a.id, "metric": a.metric, "status": a.status,
                 "title": a.title.text}
                for a in alerts
            ]
            desc = (
                f"{len(alerts)} alerta{'s' if len(alerts) != 1 else ''} "
                "esperan tu aprobación o rechazo."
            )
            sql = "SELECT id, cuerpo->>'metric' AS metric, status, cuerpo->'title'->>'text' AS title FROM api.alertas WHERE status = 'proposed'"
        else:  # q-summary-recoverable
            rows = [
                {"id": a.id, "metric": a.metric, "title": a.title.text,
                 "recoverable_per_month": a.recoverable_per_month.value}
                for a in alerts
                if a.recoverable_per_month
            ]
            desc = (
                "Suma del potencial de recuperación mensual de las alertas pendientes, "
                "si se aprueban todas las acciones propuestas."
            )
            sql = "SELECT id, cuerpo->>'metric' AS metric, cuerpo->'title'->>'text' AS title, (cuerpo->'recoverablePerMonth'->>'value')::numeric AS recoverable_per_month FROM api.alertas WHERE status = 'proposed' AND cuerpo->'recoverablePerMonth' IS NOT NULL"
        return {"id": id, "source": "alertas", "sql": sql, "description": desc, "rows": rows}

    record = query_registry.get(id)
    if record is None:
        raise HTTPException(
            404,
            f"Consulta '{id}' no encontrada. Es posible que el servidor haya reiniciado.",
        )
    return {
        "id": record.id,
        "source": record.source,
        "sql": record.sql,
        "description": record.description,
        "rows": record.rows,
    }
