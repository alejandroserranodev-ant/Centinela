# Estratega's drafter: the count of rejections of one action row that drafts a split, the targets
# and rows that never count, the evidence a version already used, a second row that nests, a draft
# the criteria refuse, and no module of packages/agents that could persist a version. Each test
# named test_orq_ is an ORQ- case.
import re

import pytest

from centinela_agents.expansion import Caps, Growth, Retire, apply_move
from centinela_agents.growth import Rejection, grow, metric_leaf
from centinela_agents.schema import index
from support import AGENTS, base_tree, grounds

GROWTH = Growth({"estratega": 3}, Caps(depth=100, nodes_per_stage=100))
R1, R2 = "act-saldo_vencido-r1", "act-saldo_vencido-r2"
FIRST, SECOND = "proponer.cartera.saldo_vencido.division_1", "proponer.cartera.saldo_vencido.division_2"


def rejected(*alerts, actions=(R1,), metric="saldo_vencido", target="propuesta"):
    return [Rejection(alert, metric, target, tuple(actions)) for alert in alerts]


def test_orq_evidence_below_its_count_drafts_no_expansion():
    assert grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2"), ()) == []


def test_orq_rejections_of_one_row_at_its_count_split_estratega_leaf_for_that_metric():
    (grown,) = grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2", "A3"), ())
    assert (grown.agent, grown.evidence, grown.problems) == ("estratega", ("A1", "A2", "A3"), ())
    nodes = index(grown.tree)
    assert (nodes[FIRST].divide, nodes[FIRST].no, nodes[FIRST].si) == ("hoja.estratega.proponer", "hoja.estratega.proponer", "hoja.estratega.proponer.saldo_vencido.1")
    assert nodes[FIRST].fundamento == "iso31000.6.5.2"
    assert nodes["hoja.estratega.proponer.saldo_vencido.1"].hoja.excluye == (R1,)
    assert nodes["explicar.con_evidencia"].si == FIRST


@pytest.mark.parametrize(
    "rejections",
    [
        rejected("A1", "A2", "A3", target="causa"),
        rejected("A1", "A2", "A3", target="ambos"),
        rejected("A1", "A2", "A3", target="ninguno"),
        rejected("A1", "A2", "A3", actions=("act-revision-manual",)),
        rejected("A1", "A2", "A3", actions=("act-margen_pct-r1",)),
    ],
    ids=["causa", "ambos", "ninguno", "manual review", "another metric's row"],
)
def test_only_a_rejection_sent_to_the_proposal_counts_a_row_of_its_own_metric(rejections):
    assert grow(base_tree(), grounds(), GROWTH, rejections, ()) == []


def test_orq_a_retired_expansion_is_not_drafted_again_before_its_count():
    (first,) = grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2", "A3"), ())
    retired = apply_move(first.tree, Retire(nodo=FIRST, motivo="No ayudó"))
    assert grow(retired, grounds(), GROWTH, rejected("A1", "A2", "A3", "A4", "A5"), first.evidence) == []
    (again,) = grow(retired, grounds(), GROWTH, rejected("A1", "A2", "A3", "A4", "A5", "A6"), first.evidence)
    assert again.evidence == ("A4", "A5", "A6")
    assert index(again.tree)[SECOND].divide == "hoja.estratega.proponer"


def test_a_second_row_of_the_same_metric_nests_and_its_retirement_restores_the_first():
    (first,) = grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2", "A3"), ())
    (second,) = grow(first.tree, grounds(), GROWTH, rejected("A4", "A5", "A6", actions=(R2,)), first.evidence)
    nodes = index(second.tree)
    assert nodes[SECOND].divide == "hoja.estratega.proponer.saldo_vencido.1"
    assert nodes["hoja.estratega.proponer.saldo_vencido.2"].hoja.excluye == (R1, R2)
    assert metric_leaf(nodes, "saldo_vencido") == "hoja.estratega.proponer.saldo_vencido.2"
    retired = index(apply_move(second.tree, Retire(nodo=SECOND, motivo="No ayudó")))
    assert metric_leaf(retired, "saldo_vencido") == "hoja.estratega.proponer.saldo_vencido.1"
    assert retired["hoja.estratega.proponer.saldo_vencido.1"].hoja.excluye == (R1,)
    assert metric_leaf(retired, "margen_pct") == "hoja.estratega.proponer"


def test_rows_of_two_metrics_draft_two_splits_one_after_the_other():
    rejections = rejected("A1", "A2", "A3") + rejected("B1", "B2", "B3", metric="margen_pct", actions=("act-margen_pct-r3",))
    first, second = grow(base_tree(), grounds(), GROWTH, rejections, ())
    assert first.move.nodo.id == "proponer.margen.margen_pct.division_1"
    assert {"proponer.margen.margen_pct.division_1", FIRST} <= set(index(second.tree))


def test_a_draft_the_criteria_refuse_comes_back_with_its_problems_and_no_tree():
    tight = Growth({"estratega": 3}, Caps(depth=3, nodes_per_stage=100))
    (grown,) = grow(base_tree(), grounds(), tight, rejected("A1", "A2", "A3"), ())
    assert grown.tree is None and any("past the cap" in problem for problem in grown.problems)


def test_a_row_the_leaf_already_excludes_lends_no_alert_to_the_new_version():
    (first,) = grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2", "A3"), ())
    rejections = rejected("A1", "A2", "A3") + rejected("B1", "B2", "B3", actions=(R2,))
    (second,) = grow(first.tree, grounds(), GROWTH, rejections, ())
    assert second.evidence == ("B1", "B2", "B3")
    assert second.move.nueva.hoja.excluye == (R1, R2)


def test_orq_no_module_of_packages_agents_opens_a_database_connection():
    sources = [path.read_text(encoding="utf-8") for path in (AGENTS / "centinela_agents").rglob("*.py")]
    assert not [text for text in sources if re.search(r"^\s*(import|from)\s+(psycopg|sqlite3|asyncpg|sqlalchemy)", text, re.MULTILINE)]
