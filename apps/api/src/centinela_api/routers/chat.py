import asyncio
import datetime
import logging
import uuid

import psycopg
from centinela_agents.agents.chat import FAILED, masked
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .. import alertas as alertas_repo
from .. import bitacora, consultas, simulacion
from ..agentes import _convert_figures, detalle_de_consulta, get_orchestrator
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import ActorAgent, ActorPerson, AgentStep, ChatMessage, ChatQuestion, CostoAgente, Persona
from ..sse import flujo

router = APIRouter(dependencies=[Depends(persona_actual)])
logger = logging.getLogger(__name__)

DESENLACE = {
    "fin.chat_respondida": "answered",
    "fin.chat_sin_evidencia": "no_evidence",
    "fin.chat_otro_periodo": "no_evidence",
    "fin.chat_fuera_de_alcance": "out_of_scope",
    "fin.chat_rechazada": "refused",
}
NODOS = {
    "conversar.raiz": "Revisar que la pregunta no traiga instrucciones",
    "hoja.chat.clasificar": "Clasificar la pregunta",
    "conversar.fuera_de_alcance": "¿Está fuera de lo que el chat responde?",
    "conversar.accion": "¿Pide aprobar o ejecutar algo?",
    "conversar.politica": "¿Pregunta por una política?",
    "conversar.periodo": "¿Pregunta por otro periodo?",
    "conversar.anclada": "¿Viene de una alerta?",
    "conversar.alerta.explicar": "¿Pregunta por qué pasó?",
    "conversar.alerta.causa": "¿La alerta tiene una causa con evidencia?",
    "conversar.alerta.que_hacer": "¿Pregunta qué hacer?",
    "conversar.alerta.acciones": "¿La alerta tiene acciones propuestas?",
    "conversar.dato": "¿Nombra un KPI?",
    "hoja.chat.responder": "Redactar la respuesta con las cifras del kernel",
    "conversar.con_evidencia": "¿Cada frase cita una consulta?",
}
INCOMPLETA = "El asistente no pudo terminar su respuesta."
RAMAS = {"si": "sí", "no": "no", "hoja": "hecho"}


def ahora() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def anclada(alerta) -> dict:
    cuerpo = alerta.model_dump(by_alias=True)
    return {"id": alerta.id, "metric": alerta.metric, "status": alerta.status, "cause": cuerpo["cause"], "actions": cuerpo["actions"]}


def costo_de(costo: dict) -> str:
    leido = CostoAgente.model_validate(costo)
    return f"Costo de {leido.step}: {leido.tokens_entrada} entrada + {leido.tokens_salida} salida ({leido.modelo}), {leido.latencia_ms}ms"


@router.post("/chat")
async def chat(
    pregunta: ChatQuestion,
    quien: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> StreamingResponse:
    dia = simulacion.dia_actual(conn)
    alerta = None
    if pregunta.alert_id is not None:
        alerta = alertas_repo.obtener(conn, pregunta.alert_id)
        if alerta is None:
            raise HTTPException(404, "No existe esa alerta")
    persona = ActorPerson(name=quien.name, role=quien.role)
    agente = ActorAgent(agent="chat")
    with conn.transaction():
        bitacora.registrar(conn, pregunta.alert_id, "question", persona, masked(pregunta.question), dia)

    async def eventos():
        inicio = ahora()
        yield "step", AgentStep(alert_id=pregunta.alert_id, agent="chat", status="running", description="Leyendo la pregunta", start=inicio)
        try:
            respuesta = await asyncio.to_thread(
                get_orchestrator().ask, pregunta.question, dia.isoformat(), anclada(alerta) if alerta is not None else None
            )
        except Exception as error:
            logger.error(f"Chat failed: {error}", exc_info=True)
            respuesta = {
                "fin": "fin.chat_sin_evidencia",
                "steps": [],
                "answer": {"text": FAILED, "figures": [], "enough_evidence": False},
                "queries": [],
                "costs": [],
                "failures": [{"step": "ask", "kind": type(error).__name__}],
            }

        for paso in respuesta["steps"]:
            descripcion = f"{NODOS.get(paso['node'], paso['node'])}: {RAMAS.get(paso['branch'], paso['branch'])}"
            yield "step", AgentStep(alert_id=pregunta.alert_id, agent="chat", node=paso["node"], status="done", description=descripcion, start=inicio, end=ahora())

        final = respuesta["answer"]
        figuras = _convert_figures(final.get("figures"))
        fallos = respuesta.get("failures") or []
        desenlace = "no_evidence" if fallos and respuesta["fin"] != "fin.chat_respondida" else DESENLACE.get(respuesta["fin"], "no_evidence")
        with conn.transaction():
            consultas.registrar(conn, respuesta["queries"])
            for consulta in respuesta["queries"]:
                bitacora.registrar(conn, pregunta.alert_id, "evidence", agente, detalle_de_consulta(consulta), dia, consulta["queryId"])
            tipo = "refusal" if desenlace in ("refused", "out_of_scope") else "answer"
            detalle = final["text"]
            if fallos:
                logger.warning("Chat answered with failures: %s", fallos)
                detalle = f"{detalle} {INCOMPLETA}"
            bitacora.registrar(conn, pregunta.alert_id, tipo, agente, detalle, dia, figuras[0].query_id if figuras else None, figuras)
            for costo in respuesta.get("costs") or []:
                bitacora.registrar_costo(conn, pregunta.alert_id, agente, costo_de(costo), dia)
            bitacora.registrar_prompts(conn, pregunta.alert_id, respuesta.get("prompts") or [], dia)

        yield "end", ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            role="centinela",
            text=final["text"],
            figures=figuras,
            alert_id=pregunta.alert_id,
            enough_evidence=bool(final.get("enough_evidence")) and bool(figuras),
            outcome=desenlace,
            date=ahora(),
        )

    return StreamingResponse(flujo(eventos()), media_type="text/event-stream")
