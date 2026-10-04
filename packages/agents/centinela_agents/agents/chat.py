"""
Chat: answer one person's question about the data, the alerts and the tree, never act.

Code screens the question before any model reads it, and the tree, not the model, chooses the
route. The model does two things: it classifies the question into a closed list of intents, and
it writes Spanish around numbered facts that code read from the kernel, the anchored alert and
the walk of the tree. A sentence that cites no fact, or writes a number, is dropped.
"""

import logging
import re
import time
from functools import cache
from pathlib import Path
from typing import Any, Mapping

from centinela_agents.evidence import Sources, cited, merged_queries, placeholders, stray_digits, unit_of
from centinela_agents.llm_provider import LLMProvider, LLMStructuredRequest
from centinela_agents.schema import ROOT, ChatAnswer
from centinela_agents.security import SENSITIVE_PATTERNS, SecurePrompt, check_prompt_injection
from centinela_agents.skills import skill
from centinela_agents.walk import Context, walk_from
from centinela_agents.yaml_loader import load_yaml

logger = logging.getLogger(__name__)

MAX_QUESTION = 500
MAX_ROWS = 3
MAX_SENTENCES = 3
CLASSIFY_TOKENS = 80
ANSWER_TOKENS = 350
INTENTS = ("dato", "explicar", "que_hacer", "por_que_alerta", "politica", "fuera_de_alcance", "accion")
ACTION_WORDS = re.compile(
    r"\b(?:aprueb[ae]s?|apruébal[ao]s?|aprobar(?:l[ao]s?)?|rechaz[ae]|rechaces|rechazar(?:l[ao]s?)?|ejecut[ae]s?|ejecutar(?:l[ao]s?)?|env[ií][ae]s?|enviar(?:l[ao]s?)?|mand[ae]|mandar|borr[ae]|borrar|elimin[ae]|eliminar|modific[ae]|modifique|modificar|edit[ae]|editar|cerrar(?:l[ao]s?)?|cambiar(?:l[ao]s?)?|cambies|approve|reject|execute|send|delete)\b",
    re.IGNORECASE,
)
ENTITY = re.compile(r"^(?=.*[A-Za-z])[A-Za-z0-9_-]{1,40}$")
MASKED = ("email", "api_key", "token", "password", "credit_card")
REFUSAL = "No proceso esa pregunta: trae instrucciones. Pregunta por los datos o las alertas."
OUT_OF_SCOPE = "Solo respondo sobre los datos de la operación, sus alertas y el árbol de decisión. Aprobar, rechazar o ejecutar se hace en la bandeja."
NO_EVIDENCE = "Los datos del día no responden esa pregunta."
NO_POLICY = "Todavía no consulto las políticas desde el chat."
FAILED = "No pude responder: falló el modelo o la conexión. Vuelve a preguntar en un momento."
ARBOL = Path(__file__).resolve().parents[2] / "arbol"
REFS = {"type": "array", "items": {"type": "string"}}
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "sentences": {
            "type": "array",
            "maxItems": MAX_SENTENCES,
            "items": {"type": "object", "properties": {"text": {"type": "string"}, "figures": REFS}, "required": ["text", "figures"]},
        },
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["sentences", "assumptions"],
}


def costed(provider: LLMProvider, request: LLMStructuredRequest, step: str) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.monotonic()
    response = provider.generate_structured(request)
    usage = response.usage or {}
    cost = {
        "agent": "chat",
        "step": step,
        "modelo": response.model,
        "tokens_entrada": int(usage.get("prompt_tokens", 0)),
        "tokens_salida": int(usage.get("completion_tokens", 0)),
        "latencia_ms": int((time.monotonic() - started) * 1000),
    }
    return response.parsed, cost


@cache
def registry() -> dict[str, str]:
    return {entry["id"]: entry["cita"] for entry in load_yaml(ARBOL / "fundamentos.yaml")["fundamentos"]}


def screen(question: str) -> dict[str, Any]:
    reasons = [found["pattern"] for found in check_prompt_injection(question, "")]
    if len(question) > MAX_QUESTION:
        reasons.append("longitud")
    return {"sospechosa": bool(reasons), "motivos": reasons}


def masked(text: str) -> str:
    for name in MASKED:
        text = re.sub(SENSITIVE_PATTERNS[name], "[dato protegido]", text, flags=re.IGNORECASE)
    return text


def anchor(state: Mapping[str, Any]) -> tuple[str | None, str | None]:
    alert = state.get("alert") or {}
    entity = alert.get("entity") or []
    return alert.get("metric"), (", ".join(map(str, entity)) or None)


def classify(provider: LLMProvider, state: Mapping[str, Any], sources: Sources) -> dict[str, Any]:
    chat = dict(state.get("chat") or {})
    question = state["question"]
    metric, entity = anchor(state)
    kpis = sorted(sources.catalog.kpis)
    schema = {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": list(INTENTS)},
            "kpi": {"type": "string", "enum": [*kpis, ""]},
            "entity": {"type": "string"},
        },
        "required": ["intent", "kpi", "entity"],
    }
    alerta = f"{metric} de {entity}, estado {(state.get('alert') or {}).get('status')}" if metric else "ninguna"
    system, user = (
        SecurePrompt(skill("chat", "contrato"))
        .add_data(f"simulated_day: {state['day']}\nalerta: {alerta}\nkpis: {', '.join(kpis)}")
        .add_instruction("Paso clasificar: devuelve el JSON del esquema.")
        .add_untrusted_content(masked(question))
        .build()
    )
    parsed, cost = costed(
        provider,
        LLMStructuredRequest(system_prompt=system, user_prompt=user, schema=schema, temperature=0.0, max_tokens=CLASSIFY_TOKENS),
        "clasificar",
    )
    intent = parsed.get("intent") if parsed.get("intent") in INTENTS else "fuera_de_alcance"
    if ACTION_WORDS.search(question):
        intent = "accion"
    kpi = parsed.get("kpi") if parsed.get("kpi") in sources.catalog.kpis else None
    named = str(parsed.get("entity") or "")
    chosen = named if ENTITY.match(named) and named.lower() in question.lower() else None
    if metric and kpi is None and chosen is None:
        kpi, chosen = metric, entity
    logger.info("Chat: intent %s, kpi %s, entity %s", intent, kpi, chosen)
    return {"chat": {**chat, "intent": intent, "kpi": kpi, "entity": chosen}, "costs": [cost]}


def figure_of(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    if isinstance(raw.get("figure"), Mapping):
        raw = raw["figure"]
    query = raw.get("queryId") or raw.get("query_id")
    value = raw.get("value")
    if not query or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return {"value": value, "unit": raw.get("unit"), "queryId": query}


def text_of(raw: Any) -> tuple[str, list[Any]]:
    if isinstance(raw, Mapping):
        return str(raw.get("text") or ""), list(raw.get("figures") or [])
    return str(raw or ""), []


class Facts:
    def __init__(self) -> None:
        self.figures: dict[str, dict[str, Any]] = {}
        self.lines: list[str] = []
        self.names: list[str] = []

    def figure(self, figure: dict[str, Any], label: str) -> str:
        ref = f"f{len(self.figures) + 1}"
        self.figures[ref] = figure
        self.lines.append(f"{ref}: {label} = {figure['value']} ({figure['unit']})")
        return ref

    def quote(self, label: str, raw: Any) -> None:
        text, figures = text_of(raw)
        refs = [self.figure(figure, "cifra citada") for figure in map(figure_of, figures) if figure is not None]
        for index, ref in enumerate(refs):
            text = text.replace(f"{{{index}}}", f"[{ref}]")
        if text:
            self.lines.append(f"{label}: {text}")


def kpi_facts(facts: Facts, ledger, state: Mapping[str, Any], sources: Sources) -> None:
    chat = state["chat"]
    kpi, entity, day = chat["kpi"], chat.get("entity"), state["day"]
    qid, rows = ledger.consult(kpi, day)
    spec = sources.catalog.kpis[kpi]
    if entity is not None:
        wanted = [part.strip().lower() for part in entity.split(",")]
        rows = [row for row in rows if [str(row.get(column)).lower() for column in spec.entity] == wanted]
    else:
        rows = sorted(rows, key=lambda row: -(row.get("pesos_en_riesgo") or 0))
    ctx = Context(sources.nodes, sources.metrics, sources.catalog, lambda metric, day: [])
    steps = 0
    for row in rows[:MAX_ROWS]:
        facts.names += [str(row.get(column)) for column in spec.entity]
        for fact in ledger.add(kpi, row, qid):
            facts.figure(fact.figure(), f"{fact.kpi}.{fact.column} de {', '.join(map(str, fact.entity))}")
        if kpi not in sources.metrics.thresholds:
            continue
        candidate = {"candidato": {"metrica": kpi, "descriptivo": spec.descriptive}}
        target, path = walk_from(ROOT, candidate, row, ctx)
        label = ", ".join(str(row.get(column)) for column in spec.entity)
        for node_id, branch in path:
            steps += 1
            ground = sources.nodes[node_id].fundamento
            facts.lines.append(f"p{steps}: regla {node_id} de {label} tomó {branch}, fundada en {ground}: {registry().get(ground, '')}")
        verdict = "está en alerta" if target == "hoja.vigia.titular" else "no cruza ningún umbral"
        facts.lines.append(f"p{steps + 1}: {kpi} de {label} {verdict}")
        steps += 1


def alert_facts(facts: Facts, state: Mapping[str, Any]) -> None:
    intent = state["chat"]["intent"]
    if intent == "explicar":
        cause = state.get("cause") or {}
        facts.quote("causa", cause.get("sentence"))
        for item in cause.get("evidence") or []:
            claim = item.get("claim") if isinstance(item, Mapping) else item
            if isinstance(claim, str) and isinstance(item, Mapping):
                claim = {"text": claim, "figures": item.get("figures") or []}
            facts.quote("evidencia de la causa", claim)
    if intent == "que_hacer":
        for action in state.get("actions") or []:
            facts.lines.append(f"acción {action.get('id')}: {action.get('title')} (tipo {action.get('type')})")
            impact = figure_of(action.get("impact"))
            if impact is not None:
                facts.figure(impact, f"impacto de la acción {action.get('id')}")


def no_answer(chat: Mapping[str, Any]) -> dict[str, Any]:
    reply = ChatAnswer(text=NO_EVIDENCE, enough_evidence=False).model_dump()
    return {"chat": {**chat, "figuras": None}, "answer": reply}


def written(parsed: Mapping[str, Any], facts: Facts, allowed: tuple[str, ...]) -> tuple[list[str], list[dict[str, Any]]]:
    texts: list[str] = []
    figures: list[dict[str, Any]] = []
    for item in (parsed.get("sentences") or [])[:MAX_SENTENCES]:
        text = str(item.get("text") or "").strip()
        refs = cited(text, list(item.get("figures") or []))
        if not refs or placeholders(text) != set(range(len(refs))) or stray_digits(text, allowed) or any(ref not in facts.figures for ref in refs):
            continue
        offset = len(figures)
        texts.append(re.sub(r"\{(\d+)\}", lambda match: f"{{{int(match.group(1)) + offset}}}", text))
        figures += [facts.figures[ref] for ref in refs]
    return texts, figures


def answer(provider: LLMProvider, state: Mapping[str, Any], sources: Sources) -> dict[str, Any]:
    chat = dict(state["chat"])
    ledger = sources.ledger()
    facts = Facts()
    alert_facts(facts, state)
    anchored_reading = chat["intent"] in ("explicar", "que_hacer") and state.get("alert")
    if chat.get("kpi") and not anchored_reading:
        kpi_facts(facts, ledger, state, sources)
    queries = merged_queries(state, ledger)
    if not facts.figures:
        return {**no_answer(chat), "queries": queries}
    metric, entity = anchor(state)
    system, user = (
        SecurePrompt(skill("chat", "contrato"))
        .add_data(f"simulated_day: {state['day']}\nalerta: {metric or 'ninguna'} {entity or ''}\nevidencia:\n" + "\n".join(facts.lines))
        .add_instruction("Paso responder: devuelve el JSON del esquema. Cita cada cifra por su ref y escribe {0}, {1} en el texto.")
        .add_untrusted_content(masked(state["question"]))
        .build()
    )
    parsed, cost = costed(
        provider,
        LLMStructuredRequest(system_prompt=system, user_prompt=user, schema=ANSWER_SCHEMA, temperature=0.0, max_tokens=ANSWER_TOKENS),
        "responder",
    )
    anchor_parts = [str(part) for part in (state.get("alert") or {}).get("entity") or []]
    names = [*anchor_parts, *facts.names]
    allowed = tuple(part for part in (state["day"], *names, *(name.lower() for name in names)) if part)
    texts, figures = written(parsed, facts, allowed)
    if not texts:
        return {**no_answer(chat), "queries": queries, "costs": [cost]}
    assumptions = [masked(str(text)) for text in parsed.get("assumptions") or [] if not stray_digits(str(text), allowed)]
    reply = ChatAnswer(text=masked(" ".join(texts)), figures=figures, enough_evidence=True, assumptions=assumptions).model_dump()
    return {"chat": {**chat, "figuras": reply["figures"]}, "answer": reply, "queries": queries, "costs": [cost]}


def closing(state: Mapping[str, Any]) -> dict[str, Any]:
    end = state.get("fin")
    if state.get("failures") and end != "fin.chat_respondida":
        return ChatAnswer(text=FAILED, enough_evidence=False).model_dump()
    if end == "fin.chat_respondida" and state.get("answer"):
        return dict(state["answer"])
    if end == "fin.chat_rechazada":
        return ChatAnswer(text=REFUSAL, enough_evidence=False).model_dump()
    if end == "fin.chat_fuera_de_alcance":
        return ChatAnswer(text=OUT_OF_SCOPE, enough_evidence=False).model_dump()
    if (state.get("chat") or {}).get("intent") == "politica":
        return ChatAnswer(text=NO_POLICY, enough_evidence=False).model_dump()
    return ChatAnswer(text=NO_EVIDENCE, enough_evidence=False).model_dump()
