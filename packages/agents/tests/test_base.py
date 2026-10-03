from pathlib import Path

from centinela_agents.metrics import load_metrics
from centinela_agents.predicate import is_kpi, kpi_column
from centinela_agents.schema import Tree, index
from centinela_agents.state import STATE_FIELDS, approved_action, field_value
from centinela_agents.yaml_loader import load_yaml

AGENTS = Path(__file__).resolve().parents[1]
METRICAS = AGENTS.parents[1] / "data" / "metricas.yaml"


def base() -> Tree:
    return Tree.model_validate(load_yaml(AGENTS / "arbol" / "base.yaml"))


def test_the_base_parses_and_every_fundamento_is_registered():
    registry = {entry["id"] for entry in load_yaml(AGENTS / "arbol" / "fundamentos.yaml")["fundamentos"]}
    tree = base()
    assert {node.fundamento for node in tree.nodos if node.fundamento} <= registry
    assert {law.fundamento for law in tree.leyes} <= registry


def test_every_state_field_the_base_reads_is_declared():
    read = {node.predicado.lee for node in base().nodos if node.predicado and not is_kpi(node.predicado.lee)}
    assert read <= STATE_FIELDS


def test_every_metric_has_a_kpi_node_in_detectar():
    read = {kpi_column(node.predicado.lee)[0] for node in base().nodos if node.predicado and is_kpi(node.predicado.lee)}
    assert read == set(load_metrics(METRICAS).names)


def test_an_operator_stays_a_string_in_the_base():
    assert index(base())["explicar.con_evidencia"].predicado.op == "="
    assert index(base())["explicar.con_evidencia"].no == "hoja.estratega.revision_manual"


def test_field_value_walks_a_dotted_path():
    assert field_value({"cause": {"kind": "identified"}}, "estado.cause.kind") == "identified"
    assert field_value({"cause": None}, "estado.cause.kind") is None


def test_the_approved_action_carries_the_edited_parameters():
    actions = [{"id": "a1", "type": "email_draft", "parameters": {"vendedor_id": "VEN-01"}}]
    edit = {"kind": "edit", "actionId": "a1", "parameters": {"vendedor_id": "VEN-02"}}
    assert approved_action({"actions": actions, "decision": edit})["parameters"] == {"vendedor_id": "VEN-02"}
    assert approved_action({"actions": actions, "decision": {"kind": "approve", "actionId": "a1"}})["type"] == "email_draft"
    assert approved_action({"actions": actions, "decision": {"kind": "reject", "reason": "no"}}) is None


def test_the_manual_review_loads_the_table_that_names_its_owner():
    assert index(base())["hoja.estratega.revision_manual"].hoja.skill == "estratega/acciones.md"
