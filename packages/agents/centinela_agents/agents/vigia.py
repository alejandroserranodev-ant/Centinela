"""
Vigía: write the title of a detected alert.

Detection is code (walk.py). This leaf reads the alert's KPI row through the kernel, hands the
model the compared column and `pesos_en_riesgo` as figures, and keeps the model's sentence only
when every placeholder points to one of them.
"""

import logging
from typing import Any, Mapping

from centinela_agents.evidence import Sources, fills, merged_queries, placeholders, stray_digits
from centinela_agents.failures import SchemaRefused
from centinela_agents.llm_provider import LLMProvider, LLMRequest
from centinela_agents.skills import skill
from centinela_agents.state import subject

logger = logging.getLogger(__name__)

TITLE_TOKENS = 80


def placeholders_problem(text: str, figures: int) -> str | None:
    if fills(text, figures):
        return None
    return f"cites {sorted(index for index in placeholders(text) if index >= figures)} with {figures} figures"


def redact_title(provider: LLMProvider, state: Mapping[str, Any], sources: Sources) -> dict[str, Any]:
    metric, entity, day = subject(state)
    detection = state["detection"]
    ledger = sources.ledger()
    qid, row = ledger.alert_row(metric, detection["entity"], day)
    columns = (*sources.compared(detection), "pesos_en_riesgo")
    facts = ledger.add(metric, row or detection["row"], qid, columns)
    figures = [fact.figure() for fact in facts]
    listed = "\n".join(f"{{{index}}}: {fact.column} = {fact.value} ({fact.figure()['unit']})" for index, fact in enumerate(facts))
    prompt = f"""detection.metric: {metric}
detection.entity: {entity}
simulated_day: {day}
regla: {sources.metrics.descriptions.get(metric, metric)}
figures:
{listed}

Escribe solo la frase del título, en español, con los placeholders de figures."""
    response = provider.generate_text(
        LLMRequest(
            system_prompt=skill("vigia", "contrato"),
            user_prompt=prompt,
            temperature=0.0,
            max_tokens=TITLE_TOKENS,
            thinking=False,
        )
    )
    text = " ".join(response.text.strip().strip('"').split())
    problem = placeholders_problem(text, len(figures))
    if stray_digits(text, (*map(str, detection["entity"]), day)):
        problem = "writes a figure outside a placeholder"
    if not text or problem:
        raise SchemaRefused(f"Vigía's title {problem or 'is empty'}")
    logger.info("Vigía: %s", text[:100])
    return {"title": {"text": text, "figures": figures}, "queries": merged_queries(state, ledger)}
