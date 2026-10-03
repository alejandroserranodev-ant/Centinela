import pytest
from pydantic import ValidationError

from centinela_agents.schema import Tree, branches, index, level, reachable, stage_of
from centinela_agents.yaml_loader import parse_yaml

TREE = {
    "version": 1,
    "leyes": [{"id": "todo_paso_en_bitacora", "fundamento": "iso31000.6.7"}],
    "nodos": [
        {"id": "hoja.vigia.titular", "hoja": {"agente": "vigia", "decision": "titular", "skill": "vigia/contrato.md"}, "sigue": "explicar.x"},
        {"id": "explicar.x", "fundamento": "iso9001.10.2.1.b.3", "predicado": {"lee": "estado.same_cause_as", "op": "existe"}, "si": "fin.unida", "no": "fin.rechazada"},
    ],
}


def test_a_no_key_stays_a_string_and_true_stays_a_boolean():
    assert parse_yaml("si: a\nno: b\nvalor: true\nyes: c\nop: \"=\"\n") == {"si": "a", "no": "b", "valor": True, "yes": "c", "op": "="}


def test_a_tree_parses_into_nodes_leaves_and_laws():
    tree = Tree.model_validate(TREE)
    nodes = index(tree)
    assert nodes["explicar.x"].no == "fin.rechazada"
    assert branches(nodes["hoja.vigia.titular"]) == [("sigue", "explicar.x")]
    assert branches(nodes["explicar.x"]) == [("si", "fin.unida"), ("no", "fin.rechazada")]
    assert tree.leyes[0].fundamento == "iso31000.6.7"


def test_an_unknown_key_fails_the_schema():
    broken = {**TREE, "nodos": [{**TREE["nodos"][1], "color": "rojo"}]}
    with pytest.raises(ValidationError):
        Tree.model_validate(broken)


def test_an_operator_outside_the_closed_list_fails_the_schema():
    node = {**TREE["nodos"][1], "predicado": {"lee": "estado.same_cause_as", "op": "and"}}
    with pytest.raises(ValidationError):
        Tree.model_validate({**TREE, "nodos": [node]})


@pytest.mark.parametrize(
    "node_id, expected",
    [
        ("detectar.raiz", 1),
        ("aprobar.decision", 1),
        ("hoja.vigia.titular", 1),
        ("detectar.cartera", 2),
        ("detectar.cartera.saldo_vencido", 3),
        ("detectar.cartera.saldo_vencido.dias", 3),
    ],
)
def test_the_level_is_read_from_the_family_in_the_id(node_id, expected):
    assert level(node_id) == expected


def test_a_leaf_takes_its_agents_stage_and_an_end_is_cerrar():
    nodes = index(Tree.model_validate(TREE))
    assert stage_of("hoja.vigia.titular", nodes) == "detectar"
    assert stage_of("explicar.x", nodes) == "explicar"
    assert stage_of("fin.unida", nodes) == "cerrar"


def test_reachable_skips_the_nodes_it_is_told_to_avoid():
    nodes = index(Tree.model_validate(TREE))
    assert reachable(nodes, ["hoja.vigia.titular"]) == {"hoja.vigia.titular", "explicar.x", "fin.unida", "fin.rechazada"}
    assert reachable(nodes, ["hoja.vigia.titular"], without=frozenset({"explicar.x"})) == {"hoja.vigia.titular"}
