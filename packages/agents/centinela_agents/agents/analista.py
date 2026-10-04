"""
Analista: explain why an alert happened, from the kernel's figures.

Code reads the alert's KPI row and the rows other KPIs hold for the same entity on the simulated
day, through kpi_consultar, and numbers every figure as a fact. The model chooses which facts
support a cause and writes the Spanish around them; it cites a fact by its ref and never writes a
number, so every figure of the cause carries the queryId of the query that returned it.
"""

import logging
from typing import Any, Mapping

from centinela_agents.evidence import Sources, UnknownFigure, cited, merged_queries, stray_digits
from centinela_agents.failures import SchemaRefused
from centinela_agents.llm_provider import LLMProvider, LLMStructuredRequest
from centinela_agents.schema import CauseIdentified, CauseNoEvidence
from centinela_agents.skills import skill
from centinela_agents.state import subject

logger = logging.getLogger(__name__)

CAUSE_TOKENS = 400
REFS = {"type": "array", "items": {"type": "string"}}
CAUSE_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["identified", "no_evidence"]},
        "sentence": {"type": "string"},
        "sentence_figures": REFS,
        "evidence": {
            "type": "array",
            "maxItems": 2,
            "items": {
                "type": "object",
                "properties": {"claim": {"type": "string"}, "figures": REFS},
                "required": ["claim", "figures"],
            },
        },
        "reason": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kind", "sentence", "sentence_figures", "evidence", "reason", "confidence", "assumptions"],
}


def build_cause(answer: Mapping[str, Any], ledger, queries: list[str], allowed: tuple[str, ...]) -> dict[str, Any]:
    if answer.get("kind") != "identified":
        reason = str(answer.get("reason") or "").strip()
        if not reason or stray_digits(reason, allowed):
            reason = "Ningún KPI del día muestra una causa para esta alerta."
        return CauseNoEvidence(kind="no_evidence", reason=reason, queriesReviewed=queries).model_dump()
    sentence = str(answer.get("sentence") or "")
    sentence_refs = cited(sentence, list(answer.get("sentence_figures") or []))
    if stray_digits(sentence, allowed):
        raise SchemaRefused("Analista wrote a figure outside a placeholder in its sentence")
    claims = [
        item
        for item in answer.get("evidence") or []
        if item.get("figures") and item.get("claim") and not stray_digits(str(item["claim"]), allowed)
    ] or ([{"claim": sentence, "figures": sentence_refs}] if sentence_refs else [])
    try:
        cause = CauseIdentified.model_validate(
            {
                "kind": "identified",
                "sentence": {"text": sentence, "figures": ledger.figures(sentence_refs)},
                "evidence": [{"claim": item["claim"], "figures": ledger.figures(list(item["figures"]))} for item in claims],
                "confidence": {
                    "level": answer.get("confidence") or "low",
                    "assumptions": [text for text in answer.get("assumptions") or [] if not stray_digits(str(text), allowed)],
                },
            }
        )
    except (UnknownFigure, ValueError) as error:
        raise SchemaRefused(f"Analista's cause is refused: {error}") from error
    return cause.model_dump()


def explain_cause(provider: LLMProvider, state: Mapping[str, Any], sources: Sources) -> dict[str, Any]:
    metric, entity, day = subject(state)
    detection = state["detection"]
    ledger = sources.ledger()
    qid, row = ledger.alert_row(metric, detection["entity"], day)
    ledger.add(metric, row or detection["row"], qid)
    ledger.related(metric, detection["entity"], day)
    rejections = "\n".join(f"- {reason}" for reason in state.get("cause_rejections") or []) or "- ninguno"
    insufficient = "sí: la causa anterior no sostuvo ninguna acción" if state.get("insufficient_cause") else "no"
    prompt = f"""detection.metric: {metric}
detection.entity: {entity}
simulated_day: {day}
cause_rejections:
{rejections}
insufficient_cause: {insufficient}

evidencia (cada hecho es una cifra que el kernel devolvió para el día simulado):
{ledger.lines()}

Devuelve el JSON del esquema. sentence es una sola frase de máximo 30 palabras; cada claim, una
frase corta. Cita cada cifra por su ref (f1, f2...) en sentence_figures o en evidence[].figures, y
escribe en el texto el placeholder {{0}}, {{1}} en ese orden. Nunca escribas una cifra en el texto."""
    response = provider.generate_structured(
        LLMStructuredRequest(
            system_prompt=skill("analista", "contrato"),
            user_prompt=prompt,
            schema=CAUSE_SCHEMA,
            temperature=0.0,
            max_tokens=CAUSE_TOKENS,
            thinking=True,
        )
    )
    allowed = (*map(str, detection["entity"]), day)
    cause = build_cause(response.parsed, ledger, list(ledger.queries), allowed)
    logger.info("Analista: %s for %s:%s", cause["kind"], metric, entity)
    return {"cause": cause, "same_cause_as": None, "queries": merged_queries(state, ledger)}
