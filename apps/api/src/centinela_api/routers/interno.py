import datetime
import hmac
import uuid

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException

from .. import alertas as alertas_repo
from .. import bitacora, simulacion
from ..ciclo_vida import transicionar
from ..config import AGENT_SECRET_KEY
from ..db import obtener_conexion
from ..modelos import (
    ActorAgent,
    Agent,
    AgentAlertInput,
    AgentCauseInput,
    AgentExecutionInput,
    AgentProposalInput,
    Alert,
    CauseNoEvidence,
    CostoAgente,
)

router = APIRouter(prefix="/interno", tags=["internal"])


def validar_agente(x_agent_key: str = Header(...)) -> None:
    """Valida que la llamada venga de un agente autorizado."""
    if not hmac.compare_digest(x_agent_key.encode(), AGENT_SECRET_KEY.encode()):
        raise HTTPException(401, "Agente no autorizado")


@router.post("/alertas", response_model=Alert)
async def crear_alerta(
    entrada: AgentAlertInput,
    agente: str = Header(..., alias="X-Agent"),
    conn: psycopg.Connection = Depends(obtener_conexion),
    _: None = Depends(validar_agente),
) -> Alert:
    """
    Vigía crea una nueva alerta.
    La alerta nace en estado 'new' y entra inmediatamente en análisis por Analista.
    """
    if agente != "vigia":
        raise HTTPException(400, "Solo Vigía puede crear alertas")

    alerta_id = f"alerta_{uuid.uuid4().hex[:16]}"
    dia = simulacion.dia_actual(conn)

    nueva = Alert(
        id=alerta_id,
        status="new",
        severity=entrada.severity,
        metric=entrada.metric,
        title=entrada.title,
        pesos_at_risk=entrada.pesos_at_risk,
        recoverable_per_month=entrada.recoverable_per_month,
        confidence=entrada.confidence,
        simulated_date=entrada.simulated_date,
        cause=CauseNoEvidence(kind="no_evidence", reason="Awaiting analyst"),
        actions=[],
        executed_action=None,
    )

    with conn.transaction():
        alertas_repo.guardar(conn, nueva)
        actor = ActorAgent(agent="vigia")
        bitacora.registrar(
            conn,
            alerta_id,
            "alert",
            actor,
            f"Alerta detectada: {entrada.title.text}",
            dia,
        )

    return nueva


@router.put("/alertas/{id}/causa", response_model=Alert)
async def ingresar_causa(
    id: str,
    entrada: AgentCauseInput,
    agente: str = Header(..., alias="X-Agent"),
    costo: str | None = Header(None, alias="X-Cost-Json"),
    conn: psycopg.Connection = Depends(obtener_conexion),
    _: None = Depends(validar_agente),
) -> Alert:
    """
    Analista explica la causa.
    Transición: new → analyzing.
    El texto de la causa es enmascarado antes de ser enviado al modelo,
    pero se almacena sin enmascarar.
    """
    if agente != "analista":
        raise HTTPException(400, "Solo Analista puede ingresar causa")

    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "Alerta no existe")

    try:
        transicionar(alerta.status, "analyzing")
    except Exception as e:
        raise HTTPException(409, str(e)) from e

    nueva = alerta.model_copy(
        update={"status": "analyzing", "cause": entrada.cause}
    )
    dia = simulacion.dia_actual(conn)
    actor = ActorAgent(agent="analista")

    detalle = f"Causa identificada: {entrada.cause.sentence.text if hasattr(entrada.cause, 'sentence') else 'N/A'}"

    with conn.transaction():
        alertas_repo.guardar(conn, nueva)
        bitacora.registrar(conn, id, "evidence", actor, detalle, dia)
        if costo:
            _registrar_costo(conn, id, costo, "analista")

    return nueva


@router.put("/alertas/{id}/propuesta", response_model=Alert)
async def ingresar_propuesta(
    id: str,
    entrada: AgentProposalInput,
    agente: str = Header(..., alias="X-Agent"),
    costo: str | None = Header(None, alias="X-Cost-Json"),
    conn: psycopg.Connection = Depends(obtener_conexion),
    _: None = Depends(validar_agente),
) -> Alert:
    """
    Estratega propone acciones.
    Transición: analyzing → proposed.
    """
    if agente != "estratega":
        raise HTTPException(400, "Solo Estratega puede ingresar propuesta")

    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "Alerta no existe")

    try:
        transicionar(alerta.status, "proposed")
    except Exception as e:
        raise HTTPException(409, str(e)) from e

    nueva = alerta.model_copy(update={"status": "proposed", "actions": entrada.actions})
    dia = simulacion.dia_actual(conn)
    actor = ActorAgent(agent="estratega")

    acciones_txt = "; ".join(a.title for a in entrada.actions)
    detalle = f"Propuestas {len(entrada.actions)} acciones: {acciones_txt}"

    with conn.transaction():
        alertas_repo.guardar(conn, nueva)
        bitacora.registrar(conn, id, "proposal", actor, detalle, dia)
        if costo:
            _registrar_costo(conn, id, costo, "estratega")

    return nueva


@router.post("/alertas/{id}/ejecutar", response_model=Alert)
async def ejecutar_accion(
    id: str,
    entrada: AgentExecutionInput,
    agente: str = Header(..., alias="X-Agent"),
    conn: psycopg.Connection = Depends(obtener_conexion),
    _: None = Depends(validar_agente),
) -> Alert:
    """
    Ejecutor corre una acción aprobada.
    Transición: approved → executed.
    """
    if agente != "ejecutor":
        raise HTTPException(400, "Solo Ejecutor puede ejecutar")

    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "Alerta no existe")

    if alerta.status != "approved":
        raise HTTPException(409, f"Alerta no aprobada, status={alerta.status}")

    accion = next((a for a in alerta.actions if a.id == entrada.action_id), None)
    if accion is None:
        raise HTTPException(400, "Acción no pertenece a esta alerta")

    try:
        transicionar(alerta.status, "executed")
    except Exception as e:
        raise HTTPException(409, str(e)) from e

    nueva = alerta.model_copy(
        update={
            "status": "executed",
            "executed_action": {
                "action_id": entrada.action_id,
                "result": entrada.result,
            },
        }
    )
    dia = simulacion.dia_actual(conn)
    actor = ActorAgent(agent="ejecutor")

    resultado = f"✓ {entrada.result}" if entrada.status == "success" else f"✗ {entrada.result}"
    detalle = f"Acción ejecutada: {accion.title} - {resultado}"

    with conn.transaction():
        alertas_repo.guardar(conn, nueva)
        bitacora.registrar(conn, id, "action", actor, detalle, dia)

    return nueva


def _registrar_costo(
    conn: psycopg.Connection, alert_id: str, costo_json: str, agente: str
) -> None:
    """Helper para registrar costos de agentes en bitácora y alertas.costos."""
    try:
        costo = CostoAgente.model_validate_json(costo_json)
        detalle = (
            f"Costo: {costo.tokens_entrada} entrada + {costo.tokens_salida} salida "
            f"({costo.modelo}), {costo.latencia_ms}ms"
        )
        dia = simulacion.dia_actual(conn)
        actor = ActorAgent(agent=costo.agent)
        bitacora.registrar_costo(conn, alert_id, actor, detalle, dia)
    except Exception as e:
        pass
