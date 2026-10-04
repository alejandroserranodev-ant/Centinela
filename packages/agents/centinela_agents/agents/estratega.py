"""
Estratega: propose one to three actions from the closed list of acciones.md.

Code reads the rows acciones.md lists for the alert's metric and hands them to the model by ref.
The model chooses rows whose condition the alert and its cause meet and words each action; code
fills every parameter from the alert's KPI row and entity, and sets the impact to the KPI's
`pesos_en_riesgo`, computed in SQL, whenever the row names a formula.
"""

import logging
import re
from typing import Any, Mapping

from centinela_agents.evidence import Sources, merged_queries, stray_digits, mask_entity
from centinela_agents.failures import SchemaRefused
from centinela_agents.llm_provider import LLMProvider, LLMStructuredRequest
from centinela_agents.schema import Action
from centinela_agents.skills import ActionRow, action_rows, skill
from centinela_agents.state import subject

logger = logging.getLogger(__name__)

PROPOSAL_TOKENS = 350
MAX_ACTIONS = 3
IMPACT_ASSUMPTION = "El impacto son los pesos en riesgo de la alerta, tal como los calcula su consulta."
NO_FORMULA = "Esta acción no tiene un impacto en pesos calculado."
POLICY = re.compile(r"^[A-Z]{3}-POL-\d{3}\b")
PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "maxItems": MAX_ACTIONS,
            "items": {
                "type": "object",
                "properties": {"row": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}},
                "required": ["row", "title", "description"],
            },
        },
        "insufficient_cause": {"type": "boolean"},
    },
    "required": ["actions", "insufficient_cause"],
}


def parameters_of(row: ActionRow, values: Mapping[str, Any]) -> dict[str, Any]:
    filled: dict[str, Any] = {}
    for token in row.parameters:
        name, _, source = (part.strip() for part in token.partition(":"))
        if source:
            value = values.get(source, source)
        elif name in values:
            value = values[name]
        else:
            continue
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            filled[name] = value
    return filled


def cause_text(cause: Mapping[str, Any]) -> str:
    if cause.get("kind") != "identified":
        return str(cause.get("reason") or "")
    sentence = cause.get("sentence")
    return sentence.get("text", "") if isinstance(sentence, Mapping) else str(sentence or "")


def described(description: str, policy: str) -> str:
    return f"{description} ({policy})" if POLICY.match(policy) else description


def propose_actions(provider: LLMProvider, state: Mapping[str, Any], cause: Mapping[str, Any] | None, sources: Sources) -> dict[str, Any]:
    metric, entity, day = subject(state)
    cause = cause or {}
    if cause.get("kind") != "identified":
        return {"actions": None, "insufficient_cause": True}
    detection = state["detection"]
    rows = {row.ref: row for row in action_rows(metric)}
    ledger = sources.ledger()
    qid, row = ledger.alert_row(metric, detection["entity"], day)
    kpi_row = dict(row or detection["row"])
    values = {**dict(zip(sources.catalog.kpis[metric].entity, detection["entity"])), **kpi_row}
    listed = "\n".join(f"{ref}: [{action.type}] {action.condition} ({action.policy})" for ref, action in rows.items())
    rejections = "\n".join(f"- {reason}" for reason in state.get("proposal_rejections") or []) or "- ninguno"

    # Use masked entity in prompt
    masked_entity = ", ".join(mask_entity(detection["entity"]))
    prompt = f"""detection.metric: {metric}
detection.entity: {masked_entity}
simulated_day: {day}
fila del KPI: {kpi_row}
causa: {cause_text(cause)}
rechazos de propuestas anteriores:
{rejections}

filas de acciones.md para {metric}:
{listed}

Elige de una a tres filas cuya condición se cumple, por su ref, en el orden de la lista. Escribe
title (máximo 8 palabras) y description (una frase) en español, sin cifras: el impacto lo agrega el
código. Si ninguna fila se
sostiene con esta causa, devuelve actions vacío e insufficient_cause true."""
    response = provider.generate_structured(
        LLMStructuredRequest(
            system_prompt=skill("estratega", "contrato"),
            user_prompt=prompt,
            schema=PROPOSAL_SCHEMA,
            temperature=0.0,
            max_tokens=PROPOSAL_TOKENS,
            thinking=True,
        )
    )
    allowed = (*map(str, detection["entity"]), day)
    chosen = [
        item
        for item in response.parsed.get("actions") or []
        if item.get("row") in rows and not stray_digits(f"{item.get('title', '')} {item.get('description', '')}", allowed)
    ]
    unique = list({item["row"]: item for item in chosen}.values())[:MAX_ACTIONS]
    if not unique:
        return {"actions": None, "insufficient_cause": True, "queries": merged_queries(state, ledger)}
    level = ((cause.get("confidence") or {}).get("level")) or "medium"
    impact = {"value": kpi_row.get("pesos_en_riesgo"), "unit": "COP", "queryId": qid} if kpi_row.get("pesos_en_riesgo") is not None else None
    actions = []
    for item in unique:
        action_row = rows[item["row"]]
        has_impact = action_row.formula is not None and impact is not None
        try:
            action = Action.model_validate(
                {
                    "id": f"act-{metric}-{action_row.ref}",
                    "title": item["title"],
                    "description": described(item["description"], action_row.policy),
                    "type": action_row.type,
                    "parameters": parameters_of(action_row, values),
                    "impact": impact if has_impact else None,
                    "confidence": {"level": level if has_impact else "low", "assumptions": [IMPACT_ASSUMPTION if has_impact else NO_FORMULA]},
                }
            )
        except ValueError as error:
            raise SchemaRefused(f"Estratega's action {action_row.ref} is refused: {error}") from error
        actions.append(action.model_dump())
    logger.info("Estratega: %d actions for %s:%s", len(actions), metric, entity)
    return {"actions": actions, "insufficient_cause": None, "queries": merged_queries(state, ledger)}
