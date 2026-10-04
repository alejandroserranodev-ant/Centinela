import asyncio
import datetime
import logging
import uuid
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import alertas as alertas_repo
from .. import bitacora, ciclo_vida, configuracion, consultas, decisiones, permisos, simulacion
from ..agentes import converted_actions, detalle_de_consulta, get_orchestrator
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
    Settings,
    DecisionApprove,
    DecisionEdit,
    DecisionReject,
    DecisionRequestChanges,
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
    return permisos.vistas(conn, persona, alertas_repo.listar(conn, status))


@router.get("/alertas/{id}", response_model=Alert)
async def obtener(
    id: str,
    persona: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> Alert:
    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "No existe esa alerta")
    return permisos.vista(conn, persona, alerta)


EN_PAUSA = "El análisis de esta alerta ya no está en pausa: no puede reanudarse"
EN_CURSO = "Esta alerta está procesando otra decisión: espera a que termine"
NO_EJECUTADA = "La acción aprobada no se ejecutó"
EJECUTOR = ActorAgent(agent="ejecutor")
reanudando: set[str] = set()


def _en_pausa(id: str) -> bool:
    try:
        orq = get_orchestrator()
        if orq.is_awaiting_decision(id):
            return True
        # If InMemorySaver has no state for this alert (e.g. after an API restart), the
        # alert may still be proposed in the DB.  Let the decision proceed: the DB update
        # will go through and orq.resume() will fail gracefully inside its own try/except.
        return orq.has_no_graph_state(id)
    except Exception as e:
        logger.error(f"Orchestrator state unreadable for {id}: {e}", exc_info=True)
        return False


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
    if not permisos.puede_decidir(conn, persona, alerta):
        raise HTTPException(403, permisos.negada(conn, persona, alerta))
    if id in reanudando:
        raise HTTPException(409, EN_CURSO)
    reanudando.add(id)
    try:
        return await _decidir(alerta, decision, persona, conn)
    finally:
        reanudando.discard(id)


def _aplicar(alerta: Alert, decision: Decision, ajustes: Settings) -> tuple[Alert, list]:
    try:
        return decisiones.aplicar(alerta, decision, ajustes.autonomy)
    except decisiones.ConflictoEstado as e:
        raise HTTPException(409, str(e)) from e
    except decisiones.DecisionInvalida as e:
        raise HTTPException(422, str(e)) from e


def no_ejecutada(fin: str | None, dia: datetime.date) -> str:
    if fin == "fin.ya_no_aplica":
        return f"{NO_EJECUTADA}: el indicador ya no está fuera de su umbral el {dia.isoformat()}."
    return f"{NO_EJECUTADA}: falló su preparación, así que queda para hacerla a mano."


async def _decidir(alerta: Alert, decision: Decision, persona: Persona, conn: psycopg.Connection) -> Alert:
    id = alerta.id
    ajustes = configuracion.leer(conn)
    _aplicar(alerta, decision, ajustes)
    en_pausa = await asyncio.to_thread(_en_pausa, id)
    if not en_pausa and not isinstance(decision, DecisionReject):
        raise HTTPException(409, EN_PAUSA)

    actor = ActorPerson(name=persona.name, role=persona.role)
    with conn.transaction():
        dia = simulacion.dia_actual(conn)
        nueva, eventos = _aplicar(alertas_repo.obtener(conn, id, bloquear=True), decision, ajustes)
        nueva = alertas_repo.guardar(conn, nueva)
        for tipo, detalle in eventos:
            bitacora.registrar(conn, nueva.id, tipo, actor, detalle, dia)

    if isinstance(decision, (DecisionApprove, DecisionEdit)):
        try:
            orq = get_orchestrator()
            orq.use_thresholds(configuracion.umbrales(ajustes))
            orch_decision: dict = {
                "id": f"dec_{uuid.uuid4().hex[:8]}",
                "kind": decision.kind,
                "actionId": decision.action_id,
                "simulated_day": dia.isoformat(),
            }
            if isinstance(decision, DecisionEdit):
                aprobada = next(a for a in nueva.actions if a.id == decision.action_id)
                orch_decision["parameters"] = dict(aprobada.parameters)

            state = await asyncio.to_thread(orq.resume, id, orch_decision)
            with conn.transaction():
                bitacora.registrar_prompts(conn, id, state.get("resumed_prompts") or [], dia)

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
                    nueva = alertas_repo.guardar(conn, nueva)
                    bitacora.registrar(conn, nueva.id, "result", EJECUTOR, f"Acción ejecutada: {nueva.executed_action.result}", dia)
            else:
                logger.warning("Approved action of %s was not executed: %s %s", id, state.get("fin"), state.get("failures"))
                with conn.transaction():
                    bitacora.registrar(conn, nueva.id, "result", EJECUTOR, no_ejecutada(state.get("fin"), dia), dia)

        except Exception as e:
            logger.error(f"Orchestrator resume failed for {id}: {e}", exc_info=True)
            with conn.transaction():
                bitacora.registrar(conn, nueva.id, "result", EJECUTOR, no_ejecutada(None, dia), dia)

    elif isinstance(decision, DecisionReject):
        if en_pausa:
            try:
                orq = get_orchestrator()
                orq.use_thresholds(configuracion.umbrales(ajustes))
                state = await asyncio.to_thread(orq.resume, id, {
                    "id": f"dec_{uuid.uuid4().hex[:8]}",
                    "kind": "reject",
                    "reason": decision.reason,
                    "simulated_day": dia.isoformat(),
                })
                with conn.transaction():
                    bitacora.registrar_prompts(conn, id, state.get("resumed_prompts") or [], dia)
            except Exception as e:
                logger.error(f"Orchestrator reject failed for {id}: {e}", exc_info=True)

    elif isinstance(decision, DecisionRequestChanges):
        nueva = await _reproponer(conn, nueva, decision.reason, ajustes, dia)

    return permisos.vista(conn, persona, nueva)


def _sin_propuesta(
    conn: psycopg.Connection, orq, alerta: Alert, error: Exception, dia: datetime.date
) -> Alert:
    en_pausa = orq is not None and _en_pausa(alerta.id)
    sin_consumir = en_pausa and not orq.get_state(alerta.id).get("proposal_returns")
    detalle = (
        f"No hubo nueva propuesta tras la solicitud de cambios; se conservan las acciones anteriores: {error}"
        if en_pausa
        else f"No hubo nueva propuesta tras la solicitud de cambios y el análisis ya no está en pausa: solo queda rechazarla: {error}"
    )
    with conn.transaction():
        if sin_consumir:
            actual = alertas_repo.obtener(conn, alerta.id, bloquear=True)
            if actual is not None and actual.status == "proposed":
                alerta = alertas_repo.guardar(conn, actual.model_copy(update={"changes_requested": False}))
        bitacora.registrar(conn, alerta.id, "proposal", ActorAgent(agent="estratega"), detalle, dia)
    return alerta


async def _reproponer(
    conn: psycopg.Connection, alerta: Alert, motivo: str, ajustes: Settings, dia: datetime.date
) -> Alert:
    estratega = ActorAgent(agent="estratega")
    orq = None
    try:
        orq = get_orchestrator()
        orq.use_thresholds(configuracion.umbrales(ajustes))
        vistas = {q["queryId"] for q in orq.get_state(alerta.id).get("queries") or []}
        state = await asyncio.to_thread(orq.resume, alerta.id, {
            "id": f"dec_{uuid.uuid4().hex[:8]}",
            "kind": "request_changes",
            "reason": motivo.strip(),
            "simulated_day": dia.isoformat(),
        })
        with conn.transaction():
            bitacora.registrar_prompts(conn, alerta.id, state.get("resumed_prompts") or [], dia)
        acciones = converted_actions(state)
        if not acciones:
            raise ValueError("Estratega no devolvió acciones")
    except Exception as e:
        logger.error(f"Orchestrator request_changes failed for {alerta.id}: {e}", exc_info=True)
        return _sin_propuesta(conn, orq, alerta, e, dia)

    nuevas = [q for q in state.get("queries") or [] if q.get("queryId") not in vistas]
    with conn.transaction():
        actual = alertas_repo.obtener(conn, alerta.id, bloquear=True)
        if actual is None or actual.status != "proposed":
            logger.warning("New proposal for %s dropped: the alert is %s", alerta.id, actual.status if actual else "gone")
            return actual or alerta
        nueva = alertas_repo.guardar(conn, actual.model_copy(update={"actions": acciones}))
        bitacora.registrar(
            conn, nueva.id, "proposal", estratega,
            f"Nueva propuesta tras la solicitud de cambios: {len(acciones)} acción(es)",
            dia,
        )
        consultas.registrar(conn, nuevas)
        for query in nuevas:
            bitacora.registrar(
                conn, nueva.id, "evidence", ActorAgent(agent="analista"),
                detalle_de_consulta(query),
                dia, query["queryId"],
            )
    return nueva
