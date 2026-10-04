"""
Vigía: Redact alert title.

Vigía detects which rules are broken (código determinista en walk.py).
This node redacts the title: one sentence in Spanish stating what happened.

Input: the alert state, whose `detection` holds the metric and the entity
Output: Sentence with title and figures
Tools: none (detection is code)
Model: LLM thinking OFF (simple redaction)
"""

import logging
from typing import Any

from centinela_agents.llm_provider import LLMProvider, LLMRequest
from centinela_agents.state import subject

logger = logging.getLogger(__name__)


class VigiaError(Exception):
    """Vigía step error."""
    pass


def redact_title(
    provider: LLMProvider,
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Redact the alert's title from the detection the state holds under `detection`.

    Returns:
        {title: Sentence with text and figures}
    """
    metric, entity_id, _ = subject(state)

    logger.info(
        f"Vigía: redact title for {metric}:{entity_id}",
        extra={"metric": metric, "entity": entity_id}
    )

    prompt = f"""Eres Vigía de Centinela. Tu tarea: redactar una frase en español que describa qué pasó.

REGLAS:
1. Una frase en español que indique qué ocurrió y a qué entidad
2. Escribe cada cifra como placeholder {{0}}, {{1}}, etc., en orden
3. No inventes figuras; copia solo las que recibiste
4. Nombra la entidad por su identificador: {entity_id}
5. Estado del hecho, no causa
6. Palabras de negocio: margen, cartera vencida, cobertura, descuento, concentración, etc.

ALERTA DETECTADA:
- Métrica: {metric}
- Entidad: {entity_id}

Redacta UNA SOLA FRASE en español describiendo qué pasó.
No incluyas causas, explicaciones, ni recomendaciones.
Solo el hecho."""

    try:
        response = provider.generate_text(
            LLMRequest(
                system_prompt="Eres Vigía redactando títulos de alertas.",
                user_prompt=prompt,
                temperature=0.0,
                thinking=False,
            )
        )

        title_text = response.text.strip()

        result = {
            "title": {
                "text": title_text,
                "figures": [],
            },
        }

        logger.info(f"Vigía: title redacted: {title_text[:100]}")
        return result

    except Exception as e:
        logger.error(f"Vigía: title redaction failed: {e}")
        fallback_text = f"{metric} en {entity_id}"
        return {
            "title": {
                "text": fallback_text,
                "figures": [],
            },
        }


