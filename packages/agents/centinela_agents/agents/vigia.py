"""
Vigía: Redact alert title.

Vigía detects which rules are broken (código determinista en walk.py).
This node redacts the title: one sentence in Spanish stating what happened.

Input: detected alert with metric, entity, cifra, regla, severity, pesos_en_riesgo
Output: Sentence with title and figures
Tools: none (detection is code)
Model: LLM thinking OFF (simple redaction)
"""

import logging
from typing import Any

from centinela_agents.llm_provider import LLMProvider, LLMRequest
from centinela_agents.schema import Figure, Sentence

logger = logging.getLogger(__name__)


class VigiaError(Exception):
    """Vigía step error."""
    pass


def redact_title(
    provider: LLMProvider,
    detection: dict[str, Any],
) -> dict[str, Any]:
    """
    Redact alert title from detected alert.

    Args:
        provider: LLM provider (thinking OFF)
        detection: {
            metric: str,
            entidad: str,
            dia: str,
            cifra: Figure,
            regla: str,
            fuente_umbral: str,
            severidad: str,
            tramo: str | None,
            pesos_en_riesgo: Figure,
        }

    Returns:
        {
            title: Sentence with text and figures,
            error: str | None,
        }

    Rules:
        1. Write one sentence in Spanish stating what happened to which entity
        2. Every figure as placeholder {0}, {1}, in order of figures list
        3. Copy each Figure from input unchanged, add no figure input doesn't have
        4. Name entity by field: linea, cliente_id, sku, bodega_id, vendedor_id, oc_id
        5. State fact, not cause
        6. Use business words (margen, cartera vencida, cobertura, descuento)

    Examples:
        Input: saldo_vencido, cliente_123, cifra=45 (days)
        Output: "Cliente cliente_123 tiene {0} de retraso." (Figure: 45 days)

        Input: margen_pct, linea_456, cifra=3.5 (pts)
        Output: "Línea linea_456 margen cayó {0}." (Figure: 3.5 pts)
    """
    metric = detection.get("metric")
    entity_type = detection.get("entity_type", "entidad")
    entity_id = detection.get("entity")
    cifra = detection.get("cifra")
    severity = detection.get("severity")

    logger.info(
        f"Vigía: redact title for {metric}:{entity_id} severity={severity}",
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
- Entidad: {entity_type} {entity_id}
- Severidad: {severity}
- Cifra: {cifra.value if cifra else "N/A"} {cifra.unit if cifra else ""}

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

        figures = []
        if cifra:
            figures.append(cifra)

        result = {
            "title": {
                "text": title_text,
                "figures": [f.model_dump() for f in figures],
            },
            "error": None,
        }

        logger.info(f"Vigía: title redacted: {title_text[:100]}")
        return result

    except Exception as e:
        logger.error(f"Vigía: title redaction failed: {e}")
        fallback_text = f"{metric} en {entity_id}"
        return {
            "title": {
                "text": fallback_text,
                "figures": [cifra.model_dump()] if cifra else [],
            },
            "error": str(e),
        }


