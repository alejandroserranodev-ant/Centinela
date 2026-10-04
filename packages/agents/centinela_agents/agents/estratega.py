"""
Estratega: Propose 1-3 actions for an alert.

Receives alert + cause and generates action proposals.
Returns list of Action (or insufficient_cause for fallback).

Input: detected alert, cause, rejection reasons
Output: list[Action] or insufficient_cause (as fallback)
Tools: sql_vistas, buscar_politica, calcular_impacto
Model: LLM thinking ON (reasoning required)
"""

import logging
from typing import Any

from centinela_agents.llm_provider import (
    LLMProvider,
    LLMStructuredRequest,
)
from centinela_agents.schema import Action, Confidence
from centinela_agents.state import subject
from centinela_agents.tools import ToolRegistry

logger = logging.getLogger(__name__)


class EstrategaError(Exception):
    """Estratega step error."""
    pass


def propose_actions(
    provider: LLMProvider,
    state: dict[str, Any],
    cause: dict[str, Any],
    tools: ToolRegistry,
) -> dict[str, Any]:
    """
    Propose 1-3 actions for an alert.

    Args:
        provider: LLM provider (thinking ON)
        state: the alert state; its `detection` holds the metric and the entity
        cause: Cause schema (identified or no_evidence)
        tools: ToolRegistry with sql_vistas, buscar_politica, calcular_impacto

    Returns:
        {
            actions: list[Action] | None,
            insufficient_cause: bool,
        }

    Rules:
        1. If cause.kind is "no_evidence", return insufficient_cause=True
        2. Read acciones.md rows for this metric
        3. Keep rows that match alert + cause
        4. Keep at most 3, in acciones.md order
        5. For each row: call calcular_impacto with formula
        6. Fill parameters only from alert, cause, queries
        7. Cite policy section in description
        8. If no row passes or insufficient_cause again, fallback to manual review
    """
    metric, entity, day = subject(state)
    cause_kind = cause.get("kind")

    logger.info(
        f"Estratega: propose for {metric}:{entity}, cause={cause_kind}",
        extra={"metric": metric, "cause": cause_kind}
    )

    if cause_kind == "no_evidence":
        logger.info(f"Estratega: no evidence, returning insufficient_cause")
        return {
            "actions": None,
            "insufficient_cause": True,
        }

    sql_tool = tools.sql_vistas if hasattr(tools, 'sql_vistas') else None
    policy_tool = tools.buscar_politica if hasattr(tools, 'buscar_politica') else None
    impact_tool = tools.calcular_impacto if hasattr(tools, 'calcular_impacto') else None

    actions_schema = {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["email_draft", "task", "purchase_order_draft", "price_change_draft"]
                        },
                        "parameters": {"type": "object"},
                        "impact": {
                            "type": ["object", "null"],
                            "properties": {
                                "value": {"type": ["number", "string"]},
                                "unit": {"type": ["string", "null"]},
                                "queryId": {"type": "string"}
                            }
                        },
                        "confidence": {
                            "type": "object",
                            "properties": {
                                "level": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"]
                                },
                                "assumptions": {"type": "array"}
                            },
                            "required": ["level"]
                        }
                    },
                    "required": ["id", "title", "description", "type", "parameters", "confidence"]
                }
            }
        },
        "required": ["actions"]
    }

    cause_sentence = cause.get("sentence", "Causa no identificada")
    evidence_summary = f"Causa identificada: {cause_sentence}"

    prompt = f"""Eres Estratega de Centinela. Propón acciones para esta alerta.

ALERTA:
- Métrica: {metric}
- Entidad: {entity}
- Día: {day}

{evidence_summary}

REGLAS:
1. Propón entre 1 y 3 acciones del catálogo cerrado
2. Solo acciones que la causa permite
3. Tipos permitidos: email_draft, task, purchase_order_draft, price_change_draft
4. Parámetros solo de alert, causa, o queries (nunca inventes)
5. Impact = nulo si la métrica no tiene fórmula
6. Confidence: high (dos vistas), medium (una vista), low (incompleto o sin fórmula)
7. Cita sección de política en description
8. Responde SOLO con JSON válido

Devuelve JSON puro. Nada de markdown ni explicación."""

    try:
        response = provider.generate_structured(
            LLMStructuredRequest(
                system_prompt="Eres Estratega. Responde con JSON válido.",
                user_prompt=prompt,
                schema=actions_schema,
                temperature=0.3,
                thinking=True,
            )
        )

        actions_data = response.parsed.get("actions", [])

        actions = []
        for idx, action_data in enumerate(actions_data):
            try:
                action = Action.model_validate(action_data)
                actions.append(action.model_dump())
            except Exception as validation_error:
                logger.warning(f"Estratega: action {idx} validation failed: {validation_error}")
                continue

        if not actions:
            logger.info(f"Estratega: no valid actions, returning insufficient_cause")
            return {
                "actions": None,
                "insufficient_cause": True,
            }

        result = {
            "actions": actions,
            "insufficient_cause": False,
        }

        logger.info(f"Estratega: proposed {len(actions)} actions")
        return result

    except Exception as e:
        logger.error(f"Estratega: proposal failed: {e}")
        return {
            "actions": None,
            "insufficient_cause": True,
        }
