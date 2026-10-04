# The three moves of an expansion and the fixed criteria: a valid split and a valid branch pass and
# keep L0 and L1, each planted move is refused naming its criterion, the caps hold, and a replay
# drops only the moves the version refuses. Each test named test_orq_ is an ORQ- case.
import shutil
from dataclasses import replace

import pytest

from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.expansion import Branch, Caps, MOVE, Retire, Split, apply_move, cap_problems, entry_of, expansion_problems, fingerprint, layer_hash, load_growth, replay
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Tree, Leaf, Node, Predicate, index, level
from centinela_agents.validator import load_grounds
from centinela_agents.walk import Context, detect
from support import ARBOL, DAY, KERNEL_CATALOG, METRICAS, SALDO_ROW, SKILLS, base_data, base_tree, grounds, node_of, reader_from, split_tree

WIDE = Caps(depth=100, nodes_per_stage=100)
DIVISION = "proponer.cartera.saldo_vencido.division_1"
NEW_LEAF = "hoja.estratega.proponer.saldo_vencido.1"
NODE = Node(id=DIVISION, fundamento="iso31000.6.5.2", predicado=Predicate(lee="estado.detection.metric", op="=", valor="saldo_vencido"), si=NEW_LEAF, no="hoja.estratega.proponer", divide="hoja.estratega.proponer")
HOJA = Leaf(agente="estratega", decision="proponer", skill="estratega/contrato.md", excluye=("act-saldo_vencido-r1",))
LEAF = Node(id=NEW_LEAF, hoja=HOJA, sigue="proponer.causa_insuficiente")
ENTRY = Node(id="detectar.cartera.retraso", fundamento="iso31000.6.4.2", predicado=Predicate(lee="estado.candidato.metrica", op="=", valor="retraso"), si="detectar.cartera.retraso.dias", no="fin.sin_alerta")
DAYS = Node(id="detectar.cartera.retraso.dias", fundamento="fin-pol-004.s4", predicado=Predicate(lee="kpi.retraso.dias_vencido", op=">", umbral="retraso"), si="hoja.vigia.titular", no="fin.sin_alerta")
WITH_RETRASO = Catalog({**KERNEL_CATALOG.kpis, "retraso": Kpi(("cliente_id",), frozenset({"cliente_id", "dias_vencido", "max_dias_vencido", "pesos_en_riesgo"}), thresholds={"dias_vencido": 1})})


def split(node=None, leaf=None, hoja=None, **changes):
    nueva = LEAF.model_copy(update={**(leaf or {}), **({"hoja": HOJA.model_copy(update=hoja)} if hoja else {})})
    return Split(**{"agente": "estratega", "hoja": "hoja.estratega.proponer", "nodo": NODE.model_copy(update=node or {}), "nueva": nueva, **changes})


def branch(**changes):
    return Branch(**{"agente": "vigia", "familia": "detectar.cartera", "metrica": "retraso", "nodos": (ENTRY, DAYS), **changes})


def test_orq_a_split_passes_keeps_l0_and_l1_and_yields_the_split_tree():
    assert expansion_problems(base_tree(), split(), grounds(), WIDE) == []
    child = apply_move(base_tree(), split())
    assert child == split_tree()
    assert layer_hash(child) == layer_hash(base_tree())
    assert child.leyes == base_tree().leyes
    assert {node.id for node in child.nodos if node.hoja is None and level(node.id) == 1} == {node.id for node in base_tree().nodos if node.hoja is None and level(node.id) == 1}
    assert entry_of(split()) == DIVISION


def test_the_layer_hash_moves_when_l0_or_an_l1_node_changes():
    data = base_data()
    law = data["leyes"][0]
    law["fundamento"] = "iso31000.6.6"
    assert layer_hash(Tree.model_validate(data)) != layer_hash(base_tree())
    data = base_data()
    node_of(data, "aprobar.decision")["predicado"]["valor"] = ["approve"]
    assert layer_hash(Tree.model_validate(data)) != layer_hash(base_tree())


def test_a_split_whose_new_node_is_no_leaf_is_refused_naming_that_problem():
    found = expansion_problems(base_tree(), split(leaf={"hoja": None}), grounds(), WIDE)
    assert found == ["hoja.estratega.proponer.saldo_vencido.1, the new leaf of the split, carries no hoja"]


def test_a_split_whose_new_leaf_lacks_its_sigue_is_refused_naming_that_problem():
    found = expansion_problems(base_tree(), split(leaf={"sigue": None}), grounds(), WIDE)
    assert found == ["hoja.estratega.proponer.saldo_vencido.1 lacks its sigue"]


def test_orq_a_branch_for_a_new_kpi_passes_and_its_detection_walks_it():
    assert expansion_problems(base_tree(), branch(), grounds(catalog=WITH_RETRASO), WIDE) == []
    child = apply_move(base_tree(), branch())
    nodes = index(child)
    assert "retraso" in nodes["detectar.cartera"].predicado.valor
    assert nodes["detectar.cartera.dias_pago_prom"].no == "detectar.cartera.retraso"
    rows = {"retraso": [{"cliente_id": "CLI-009", "dias_vencido": 6, "pesos_en_riesgo": 100.0}], "saldo_vencido": [SALDO_ROW]}
    found = detect(Context.of(child, load_metrics(METRICAS), WITH_RETRASO, reader_from({DAY: rows})), DAY)
    assert {(detection.metric, detection.entry) for detection in found} == {("retraso", "hoja.vigia.titular"), ("saldo_vencido", "hoja.vigia.titular")}


PLANTED_MOVES = [
    ("split by another agent", split(agente="analista"), "analista splits hoja.estratega.proponer, a leaf of estratega"),
    ("the chat expands", split(agente="chat"), "chat expands nothing"),
    ("split node outside the stage", split(node={"id": "explicar.cartera.saldo_vencido.division_1"}), "only an L2 or L3 node of proponer does"),
    ("split node at L1", split(node={"id": "proponer.division_1"}), "only an L2 or L3 node of proponer does"),
    ("split leaf of another agent", split(hoja={"agente": "analista", "decision": "explicar", "skill": "analista/contrato.md"}), "takes no new leaf of estratega/proponer on si"),
    ("split leaf of another decision", split(hoja={"decision": "revision_manual"}), "takes no new leaf of estratega/proponer on si"),
    ("split node that divides nothing", split(node={"divide": None}), "must divide hoja.estratega.proponer"),
    ("split that drops the old leaf", split(node={"no": "hoja.estratega.revision_manual"}), "does not lead back to hoja.estratega.proponer on no"),
    ("split leaf that bypasses aprobar", split(leaf={"sigue": "hoja.ejecutor.ejecutar"}), "continues to hoja.ejecutor.ejecutar"),
    ("split leaf already in the tree", split(leaf={"id": "hoja.estratega.revision_manual"}, node={"si": "hoja.estratega.revision_manual"}), "hoja.estratega.revision_manual is already in the tree"),
    ("unregistered fundamento", split(node={"fundamento": "iso9999.1"}), "absent from fundamentos.yaml"),
    ("two operands", split(node={"predicado": Predicate(lee="estado.detection.metric y estado.cause.kind", op="=", valor="saldo_vencido")}), "which is not one operand"),
    ("undeclared state field", split(node={"predicado": Predicate(lee="estado.detection.humor", op="=", valor="x")}), "which the alert's state does not declare"),
    ("kpi outside detectar", split(node={"predicado": Predicate(lee="kpi.saldo_vencido.max_dias_vencido", op=">", umbral="saldo_vencido")}), "reads a KPI outside detectar"),
    ("row of another metric excluded", split(hoja={"excluye": ("act-margen_pct-r1",)}), "excludes act-margen_pct-r1, a row of another metric than saldo_vencido"),
    ("excluded rows under a split that tests no metric", split(node={"predicado": Predicate(lee="estado.cause.kind", op="=", valor="identified")}), "excludes rows without testing estado.detection.metric = one metric"),
    ("unknown row excluded", split(hoja={"excluye": ("act-saldo_vencido-r99",)}), "which no row of acciones.md names"),
    ("branch under no family", branch(familia="aprobar.decision"), "which is no L2 family of detectar"),
    ("branch outside the agent's stage", branch(agente="estratega"), "which is no L2 family of proponer"),
    ("metric already admitted", branch(metrica="saldo_vencido"), "detectar.cartera already admits saldo_vencido"),
    ("branch entry that tests nothing", branch(nodos=(ENTRY.model_copy(update={"predicado": Predicate(lee="estado.candidato.descriptivo", op="=", valor=False)}), DAYS)), "starts at detectar.cartera.retraso, which tests estado.candidato.metrica = retraso"),
    ("branch exit around aprobar", branch(nodos=(ENTRY, DAYS.model_copy(update={"si": "hoja.ejecutor.ejecutar"}))), "exits to hoja.ejecutor.ejecutar"),
    ("branch leaf of a decision no base leaf takes", branch(nodos=(ENTRY, DAYS.model_copy(update={"si": "hoja.vigia.kpi"}), Node(id="hoja.vigia.kpi", hoja=Leaf(agente="vigia", decision="proponer_kpi", skill="vigia/contrato.md"), sigue="hoja.analista.explicar"))), "hoja.vigia.kpi is no leaf of vigia taking a decision and a route its base leaves take"),
    ("unknown umbral", branch(nodos=(ENTRY, DAYS.model_copy(update={"predicado": Predicate(lee="kpi.retraso.dias_vencido", op=">", umbral="inventada")}))), "absent from metricas.yaml and from the approved KPIs"),
    ("retire an L1 node", Retire(nodo="explicar.con_evidencia", motivo="No aplica"), "explicar.con_evidencia is an L1 node; only an L2 or L3 node retires"),
    ("retire a leaf", Retire(nodo="hoja.estratega.proponer", motivo="No aplica"), "hoja.estratega.proponer is a leaf; only an L2 or L3 node retires"),
    ("retire with no reason", Retire(nodo="detectar.cartera.saldo_vencido.dias", motivo=" "), "carries no reason"),
    ("retire outside the agent's stage", Retire(agente="estratega", nodo="detectar.cartera.saldo_vencido.dias", motivo="No aplica"), "estratega retires detectar.cartera.saldo_vencido.dias, outside its stage proponer"),
    ("retire the last branch of a metric", Retire(nodo="detectar.inventario.cobertura_dias.minima", motivo="No aplica"), "metric cobertura_dias has no L3 branch in detectar"),
    ("retire a node that is not there", Retire(nodo="detectar.nada", motivo="No aplica"), "detectar.nada, which is no node of the tree"),
]


@pytest.mark.parametrize("name, move, expected", PLANTED_MOVES, ids=[name for name, _, _ in PLANTED_MOVES])
def test_orq_the_criteria_refuse_each_planted_move(name, move, expected):
    found = expansion_problems(base_tree(), move, grounds(catalog=WITH_RETRASO), WIDE)
    assert any(expected in problem for problem in found), found


def test_orq_a_new_umbral_whose_source_quotes_no_document_is_refused():
    real = load_metrics(METRICAS)
    silent = replace(real, threshold_sources={**real.threshold_sources, "saldo_vencido": ""})
    days = DAYS.model_copy(update={"predicado": Predicate(lee="kpi.retraso.max_dias_vencido", op=">", umbral="saldo_vencido")})
    found = expansion_problems(base_tree(), branch(nodos=(ENTRY, days)), grounds(catalog=WITH_RETRASO, metrics=silent), WIDE)
    assert "detectar.cartera.retraso.dias names umbral saldo_vencido, whose fuente_umbral quotes no document" in found


def test_orq_a_move_past_a_cap_is_refused():
    assert any("past the cap of 3" in problem for problem in expansion_problems(base_tree(), split(), grounds(), Caps(depth=3, nodes_per_stage=100)))
    assert any(problem.startswith("stage proponer holds") for problem in expansion_problems(base_tree(), split(), grounds(), Caps(depth=100, nodes_per_stage=3)))


def test_orq_a_retirement_passes_under_caps_the_tree_already_exceeds():
    parent = split_tree()
    assert cap_problems(parent, Caps(depth=3, nodes_per_stage=3))
    assert expansion_problems(parent, Retire(nodo=DIVISION, motivo="No ayudó"), grounds(), Caps(depth=3, nodes_per_stage=3)) == []


def test_the_settings_of_growth_load_and_hold_the_base_under_its_caps():
    growth = load_growth(ARBOL / "crecimiento.yaml")
    assert isinstance(growth.repetitions["estratega"], int) and growth.repetitions["estratega"] >= 1
    assert cap_problems(base_tree(), growth.caps) == []


def test_a_move_survives_its_json():
    for move in (split(), branch(), Retire(nodo=DIVISION, motivo="No ayudó")):
        assert MOVE.validate_python(move.model_dump(mode="json")) == move


def test_a_replay_applies_each_move_in_order_and_drops_the_refused_ones():
    retire = Retire(nodo=DIVISION, motivo="No ayudó")
    tree, dropped = replay(base_tree(), [split(), retire, split(agente="analista")], grounds(), WIDE)
    assert index(tree)[DIVISION].retirado == "No ayudó"
    assert [position for position, _ in dropped] == [2]


def test_load_grounds_returns_the_checked_base_and_its_registry():
    loaded = load_grounds(ARBOL, METRICAS, SKILLS, KERNEL_CATALOG)
    assert loaded.base == base_tree() and "iso31000.6.5.2" in loaded.registry


def skills_copy(tmp_path):
    shutil.copytree(SKILLS, tmp_path / "skills")
    return tmp_path / "skills"


def digest(growth=None, skills=SKILLS, **changes):
    return fingerprint(replace(grounds(), skills=skills, **changes), growth or load_growth(ARBOL / "crecimiento.yaml"))


def test_the_fingerprint_is_the_same_for_two_loads_of_the_same_inputs():
    first = load_grounds(ARBOL, METRICAS, SKILLS, KERNEL_CATALOG)
    second = load_grounds(ARBOL, METRICAS, SKILLS, KERNEL_CATALOG)
    growth = load_growth(ARBOL / "crecimiento.yaml")
    assert fingerprint(first, growth) == fingerprint(second, growth) == digest()
    assert len(digest()) == 64


def test_the_fingerprint_moves_when_the_base_the_registry_the_metrics_or_the_growth_settings_change():
    data = base_data()
    node_of(data, "aprobar.decision")["predicado"]["valor"] = ["approve"]
    real = load_metrics(METRICAS)
    growth = load_growth(ARBOL / "crecimiento.yaml")
    changed = {
        "base": digest(base=Tree.model_validate(data)),
        "registry": digest(registry=grounds().registry | {"iso9999.1"}),
        "metrics": digest(metrics=replace(real, threshold_sources={**real.threshold_sources, "saldo_vencido": "otro"})),
        "repetitions": digest(growth=replace(growth, repetitions={"estratega": growth.repetitions["estratega"] + 1})),
        "depth": digest(growth=replace(growth, caps=replace(growth.caps, depth=growth.caps.depth + 1))),
        "nodes per stage": digest(growth=replace(growth, caps=replace(growth.caps, nodes_per_stage=growth.caps.nodes_per_stage + 1))),
    }
    assert len({digest(), *changed.values()}) == len(changed) + 1


@pytest.mark.parametrize("name", ["estratega/acciones.md", "vigia/contrato.md", "analista/saldo_vencido.md", "analista/politicas.md"])
def test_the_fingerprint_moves_when_a_skill_it_reads_changes(tmp_path, name):
    skills = skills_copy(tmp_path)
    assert digest(skills=skills) == digest()
    with (skills / name).open("a", encoding="utf-8") as file:
        file.write("\nchanged\n")
    assert digest(skills=skills) != digest()


def test_the_fingerprint_moves_when_an_analyst_skill_is_added_or_removed(tmp_path):
    skills = skills_copy(tmp_path)
    (skills / "analista" / "nueva.md").write_text("x", encoding="utf-8")
    assert digest(skills=skills) != digest()
    (skills / "analista" / "nueva.md").unlink()
    (skills / "analista" / "saldo_vencido.md").unlink()
    assert digest(skills=skills) != digest()
