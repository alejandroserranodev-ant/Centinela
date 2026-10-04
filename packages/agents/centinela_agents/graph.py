import hashlib
import logging
import re
from typing import Any, Callable, Iterator, Mapping

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .catalog import Catalog, KpiReader
from .failures import SchemaRefused, StepTimeout, TokenCapReached
from .metered import metering, spent
from .metrics import Metrics
from .schema import CHAT_ROOT, ENDS, GATE, ROOT, Leaf, Node, Tree, reachable
from .state import AlertState, ChatState, approved_action
from .walk import Context, Detection, detection_state, state_holds

logger = logging.getLogger(__name__)

LeafFunction = Callable[[Mapping[str, Any]], Mapping[str, Any]]
Classifier = Callable[[Mapping[str, Any]], str]
DECISION_KINDS = ("approve", "edit", "reject", "request_changes")
REJECTION_TARGETS = ("causa", "propuesta", "ambos", "ninguno")
DECIDED_STATUS = {"approve": "aprobada", "edit": "aprobada", "reject": "rechazada"}
ACCUMULATED = ("camino", "transitions", "failures", "events")
REASONS = {
    "timeout": "El análisis no terminó a tiempo.",
    "token_cap": "El análisis no terminó: la alerta agotó el trabajo que tiene asignado.",
    "schema": "El análisis no terminó: no se pudo redactar una causa respaldada por cifras.",
    "error": "El análisis no terminó: no se pudo consultar la información necesaria.",
}
MANUAL_REVIEW_OWNERS = "## The owner of a manual review"
BOUND_NODES = frozenset({"explicar.destino_nuevo", "proponer.retorno_disponible", "aprobar.recarga_disponible", GATE})
STEP_LABELS = {
    ("vigia", "detectar"): "Detectada anomalía",
    ("vigia", "titular"): "Redactando el título",
    ("analista", "explicar"): "Buscando la causa",
    ("estratega", "proponer"): "Proponiendo acciones",
    ("estratega", "revision_manual"): "Preparando la revisión manual",
    ("ejecutor", "ejecutar"): "Ejecutando la acción aprobada",
    ("ejecutor", "nota_manual"): "Redactando la nota de la tarea manual",
    ("chat", "clasificar"): "Leyendo la pregunta",
    ("chat", "responder"): "Respondiendo con los datos",
}

LEAF_OUTPUTS = {
    ("vigia", "titular"): ("title",),
    ("analista", "explicar"): ("cause", "same_cause_as"),
    ("estratega", "proponer"): ("actions", "insufficient_cause"),
    ("estratega", "revision_manual"): ("actions", "insufficient_cause"),
    ("ejecutor", "ejecutar"): ("executed_action",),
    ("ejecutor", "nota_manual"): ("executed_action",),
    ("chat", "responder"): ("answer",),
}


class MissingLeaf(Exception):
    pass


class ResumeRefused(Exception):
    pass


class StartRefused(Exception):
    pass


def merge(*updates: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for update in updates:
        for key, value in update.items():
            merged[key] = [*merged.get(key, []), *value] if key in ACCUMULATED else value
    return merged


def entering(target: str, state: Mapping[str, Any], nodes: Mapping[str, Node]) -> dict[str, Any]:
    node = nodes.get(target)
    status = state.get("status")
    if node is not None and node.hoja is not None and node.hoja.agente == "analista" and status == "nueva":
        return {"status": "en análisis", "transitions": [[state["alert_id"], "en análisis"]]}
    if target == GATE and status != "propuesta":
        return {"status": "propuesta", "transitions": [[state["alert_id"], "propuesta"]]}
    return {}


def effects(node_id: str, branch: str, state: Mapping[str, Any]) -> dict[str, Any]:
    named = state.get("same_cause_as")
    merged = list(state.get("merged_alerts") or [])
    if (node_id, branch) == ("explicar.destino_nuevo", "si"):
        if named in merged:
            return {}
        return {"merged_alerts": [*merged, named], "transitions": [[named, "unida"]]}
    if (node_id, branch) == ("explicar.destino_nuevo", "no"):
        return {"same_cause_as": None, "events": [{"kind": "same_cause_dropped", "alert": named}]}
    if (node_id, branch) == ("proponer.retorno_disponible", "si"):
        return {"analyst_returns": (state.get("analyst_returns") or 0) + 1}
    if (node_id, branch) == ("aprobar.recarga_disponible", "si"):
        return {
            "proposal_returns": (state.get("proposal_returns") or 0) + 1,
            "proposal_rejections": [*(state.get("proposal_rejections") or []), state["decision"]["reason"]],
            "decision": None,
        }
    return {}


def failure_kind(error: Exception) -> str:
    if isinstance(error, (StepTimeout, TimeoutError)):
        return "timeout"
    if isinstance(error, TokenCapReached):
        return "token_cap"
    if isinstance(error, SchemaRefused):
        return "schema"
    return "error"


def manual_owners(acciones: str) -> dict[str, str]:
    section = acciones.split(MANUAL_REVIEW_OWNERS, 1)[1].split("\n## ")[0]
    rows = re.split(r"^\|(?:---\|)+$", section, maxsplit=1, flags=re.MULTILINE)[1]
    return dict(re.findall(r"^\| `([a-z0-9_]+)` \| `([^`]+)` \|", rows, re.MULTILINE))


def manual_review(metric: str, owners: Mapping[str, str]) -> dict[str, Any]:
    owner = owners.get(metric)
    return {
        "id": "act-revision-manual",
        "title": "Revisión manual de la alerta",
        "type": "task",
        "impact": None,
        "parameters": {} if owner is None else {"owner": owner},
    }


def fallback(leaf: Leaf, state: Mapping[str, Any], error: Exception, ctx: Context) -> dict[str, Any]:
    key = (leaf.agente, leaf.decision)
    if key == ("vigia", "titular"):
        detection = state["detection"]
        words = [ctx.metrics.descriptions.get(detection["metric"], detection["metric"]), *map(str, detection["entity"])]
        return {"title": {"text": " ".join(words), "figures": []}}
    if key == ("analista", "explicar"):
        reason = REASONS[failure_kind(error)]
        reviewed = [query["queryId"] if isinstance(query, Mapping) else str(query) for query in state.get("queries") or []]
        return {"cause": {"kind": "no_evidence", "reason": reason, "queriesReviewed": reviewed}, "same_cause_as": None}
    if key == ("estratega", "proponer"):
        return {"actions": None, "insufficient_cause": None}
    if key == ("estratega", "revision_manual"):
        return {"actions": [manual_review(state["detection"]["metric"], ctx.owners)], "insufficient_cause": None}
    if leaf.agente == "ejecutor":
        return {"executed_action": None}
    if key == ("chat", "clasificar"):
        return {"chat": {**state["chat"], "intent": "fuera_de_alcance"}}
    if key == ("chat", "responder"):
        return {"chat": {**state["chat"], "figuras": None}, "answer": None}
    raise error


def leaf_node(node: Node, function: LeafFunction, ctx: Context, token_cap: int | None = None):
    leaf = node.hoja

    def run(state: Mapping[str, Any]) -> dict[str, Any]:
        write = get_stream_writer()
        step = {"alert_id": state.get("alert_id"), "agent": leaf.agente, "node": node.id, "description": STEP_LABELS.get((leaf.agente, leaf.decision), leaf.decision)}
        write({**step, "status": "running"})
        given = (
            {"alert_id": state["alert_id"], "action": approved_action(state), "decision": state.get("decision")}
            if leaf.agente == "ejecutor"
            else {**state, "excluye": list(leaf.excluye)} if leaf.excluye else state
        )
        cleared = {key: None for key in LEAF_OUTPUTS.get((leaf.agente, leaf.decision), ())}
        with metering(leaf.agente, spent(state.get("cost")), token_cap) as meter:
            try:
                update, failures = {**cleared, **function(given)}, []
            except Exception as error:
                logger.warning("Leaf %s failed for %s: %s", node.id, state.get("alert_id") or "chat", error, exc_info=error)
                update = {**cleared, **fallback(leaf, state, error, ctx)}
                failures = [{"step": node.id, "kind": failure_kind(error), "attempts": meter.attempts}]
        write({**step, "status": "done", "failed": bool(failures)})
        return merge(update, entering(node.sigue, {**state, **update}, ctx.nodes), {"camino": [[node.id, "hoja"]], "failures": failures, "cost": meter.cost()})

    return run


def predicate_node(node: Node, ctx: Context):
    def run(state: Mapping[str, Any]) -> dict[str, Any]:
        recorded: dict[str, Any] = {}
        if node.id == GATE:
            decision = interrupt({"alert_id": state["alert_id"], "awaiting": GATE})
            recorded = {"decision": decision}
            if decision["kind"] in DECIDED_STATUS:
                recorded["status"] = DECIDED_STATUS[decision["kind"]]
            state = {**state, **recorded}
        passed = node.retirado is None and state_holds(node.predicado, state, ctx)
        branch = "si" if passed else "no"
        target = node.si if passed else node.no
        change = merge(recorded, effects(node.id, branch, state))
        return merge(change, entering(target, {**state, **change}, ctx.nodes), {"camino": [[node.id, branch]], "next_node": target})

    return run


def classified(classify: Classifier, state: Mapping[str, Any]) -> str:
    try:
        target = classify(state)
    except Exception:
        return "ninguno"
    return target if target in REJECTION_TARGETS else "ninguno"


def end_node(end_id: str, classify: Classifier):
    def run(state: Mapping[str, Any]) -> dict[str, Any]:
        alert = state.get("alert_id")
        if end_id == "fin.unida":
            return {"fin": end_id, "merged_into": state["same_cause_as"], "status": "unida", "transitions": [[alert, "unida"]]}
        if end_id == "fin.ejecutada":
            return {"fin": end_id, "status": "ejecutada", "transitions": [[alert, "ejecutada"]]}
        if end_id == "fin.rechazada":
            return {"fin": end_id, "rejection_target": classified(classify, state)}
        return {"fin": end_id}

    return run


def read_next(state: Mapping[str, Any]) -> str:
    return state["next_node"]


def read_entry(state: Mapping[str, Any]) -> str:
    return state["entry"]


def compile_tree(
    tree: Tree,
    *,
    leaves: Mapping[tuple[str, str], LeafFunction],
    metrics: Metrics,
    catalog: Catalog,
    reader: KpiReader,
    classify: Classifier,
    checkpointer: Any,
    owners: Mapping[str, str] | None = None,
    token_cap: int | None = None,
):
    ctx = Context.of(tree, metrics, catalog, reader, owners)
    rooted = reachable(ctx.nodes, [ROOT])
    entries = sorted(node.id for node in tree.nodos if node.id in rooted and node.hoja is not None and node.hoja.agente == "vigia")
    graph = StateGraph(AlertState)
    add_walk(graph, reachable(ctx.nodes, entries), leaves, ctx, classify, token_cap)
    graph.add_conditional_edges(START, read_entry, entries)
    return graph.compile(checkpointer=checkpointer)


def add_walk(graph: StateGraph, names: set[str], leaves: Mapping[tuple[str, str], LeafFunction], ctx: Context, classify: Classifier, token_cap: int | None = None) -> None:
    for name in sorted(names):
        node = ctx.nodes.get(name)
        if node is None:
            graph.add_node(name, end_node(name, classify))
            graph.add_edge(name, END)
        elif node.hoja is not None:
            function = leaves.get((node.hoja.agente, node.hoja.decision))
            if function is None:
                raise MissingLeaf(f"{name} needs a function for {node.hoja.agente}/{node.hoja.decision}")
            graph.add_node(name, leaf_node(node, function, ctx, token_cap))
            graph.add_edge(name, node.sigue)
        else:
            graph.add_node(name, predicate_node(node, ctx))
            graph.add_conditional_edges(name, read_next, sorted({node.si, node.no}))


def compile_chat(tree: Tree, *, leaves: Mapping[tuple[str, str], LeafFunction], metrics: Metrics, catalog: Catalog, reader: KpiReader, token_cap: int | None = None):
    ctx = Context.of(tree, metrics, catalog, reader)
    graph = StateGraph(ChatState)
    add_walk(graph, reachable(ctx.nodes, [CHAT_ROOT]), leaves, ctx, lambda state: "ninguno", token_cap)
    graph.add_edge(START, CHAT_ROOT)
    return graph.compile()


class Compiler:
    def __init__(self, *, leaves, metrics: Metrics, catalog: Catalog, reader: KpiReader, classify: Classifier, checkpointer: Any, owners: Mapping[str, str] | None = None, token_cap: int | None = None):
        self._dependencies = {"leaves": leaves, "metrics": metrics, "catalog": catalog, "reader": reader, "classify": classify, "checkpointer": checkpointer, "owners": owners, "token_cap": token_cap}
        self._graphs: dict[tuple[int, str], Any] = {}

    def graph(self, tree: Tree):
        key = (tree.version, hashlib.sha256(tree.model_dump_json().encode()).hexdigest())
        if key not in self._graphs:
            self._graphs[key] = compile_tree(tree, **self._dependencies)
        return self._graphs[key]


def thread(alert_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": alert_id}}


def run_config(alert_id: str, tracer=None) -> dict[str, Any]:
    return {**(dict(tracer.config(alert_id)) if tracer is not None else {}), **thread(alert_id)}


def initial_state(detection: Detection, alert_id: str, day: str, earlier_alerts, alert_briefs, cause_rejections, proposal_rejections) -> dict[str, Any]:
    earlier = {other: status for other, status in (earlier_alerts or {}).items() if other != alert_id}
    return {
        "alert_id": alert_id,
        "simulated_day": day,
        "entry": detection.entry,
        "earlier_alerts": earlier,
        "alert_briefs": {other: dict(brief) for other, brief in (alert_briefs or {}).items() if other in earlier},
        "detection": detection_state(detection),
        "queries": [dict(detection.query)] if detection.query else [],
        "status": "nueva",
        "transitions": [[alert_id, "nueva"]],
        "analyst_returns": 0,
        "proposal_returns": 0,
        "cause_rejections": list(cause_rejections),
        "proposal_rejections": list(proposal_rejections),
        "merged_alerts": [],
    }


def stream_alert(graph, detection: Detection, *, alert_id: str, day: str, earlier_alerts=None, alert_briefs=None, cause_rejections=(), proposal_rejections=(), tracer=None) -> Iterator[dict[str, Any]]:
    initial = initial_state(detection, alert_id, day, earlier_alerts, alert_briefs, cause_rejections, proposal_rejections)
    fresh(graph, alert_id)
    yield from graph.stream(initial, run_config(alert_id, tracer), stream_mode="custom")


def start_alert(graph, detection: Detection, *, alert_id: str, day: str, earlier_alerts=None, alert_briefs=None, cause_rejections=(), proposal_rejections=(), tracer=None) -> dict[str, Any]:
    for _ in stream_alert(graph, detection, alert_id=alert_id, day=day, earlier_alerts=earlier_alerts, alert_briefs=alert_briefs, cause_rejections=cause_rejections, proposal_rejections=proposal_rejections, tracer=tracer):
        pass
    return graph.get_state(thread(alert_id)).values


def fresh(graph, alert_id: str) -> None:
    snapshot = graph.get_state(thread(alert_id))
    if not snapshot.values:
        return
    if snapshot.next == (GATE,):
        raise StartRefused(f"{alert_id} awaits a decision, and a start would discard it")
    graph.checkpointer.delete_thread(alert_id)


def awaiting_decision(graph, alert_id: str) -> bool:
    return graph.get_state(thread(alert_id)).next == (GATE,)


def decision_problem(decision: Mapping[str, Any], state: Mapping[str, Any]) -> str | None:
    if not decision.get("id"):
        return "the decision has no record in apps/api"
    kind = decision.get("kind")
    if kind not in DECISION_KINDS:
        return f"{kind} is no decision"
    if not decision.get("simulated_day"):
        return "the decision carries no simulated day"
    if kind in ("reject", "request_changes") and not str(decision.get("reason", "")).strip():
        return f"{kind} carries no reason"
    if kind in ("approve", "edit") and decision.get("actionId") not in [action["id"] for action in state.get("actions") or []]:
        return f"{decision.get('actionId')} names no proposed action"
    if kind == "edit" and not isinstance(decision.get("parameters"), Mapping):
        return "the edit carries no parameters"
    if kind == "request_changes" and (state.get("proposal_returns") or 0) >= 1:
        return "the alert already requested changes once"
    return None


def resume(graph, alert_id: str, decision: Mapping[str, Any], tracer=None) -> dict[str, Any]:
    snapshot = graph.get_state(thread(alert_id))
    if snapshot.next != (GATE,):
        raise ResumeRefused(f"{alert_id} awaits no decision")
    problem = decision_problem(decision, snapshot.values)
    if problem is not None:
        raise ResumeRefused(f"{alert_id}: {problem}")
    graph.invoke(Command(resume=dict(decision)), run_config(alert_id, tracer))
    return graph.get_state(thread(alert_id)).values
