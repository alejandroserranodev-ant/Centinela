import datetime
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..modelos import AgentStep, ChatMessage, ChatQuestion
from ..sse import flujo

router = APIRouter()

SIN_AGENTES = "Sin evidencia suficiente: los agentes todavía no están conectados en este esqueleto"


@router.post("/chat")
async def chat(pregunta: ChatQuestion) -> StreamingResponse:
    async def eventos():
        ahora = datetime.datetime.now(datetime.UTC).isoformat()
        paso = AgentStep(
            alert_id=pregunta.alert_id,
            agent="analista",
            status="running",
            description="Buscando la respuesta en los datos",
            start=ahora,
        )
        yield "step", paso
        paso = paso.model_copy(update={"status": "done", "description": SIN_AGENTES, "end": ahora})
        yield "step", paso

        mensaje = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            role="centinela",
            text=SIN_AGENTES,
            figures=[],
            alert_id=pregunta.alert_id,
            enough_evidence=False,
            date=ahora,
        )
        yield "end", mensaje

    return StreamingResponse(flujo(eventos()), media_type="text/event-stream")
