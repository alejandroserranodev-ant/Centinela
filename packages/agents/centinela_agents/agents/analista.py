"""
Analista: Explain why alert happened.

Analyzes alert using data from sql_vistas and buscar_politica.
Returns Cause (identified with evidence OR no_evidence).

Input: detected alert, earlier alerts state, rejection reasons
Output: Cause schema (CauseIdentified | CauseNoEvidence)
Tools: sql_vistas, buscar_politica
Model: LLM thinking ON (reasoning required)
"""

import json
import logging
from typing import Any

from centinela_agents.llm_provider import (
    LLMProvider,
    LLMStructuredRequest,
)
from centinela_agents.schema import Cause, CauseIdentified, CauseNoEvidence
from centinela_agents.tools import ToolRegistry

logger = logging.getLogger(__name__)


class AnalistaError(Exception):
    """Analista step error."""
    pass


def explain_cause(
    provider: LLMProvider,
    alert: dict[str, Any],
    tools: ToolRegistry,
) -> dict[str, Any]:
    """
    Explain why alert happened.

    Args:
        provider: LLM provider (thinking ON)
        alert: {
            metric: str,
            entity: str,
            day: str,
            cifra: Figure,
            severity: str,
            cause_rejections: list[{reason, target}],
        }
        tools: ToolRegistry with sql_vistas, buscar_politica

    Returns:
        {
            cause: CauseIdentified | CauseNoEvidence,
            error: str | None,
        }

    Rules:
        1. Test hypotheses from skill file for this metric
        2. Run queries filtering by simulated day
        3. Test hypothesis: entity, time, direction (three tests)
        4. Report at most one main cause and two contributing
        5. If no hypothesis passes, answer no_evidence
        6. Check rejection reasons; if reason refutes, test next hypothesis
    """
    metric = alert.get("metric")
    entity = alert.get("entity")
    day = alert.get("day")

    logger.info(
        f"Analista: explain {metric}:{entity} on {day}",
        extra={"metric": metric, "entity": entity}
    )

    # Stub: no real tools yet
    sql_tool = tools.sql_vistas if hasattr(tools, 'sql_vistas') else None
    policy_tool = tools.buscar_politica if hasattr(tools, 'buscar_politica') else None

    # Build schema for structured output
    cause_schema = {
        "type": "object",
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "const": "identified"},
                    "sentence": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "claim": {"type": "string"},
                                "figures": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "value": {"type": ["number", "string"]},
                                            "unit": {"type": ["string", "null"]},
                                            "queryId": {"type": "string"}
                                        },
                                        "required": ["value", "queryId"]
                                    }
                                }
                            },
                            "required": ["claim"]
                        }
                    },
                    "same_cause_as": {"type": ["string", "null"]}
                },
                "required": ["kind", "sentence", "evidence"]
            },
            {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "const": "no_evidence"},
                    "reason": {"type": "string"},
                    "queriesReviewed": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["kind", "reason"]
            }
        ]
    }

    prompt = f"""Eres Analista de Centinela. Explica por qué ocurrió la alerta.

ALERTA:
- Métrica: {metric}
- Entidad: {entity}
- Día: {day}

REGLAS:
1. Responde SOLO con JSON válido (no texto adicional)
2. Si encontraste causa con evidencia, usa kind: "identified"
3. Si no hay evidencia suficiente, usa kind: "no_evidence"
4. Una frase que explique qué pasó (causa)
5. Evidencias: claim (texto) + figures (datos con queryId)
6. Máximo una causa principal + dos contribuyentes
7. Sin forecasting; solo datos históricos y políticas
8. Nunca digas "provocó", "probablemente", "seguramente"; usa "coincide con"

Devuelve JSON puro. Nada de markdown, backticks ni explicación."""

    try:
        response = provider.generate_structured(
            LLMStructuredRequest(
                system_prompt="Eres Analista. Responde con JSON válido.",
                user_prompt=prompt,
                schema=cause_schema,
                temperature=0.3,  # Thinking ON (reasoning)
                thinking=True,  # Extended thinking
            )
        )

        # Validate with Pydantic
        cause_data = response.parsed

        # Try to parse as CauseIdentified first, then CauseNoEvidence
        try:
            if cause_data.get("kind") == "identified":
                cause = CauseIdentified.model_validate(cause_data)
            else:
                cause = CauseNoEvidence.model_validate(cause_data)
        except Exception as validation_error:
            logger.warning(f"Analista: validation failed, returning no_evidence: {validation_error}")
            cause = CauseNoEvidence(
                kind="no_evidence",
                reason="El análisis no terminó: el modelo no devolvió una respuesta válida.",
                queriesReviewed=[]
            )

        result = {
            "cause": cause.model_dump(),
            "error": None,
        }

        logger.info(f"Analista: cause found: {cause.kind}")
        return result

    except Exception as e:
        logger.error(f"Analista: explanation failed: {e}")
        # Fallback: no_evidence
        return {
            "cause": CauseNoEvidence(
                kind="no_evidence",
                reason=f"El análisis no terminó: falló una herramienta o la conexión.",
                queriesReviewed=[]
            ).model_dump(),
            "error": str(e),
        }
