import asyncio
import logging
import uuid
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import alertas as alertas_repo
from .. import bitacora, ciclo_vida, decisiones, permisos, simulacion
from ..agentes import get_orchestrator
from ..ciclo_vida import ESTADO_A_STATUS
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import (
    ActorAgent,
    ActorPerson,
    Alert,
    AlertEstadoEnum,
    Decision,
    Persona,
    DecisionApprove,
    DecisionEdit,
    DecisionReject,
    ExecutedAction,
)

router = APIRouter(tags=["alerts"], dependencies=[Depends(persona_actual)])
logger = logging.getLogger(__name__)


@router.get("/alertas", response_model=list[Alert])
async def listar(
    estado: Annotated[AlertEstadoEnum | None, Query(description="Filter by alert estado (Spanish name for status)")] = None,
    persona: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
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
    return [permisos.vista(persona, a) for a in alertas_repo.listar(conn, status)]


@router.get("/alertas/{id}", response_model=Alert)
async def obtener(
    id: str,
    persona: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> Alert:
    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "No existe esa alerta")
    return permisos.vista(persona, alerta)


@router.post("/alertas/{id}/decision", response_model=Alert)
async def decidir(
    id: str,
    decision: Decision,
    persona: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> Alert:
    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "No existe esa alerta")
    if not permisos.puede_decidir(persona, alerta):
        raise HTTPException(403, permisos.negada(alerta))

    try:
        nueva, eventos = decisiones.aplicar(alerta, decision)
    except decisiones.ConflictoEstado as e:
        raise HTTPException(409, str(e)) from e
    except decisiones.DecisionInvalida as e:
        raise HTTPException(422, str(e)) from e

    actor = ActorPerson(name=persona.name, role=persona.role)
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

    return permisos.vista(persona, nueva)
