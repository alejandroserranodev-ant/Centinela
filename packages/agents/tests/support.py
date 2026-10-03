# The catalogue the tests hand the validator and the walk. Each metric's columns are its
# v_* view's, plus the ones the base reads that no view has and the kernel builds:
# caida_pts, margen_minimo_pct, concentracion_vencida_pct, aumento_pct, dias_habiles_sin_traslado.
# The real catalogue comes from kpi_catalogo; DOUBTS.md files the gap.
import copy
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.graph import compile_tree
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Tree
from centinela_agents.validator import Grounds, load_registry
from centinela_agents.walk import Context, detect
from centinela_agents.yaml_loader import load_yaml

AGENTS = Path(__file__).resolve().parents[1]
ARBOL = AGENTS / "arbol"
METRICAS = AGENTS.parents[1] / "data" / "metricas.yaml"
SKILLS = AGENTS / "skills"


def kpi(entity, *columns):
    return Kpi(entity=tuple(entity), columns=frozenset({*entity, *columns}))


VIEW_CATALOG = Catalog(
    {
        "margen_pct": kpi(["semana", "linea"], "ventas", "costo", "margen_pct", "caida_pts", "margen_minimo_pct"),
        "saldo_vencido": kpi(["cliente_id"], "segmento", "cupo_credito", "plazo_dias", "saldo_abierto", "saldo_vencido", "max_dias_vencido", "dias_pago_prom_120d"),
        "concentracion_vencida_pct": kpi(["cliente_id"], "saldo_vencido", "concentracion_vencida_pct"),
        "dias_pago_prom": kpi(["cliente_id", "mes_factura"], "dias_pago_prom", "facturas_pagadas", "aumento_pct"),
        "cobertura_dias": kpi(["sku", "bodega_id"], "linea", "clase_abc", "existencia", "demanda_prom_30d", "cobertura_dias", "unidades_pendientes"),
        "variacion_costo_pct": kpi(["sku"], "linea", "clase_abc", "proveedor_id", "costo_unitario", "costo_anterior", "variacion_pct", "fecha_vigencia", "dias_habiles_sin_traslado"),
        "dias_retraso": kpi(["oc_id"], "proveedor_id", "sku", "bodega_id", "fecha_esperada", "cantidad", "costo_unitario", "recibida", "dias_retraso"),
        "descuento_en_exceso": kpi(["vendedor_id", "semana"], "descuento_en_exceso"),
        "margen_bruto_negativo": kpi(["pedido_id", "linea_n"], "sku", "margen_bruto"),
        "veces_intervalo_habitual": kpi(["cliente_id"], "pedidos", "ultima_compra", "intervalo_prom_dias", "dias_sin_comprar", "veces_intervalo_habitual"),
    }
)


def base_data() -> dict:
    return copy.deepcopy(load_yaml(ARBOL / "base.yaml"))


def base_tree() -> Tree:
    return Tree.model_validate(base_data())


def node_of(data: dict, node_id: str) -> dict:
    return next(node for node in data["nodos"] if node["id"] == node_id)


def grounds(catalog: Catalog = VIEW_CATALOG, metrics=None) -> Grounds:
    return Grounds(
        base=base_tree(),
        registry=load_registry(ARBOL / "fundamentos.yaml"),
        metrics=metrics or load_metrics(METRICAS),
        catalog=catalog,
        skills=SKILLS,
    )


DAY = "2026-03-02"
DECISION_DAY = "2026-03-05"
SALDO_ROW = {"cliente_id": "CLI-001", "segmento": "Mayorista", "cupo_credito": 5000000, "saldo_abierto": 1200000, "saldo_vencido": 800000, "max_dias_vencido": 20}
IDENTIFIED = {"kind": "identified", "sentence": {"text": "El cliente dejó de pagar desde enero.", "figures": []}, "evidence": []}
EMAIL = {"id": "act-email", "title": "Recordatorio de pago", "type": "email_draft", "impact": None, "parameters": {"recipient": "CLI-001", "vendedor_id": "VEN-01"}}
MANUAL_TASK = {"id": "act-manual", "title": "Revisión manual de la alerta", "type": "task", "impact": None, "parameters": {"owner": "Analista de cartera"}}

DEFAULT_LEAVES = {
    ("vigia", "titular"): lambda state: {"title": {"text": "Cartera vencida de CLI-001", "figures": []}},
    ("analista", "explicar"): lambda state: {"cause": IDENTIFIED, "same_cause_as": None},
    ("estratega", "proponer"): lambda state: {"actions": [EMAIL], "insufficient_cause": None},
    ("estratega", "revision_manual"): lambda state: {"actions": [MANUAL_TASK]},
    ("ejecutor", "ejecutar"): lambda state: {"executed_action": {"actionId": state["action"]["id"], "result": "Borrador creado"}},
    ("ejecutor", "nota_manual"): lambda state: {"executed_action": {"actionId": state["action"]["id"], "result": "Tarea creada"}},
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


def compiled(recorder, *, overrides=None, rows=None, classify=None, tree=None, catalog=VIEW_CATALOG):
    return compile_tree(
        tree or base_tree(),
        leaves=leaves(recorder, overrides),
        metrics=load_metrics(METRICAS),
        catalog=catalog,
        reader=reader_from({DECISION_DAY: {"saldo_vencido": [SALDO_ROW]}} if rows is None else rows),
        classify=classify or (lambda state: "propuesta"),
        checkpointer=InMemorySaver(),
    )


def saldo_detection(row=SALDO_ROW, tree=None, catalog=VIEW_CATALOG, rows=None):
    ctx = Context.of(tree or base_tree(), load_metrics(METRICAS), catalog, reader_from({DAY: rows or {"saldo_vencido": [row]}}))
    (detection,) = detect(ctx, DAY)
    return detection


def approve(action_id="act-email", decision_id="dec-1", day=DECISION_DAY):
    return {"id": decision_id, "kind": "approve", "actionId": action_id, "simulated_day": day}


def statuses(state, alert_id="A1"):
    return [status for alert, status in state["transitions"] if alert == alert_id]
