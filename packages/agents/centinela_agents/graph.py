import hashlib
import re
from typing import Any, Callable, Mapping

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .catalog import Catalog, KpiReader
from .failures import SchemaRefused, StepTimeout, TokenCapReached
from .metrics import Metrics
from .schema import ENDS, GATE, ROOT, Leaf, Node, Tree, reachable
from .state import AlertState, approved_action
from .walk import Context, Detection, state_holds

LeafFunction = Callable[[Mapping[str, Any]], Mapping[str, Any]]
Classifier = Callable[[Mapping[str, Any]], str]
DECISION_KINDS = ("approve", "edit", "reject", "request_changes")
REJECTION_TARGETS = ("causa", "propuesta", "ambos", "ninguno")
DECIDED_STATUS = {"approve": "aprobada", "edit": "aprobada", "reject": "rechazada"}
ACCUMULATED = ("camino", "transitions", "failures", "events")
REASONS = {
    "timeout": "El análisis no terminó: se agotó el tiempo de respuesta del modelo.",
    "token_cap": "El análisis no terminó: la alerta alcanzó su tope de tokens.",
    "schema": "El análisis no terminó: el modelo no devolvió una respuesta válida.",
    "error": "El análisis no terminó: falló una herramienta o la conexión.",
}
MANUAL_REVIEW_OWNERS = "## The owner of a manual review"
BOUND_NODES = frozenset({"explicar.destino_nuevo", "proponer.retorno_disponible", "aprobar.recarga_disponible", GATE})
LEAF_OUTPUTS = {
    ("vigia", "titular"): ("title",),
    ("analista", "explicar"): ("cause", "same_cause_as"),
    ("estratega", "proponer"): ("actions", "insufficient_cause"),
    ("estratega", "revision_manual"): ("actions", "insufficient_cause"),
    ("ejecutor", "ejecutar"): ("executed_action",),
    ("ejecutor", "nota_manual"): ("executed_action",),
}


class MissingLeaf(Exception):
    pass


class ResumeRefused(Exception):
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
    if isinstance(error, StepTimeout):
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
    raise error


def leaf_node(node: Node, function: LeafFunction, ctx: Context):
    leaf = node.hoja

    def run(state: Mapping[str, Any]) -> dict[str, Any]:
        given = (
            {"alert_id": state["alert_id"], "action": approved_action(state), "decision": state.get("decision")}
            if leaf.agente == "ejecutor"
            else state
        )
        cleared = {key: None for key in LEAF_OUTPUTS.get((leaf.agente, leaf.decision), ())}
        try:
            update, failures = {**cleared, **function(given)}, []
        except Exception as error:
            update, failures = {**cleared, **fallback(leaf, state, error, ctx)}, [{"step": node.id, "kind": failure_kind(error)}]
        return merge(update, entering(node.sigue, {**state, **update}, ctx.nodes), {"camino": [[node.id, "hoja"]], "failures": failures})

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
        passed = state_holds(node.predicado, state, ctx)
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
        alert = state["alert_id"]
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
):
    ctx = Context.of(tree, metrics, catalog, reader, owners)
    rooted = reachable(ctx.nodes, [ROOT])
    entries = sorted(node.id for node in tree.nodos if node.id in rooted and node.hoja is not None and node.hoja.agente == "vigia")
    graph = StateGraph(AlertState)
    for name in sorted(reachable(ctx.nodes, entries)):
        node = ctx.nodes.get(name)
        if node is None:
            graph.add_node(name, end_node(name, classify))
            graph.add_edge(name, END)
        elif node.hoja is not None:
            function = leaves.get((node.hoja.agente, node.hoja.decision))
            if function is None:
                raise MissingLeaf(f"{name} needs a function for {node.hoja.agente}/{node.hoja.decision}")
            graph.add_node(name, leaf_node(node, function, ctx))
            graph.add_edge(name, node.sigue)
        else:
            graph.add_node(name, predicate_node(node, ctx))
            graph.add_conditional_edges(name, read_next, sorted({node.si, node.no}))
    graph.add_conditional_edges(START, read_entry, entries)
    return graph.compile(checkpointer=checkpointer)


class Compiler:
    def __init__(self, *, leaves, metrics: Metrics, catalog: Catalog, reader: KpiReader, classify: Classifier, checkpointer: Any, owners: Mapping[str, str] | None = None):
        self._dependencies = {"leaves": leaves, "metrics": metrics, "catalog": catalog, "reader": reader, "classify": classify, "checkpointer": checkpointer, "owners": owners}
        self._graphs: dict[tuple[int, str], Any] = {}

    def graph(self, tree: Tree):
        key = (tree.version, hashlib.sha256(tree.model_dump_json().encode()).hexdigest())
        if key not in self._graphs:
            self._graphs[key] = compile_tree(tree, **self._dependencies)
        return self._graphs[key]


def thread(alert_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": alert_id}}


def start_alert(graph, detection: Detection, *, alert_id: str, day: str, earlier_alerts=None, cause_rejections=(), proposal_rejections=()) -> dict[str, Any]:
    initial = {
        "alert_id": alert_id,
        "simulated_day": day,
        "entry": detection.entry,
        "earlier_alerts": {other: status for other, status in (earlier_alerts or {}).items() if other != alert_id},
        "detection": {
            "metric": detection.metric,
            "entity": list(detection.entity),
            "path": [list(step) for step in detection.path],
            "row": dict(detection.row),
        },
        "status": "nueva",
        "transitions": [[alert_id, "nueva"]],
        "analyst_returns": 0,
        "proposal_returns": 0,
        "cause_rejections": list(cause_rejections),
        "proposal_rejections": list(proposal_rejections),
        "merged_alerts": [],
    }
    graph.invoke(initial, thread(alert_id))
    return graph.get_state(thread(alert_id)).values


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


def resume(graph, alert_id: str, decision: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = graph.get_state(thread(alert_id))
    if snapshot.next != (GATE,):
        raise ResumeRefused(f"{alert_id} awaits no decision")
    problem = decision_problem(decision, snapshot.values)
    if problem is not None:
        raise ResumeRefused(f"{alert_id}: {problem}")
    graph.invoke(Command(resume=dict(decision)), thread(alert_id))
    return graph.get_state(thread(alert_id)).values
