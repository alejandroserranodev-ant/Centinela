import datetime
import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from centinela_agents.llm_provider import LLMRequest

from ..agentes import get_orchestrator
from ..modelos import AgentStep, ChatMessage, ChatQuestion
from ..sse import flujo

router = APIRouter()


@router.post("/chat")
async def chat(pregunta: ChatQuestion) -> StreamingResponse:
    async def eventos():
        ahora = datetime.datetime.now(datetime.UTC).isoformat()
        paso = AgentStep(
            alert_id=pregunta.alert_id,
            agent="analista",
            status="running",
            description="Analizando tu pregunta con los datos disponibles",
            start=ahora,
        )
        yield "step", paso

        text = ""
        enough_evidence = False
        try:
            orchestrator = get_orchestrator()

            # Build alert context if alert_id provided
            context_lines: list[str] = []
            if pregunta.alert_id:
                try:
                    state = orchestrator.get_state(pregunta.alert_id)
                    if state:
                        context_lines.append(f"Alerta: {pregunta.alert_id}")
                        if state.get("metric"):
                            context_lines.append(f"Métrica: {state['metric']}")
                        if state.get("entity"):
                            context_lines.append(f"Entidad: {state['entity']}")
                        if state.get("day"):
                            context_lines.append(f"Día simulado: {state['day']}")
                        cause = state.get("cause")
                        if cause and isinstance(cause, dict):
                            context_lines.append(f"Causa: {json.dumps(cause, ensure_ascii=False)}")
                        actions = state.get("actions")
                        if actions:
                            context_lines.append(f"Acciones propuestas: {json.dumps(actions, ensure_ascii=False)}")
                except Exception:
                    pass

            system_prompt = (
                "Eres Analista de Centinela, sistema de vigilancia financiera y operacional "
                "de Distribuidora Andina S.A.S. Respondes preguntas sobre alertas, métricas y datos "
                "de negocio de forma concisa y factual. Solo usas datos disponibles, sin inventar."
            )
            if context_lines:
                system_prompt += "\n\nCONTEXTO DE LA ALERTA:\n" + "\n".join(context_lines)

            response = orchestrator.provider.generate_text(
                LLMRequest(
                    system_prompt=system_prompt,
                    user_prompt=pregunta.question,
                    temperature=0.3,
                )
            )
            text = response.text
            enough_evidence = bool(text)

        except Exception as exc:
            text = f"No pude procesar tu pregunta en este momento: {exc}"
            enough_evidence = False

        ahora = datetime.datetime.now(datetime.UTC).isoformat()
        paso = paso.model_copy(update={"status": "done", "end": ahora, "description": "Análisis completado"})
        yield "step", paso

        yield "end", ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            role="centinela",
            text=text,
            figures=[],
            alert_id=pregunta.alert_id,
            enough_evidence=enough_evidence,
            date=ahora,
        )

    return StreamingResponse(flujo(eventos()), media_type="text/event-stream")
