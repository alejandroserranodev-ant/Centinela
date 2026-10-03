# One planted violation per rule of the validator, each on a copy of the base, so a rule that
# never fires fails here. The base itself must pass with no problem. A plant that needs other
# grounds, a threshold of metricas.yaml, returns them as keywords of grounds().
import pytest

from centinela_agents.metrics import Metrics, load_metrics
from centinela_agents.validator import InvalidTree, checked_base, load_base, load_registry, problems
from support import ARBOL, METRICAS, SKILLS, KERNEL_CATALOG, base_data, grounds, node_of


def set_key(node_id, key, value):
    def plant(data):
        node_of(data, node_id)[key] = value
    return plant


def drop_key(node_id, key):
    def plant(data):
        node_of(data, node_id).pop(key)
    return plant


def set_predicate(node_id, **changes):
    def plant(data):
        node_of(data, node_id)["predicado"].update(changes)
    return plant


def set_leaf(node_id, **changes):
    def plant(data):
        node_of(data, node_id)["hoja"].update(changes)
    return plant


def duplicate(node_id):
    def plant(data):
        data["nodos"].append(dict(node_of(data, node_id)))
    return plant


def set_law(index, fundamento):
    def plant(data):
        data["leyes"][index]["fundamento"] = fundamento
    return plant


def both_branches(node_id, target):
    def plant(data):
        node_of(data, node_id).update(si=target, no=target)
    return plant


def add_return(data):
    data["nodos"].append({"id": "proponer.cartera.otra", "fundamento": "iso9001.10.2.1.b.2", "predicado": {"lee": "estado.analyst_returns", "op": "=", "valor": 0}, "si": "hoja.analista.explicar", "no": "proponer.causa_insuficiente"})
    node_of(data, "hoja.estratega.proponer")["sigue"] = "proponer.cartera.otra"




def add_node(node):
    def plant(data):
        data["nodos"].append(dict(node))
    return plant


def set_threshold(metric, column, spec):
    def plant(data):
        real = load_metrics(METRICAS)
        return {"metrics": Metrics(real.descriptions, {**real.thresholds, metric: {**real.thresholds[metric], column: spec}})}
    return plant


ANY_STATE = {"fundamento": "iso31000.6.6", "predicado": {"lee": "estado.actions", "op": "existe"}, "si": "fin.sin_alerta", "no": "fin.sin_alerta"}
ORPHAN = {"id": "hoja.vigia.huerfana", "hoja": {"agente": "vigia", "decision": "titular", "skill": "vigia/contrato.md"}, "sigue": "hoja.ejecutor.ejecutar"}


def add_orphan(data):
    data["nodos"].append(dict(ORPHAN))


PLANTED = [
    ("schema", set_key("explicar.misma_causa", "color", "rojo"), "schema:"),
    ("two values", set_predicate("detectar.cartera.saldo_vencido.dias", valor=15), "compares with an umbral and a valor at once"),
    ("two operands", set_predicate("explicar.con_evidencia", lee="estado.cause.kind y estado.actions"), "which is not one operand"),
    ("en without a list", set_predicate("aprobar.decision", valor="approve"), "tests en without a closed list"),
    ("no fundamento", drop_key("explicar.con_evidencia", "fundamento"), "explicar.con_evidencia lacks its fundamento"),
    ("no si", drop_key("explicar.con_evidencia", "si"), "explicar.con_evidencia lacks its si"),
    ("no no", drop_key("explicar.con_evidencia", "no"), "explicar.con_evidencia lacks its no"),
    ("unregistered fundamento", set_key("explicar.con_evidencia", "fundamento", "iso9999.1"), "absent from fundamentos.yaml"),
    ("leaf with fundamento", set_key("hoja.vigia.titular", "fundamento", "iso31000.6.4.2"), "inherits its parent's fundamento"),
    ("duplicate id", duplicate("explicar.con_evidencia"), "explicar.con_evidencia is declared twice"),
    ("bypass the gate", set_key("proponer.con_acciones", "si", "ejecutar.vigente"), "is reached without passing aprobar.decision"),
    ("bypass vigente", set_key("aprobar.decision", "si", "ejecutar.automatizable"), "is reached without passing ejecutar.vigente"),
    ("cycle", set_key("hoja.analista.explicar", "sigue", "hoja.vigia.titular"), "cycle"),
    ("uncapped return", set_key("proponer.causa_insuficiente", "si", "hoja.analista.explicar"), "cycle"),
    ("dangling id", set_key("explicar.con_evidencia", "no", "explicar.inexistente"), "names explicar.inexistente, which is no node, leaf or end"),
    ("unknown end", set_key("explicar.con_evidencia", "no", "fin.inventado"), "names fin.inventado, which is no node, leaf or end"),
    ("reaches no fin", both_branches("explicar.con_evidencia", "explicar.inexistente"), "explicar.con_evidencia reaches no fin"),
    ("unknown kpi column", set_predicate("detectar.cartera.saldo_vencido.dias", lee="kpi.saldo_vencido.dias_inventados"), "which the kernel does not build"),
    ("undeclared state field", set_predicate("explicar.con_evidencia", lee="estado.humor"), "which the alert's state does not declare"),
    ("kpi outside detectar", set_predicate("proponer.con_acciones", lee="kpi.saldo_vencido.max_dias_vencido", op=">", umbral="saldo_vencido", valor=None), "reads a KPI outside detectar"),
    ("unknown umbral", set_predicate("detectar.cartera.saldo_vencido.dias", umbral="inventada"), "absent from metricas.yaml and from the approved KPIs"),
    ("umbral without the column", set_predicate("detectar.cartera.saldo_vencido.dias", lee="kpi.saldo_vencido.saldo_vencido"), "sets no threshold for saldo_vencido"),
    ("valor on a kpi", set_predicate("detectar.cartera.saldo_vencido.dias", umbral=None, valor=15), "compares a KPI with a valor"),
    ("umbral on a state field", set_predicate("explicar.con_evidencia", valor=None, umbral="saldo_vencido"), "bounds a state field with an umbral"),
    ("missing skill", set_leaf("hoja.vigia.titular", skill="vigia/inexistente.md"), "which is no file under packages/agents/skills"),
    ("decision outside the list", set_leaf("hoja.vigia.titular", decision="proponer"), "outside the decisions of vigia"),
    ("unknown agent", set_leaf("hoja.vigia.titular", agente="orquestador"), "outside vigia, analista, estratega and ejecutor"),
    ("L0 changed", set_law(0, "iso31000.6.6"), "L0 differs from the base"),
    ("L1 changed", set_predicate("aprobar.decision", valor=["approve"]), "L1 node aprobar.decision differs from the base"),
    ("base leaf redirected", set_key("hoja.vigia.titular", "sigue", "explicar.con_evidencia"), "leaf hoja.vigia.titular differs from the base"),
    ("leaf without sigue", drop_key("hoja.vigia.titular", "sigue"), "hoja.vigia.titular lacks its sigue"),
    ("leaf with a branch", set_key("hoja.vigia.titular", "si", "fin.sin_alerta"), "hoja.vigia.titular is a leaf and holds a predicate or a branch"),
    ("node with sigue", set_key("explicar.con_evidencia", "sigue", "fin.sin_alerta"), "explicar.con_evidencia is a node, and only a leaf has sigue"),
    ("id with no stage", add_node({"id": "revisar.x", **ANY_STATE}), "revisar.x names no stage"),
    ("leaf id without hoja", add_node({"id": "detectar.titular", "hoja": {"agente": "vigia", "decision": "titular", "skill": "vigia/contrato.md"}, "sigue": "fin.sin_alerta"}), "detectar.titular is a leaf, so its id starts with hoja"),
    ("existe with a value", set_predicate("proponer.con_acciones", valor=1), "proponer.con_acciones tests existe and compares a value too"),
    ("list without en", set_predicate("aprobar.decision", op="="), "aprobar.decision compares with a list without en"),
    ("threshold of no shape", set_threshold("saldo_vencido", "max_dias_vencido", "quince"), "which is no number, boolean, columna or por with valores"),
    ("threshold on a column the kpi lacks", set_threshold("saldo_vencido", "saldo_abierto", {"columna": "cupo_inventado"}), "reads cupo_inventado, which kpi.saldo_vencido does not build"),
    ("L1 node absent from the base", add_node({"id": "explicar.nuevo", **ANY_STATE}), "L1 node explicar.nuevo is absent from the base"),
    ("law on an unregistered id", set_law(0, "iso9999.1"), "law cifra_de_consulta rests on iso9999.1, absent from fundamentos.yaml"),
    ("boolean written as text", set_predicate("detectar.raiz", valor="True"), "detectar.raiz writes a boolean as True; write true or false"),
    ("boolean in a list written as text", set_predicate("aprobar.decision", valor=["approve", "yes"]), "aprobar.decision writes a boolean as yes; write true or false"),
    ("orphan entry", add_orphan, "hoja.vigia.huerfana is unreachable from detectar.raiz"),
    ("base leaf decision changed", set_leaf("hoja.vigia.titular", decision="detectar"), "leaf hoja.vigia.titular differs from the base"),
    ("return the interpreter does not count", add_return, "cycle"),
    ("kpi read on another metric's row", set_key("detectar.cartera.concentracion_vencida_pct.participacion", "no", "detectar.cartera.saldo_vencido.cupo"), "reads saldo_vencido where the candidate may be concentracion_vencida_pct"),
]


def test_the_base_passes():
    assert problems(base_data(), grounds()) == []


@pytest.mark.parametrize("name, plant, expected", PLANTED, ids=[name for name, _, _ in PLANTED])
def test_the_validator_refuses_each_planted_violation(name, plant, expected):
    data = base_data()
    overrides = plant(data) or {}
    found = problems(data, grounds(**overrides))
    assert any(expected in problem for problem in found), found


def test_a_metric_with_no_branch_skill_or_action_row_is_refused():
    real = load_metrics(METRICAS)
    metrics = Metrics({**real.descriptions, "metrica_nueva": "Nueva"}, {**real.thresholds, "metrica_nueva": {"x": 1}})
    found = problems(base_data(), grounds(metrics=metrics))
    assert "metric metrica_nueva has no L3 branch in detectar" in found
    assert "metric metrica_nueva has no skills/analista/metrica_nueva.md" in found
    assert "metric metrica_nueva has no row in skills/estratega/acciones.md" in found


def test_load_base_returns_the_base_from_its_files():
    assert load_base(ARBOL, METRICAS, SKILLS, KERNEL_CATALOG).version == 1


def test_checked_base_raises_with_every_problem():
    data = base_data()
    node_of(data, "explicar.con_evidencia").pop("no")
    with pytest.raises(InvalidTree) as refused:
        checked_base(data, load_registry(ARBOL / "fundamentos.yaml"), load_metrics(METRICAS), KERNEL_CATALOG, SKILLS)
    assert "explicar.con_evidencia lacks its no" in refused.value.problems
