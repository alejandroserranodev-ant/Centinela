# Helpers the tree's tests share. The catalogue is the one the kernel serves: kpi_catalogo of
# packages/tools over the kernel: blocks of data/metricas.yaml, compiled with no database.
import copy
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from centinela_agents.catalog import Catalog, catalog_from_kernel
from centinela_agents.graph import compile_chat, compile_tree
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Tree
from centinela_agents.validator import Grounds, load_registry
from centinela_agents.walk import Context, detect
from centinela_agents.yaml_loader import load_yaml
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_catalogo, load_entries

AGENTS = Path(__file__).resolve().parents[1]
ARBOL = AGENTS / "arbol"
METRICAS = AGENTS.parents[1] / "data" / "metricas.yaml"
SKILLS = AGENTS / "skills"


KERNEL_CATALOG = catalog_from_kernel({"kpis": kpi_catalogo(catalogue_of(load_entries(METRICAS), load_sources()))})


def base_data() -> dict:
    return copy.deepcopy(load_yaml(ARBOL / "base.yaml"))


def base_tree() -> Tree:
    return Tree.model_validate(base_data())


def node_of(data: dict, node_id: str) -> dict:
    return next(node for node in data["nodos"] if node["id"] == node_id)


def grounds(catalog: Catalog = KERNEL_CATALOG, metrics=None) -> Grounds:
    return Grounds(
        base=base_tree(),
        registry=load_registry(ARBOL / "fundamentos.yaml"),
        metrics=metrics or load_metrics(METRICAS),
        catalog=catalog,
        skills=SKILLS,
    )


DAY = "2026-03-02"
DECISION_DAY = "2026-03-05"
SALDO_ROW = {"cliente_id": "CLI-001", "cupo_credito": 5000000, "saldo_abierto": 1200000, "saldo_vencido": 800000, "max_dias_vencido": 20}
IDENTIFIED = {"kind": "identified", "sentence": {"text": "El cliente dejó de pagar desde enero.", "figures": []}, "evidence": []}
EMAIL = {"id": "act-email", "title": "Recordatorio de pago", "type": "email_draft", "impact": None, "parameters": {"recipient": "CLI-001", "vendedor_id": "VEN-01"}}
MANUAL_TASK = {"id": "act-manual", "title": "Revisión manual de la alerta", "type": "task", "impact": None, "parameters": {"owner": "Analista de cartera"}}

CHAT_FIGURE = {"value": 800000, "unit": "COP", "queryId": "q_saldo"}

DEFAULT_LEAVES = {
    ("vigia", "titular"): lambda state: {"title": {"text": "Cartera vencida de CLI-001", "figures": []}},
    ("analista", "explicar"): lambda state: {"cause": IDENTIFIED, "same_cause_as": None},
    ("estratega", "proponer"): lambda state: {"actions": [EMAIL], "insufficient_cause": None},
    ("estratega", "revision_manual"): lambda state: {"actions": [MANUAL_TASK]},
    ("ejecutor", "ejecutar"): lambda state: {"executed_action": {"actionId": state["action"]["id"], "result": "Borrador creado"}},
    ("ejecutor", "nota_manual"): lambda state: {"executed_action": {"actionId": state["action"]["id"], "result": "Tarea creada"}},
    ("chat", "clasificar"): lambda state: {"chat": {**state["chat"], "intent": "dato", "kpi": "saldo_vencido", "entity": "CLI-001"}},
    ("chat", "responder"): lambda state: {"chat": {**state["chat"], "figuras": [CHAT_FIGURE]}, "answer": {"text": "Debe {0}.", "figures": [CHAT_FIGURE], "enough_evidence": True, "assumptions": []}},
}


class Recorder:
    def __init__(self):
        self.calls = []
        self.received = {}

    def count(self, agent, decision):
        return self.calls.count((agent, decision))


def leaves(recorder, overrides=None):
    chosen = {**DEFAULT_LEAVES, **(overrides or {})}

    def recording(key, function):
        def run(state):
            recorder.calls.append(key)
            recorder.received[key] = dict(state)
            return function(state)
        return run

    return {key: recording(key, function) for key, function in chosen.items()}


def reader_from(rows_by_day):
    return lambda metric, day: list(rows_by_day.get(day, {}).get(metric, []))


def compiled(recorder, *, overrides=None, rows=None, classify=None, tree=None, catalog=KERNEL_CATALOG, owners=None, token_cap=None):
    return compile_tree(
        tree or base_tree(),
        leaves=leaves(recorder, overrides),
        metrics=load_metrics(METRICAS),
        catalog=catalog,
        reader=reader_from({DECISION_DAY: {"saldo_vencido": [SALDO_ROW]}} if rows is None else rows),
        classify=classify or (lambda state: "propuesta"),
        checkpointer=InMemorySaver(),
        owners=owners,
        token_cap=token_cap,
    )


def saldo_detection(row=SALDO_ROW, tree=None, catalog=KERNEL_CATALOG, rows=None):
    ctx = Context.of(tree or base_tree(), load_metrics(METRICAS), catalog, reader_from({DAY: rows or {"saldo_vencido": [row]}}))
    (detection,) = detect(ctx, DAY)
    return detection


def approve(action_id="act-email", decision_id="dec-1", day=DECISION_DAY):
    return {"id": decision_id, "kind": "approve", "actionId": action_id, "simulated_day": day}


def statuses(state, alert_id="A1"):
    return [status for alert, status in state["transitions"] if alert == alert_id]


def compiled_chat(recorder, *, overrides=None, tree=None):
    return compile_chat(
        tree or base_tree(),
        leaves=leaves(recorder, overrides),
        metrics=load_metrics(METRICAS),
        catalog=KERNEL_CATALOG,
        reader=reader_from({}),
    )


def question(text="¿Cuánto debe CLI-001?", *, sospechosa=False, alert=None, cause=None, actions=None):
    chat = {"sospechosa": sospechosa, "alert_id": (alert or {}).get("id"), "intent": None, "kpi": None, "entity": None, "figuras": None}
    return {"question": text, "day": DAY, "alert": alert, "cause": cause, "actions": actions, "chat": chat, "queries": []}
