"""
Tests for LangGraph orchestrator routing.

Validates that the decision tree is correctly compiled to LangGraph
and that the graph routes alerts through the correct nodes.
"""

from unittest.mock import MagicMock

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from centinela_agents.graph import (
    GATE,
    Compiler,
    awaiting_decision,
    decision_problem,
    start_alert,
)
from centinela_agents.metrics import Metrics
from centinela_agents.schema import Tree, Node, Law, Leaf, Predicate
from centinela_agents.walk import Detection


class TestGraphCompilation:
    """Tests for compiling decision tree to LangGraph."""

    def test_compile_tree_minimal(self):
        """Compile a minimal tree."""
        tree = Tree(
            version=1,
            leyes=[],
            nodos=(
                Node(
                    id="detectar.raiz",
                    fundamento=None,
                    predicado=None,
                    si=None,
                    no=None,
                    hoja=Leaf(agente="vigia", decision="titular", skill="vigia/contrato.md"),
                    sigue="fin.sin_alerta",
                ),
            )
        )

        leaves = {("vigia", "titular"): lambda x: {"title": {"text": "Test", "figures": []}}}
        metrics = MagicMock(spec=Metrics)
        metrics.catalog = {}
        catalog = MagicMock()
        catalog.columns = {}
        reader = MagicMock()
        classify = lambda x: "ninguno"
        checkpointer = InMemorySaver()

        compiler = Compiler(
            leaves=leaves,
            metrics=metrics,
            catalog=catalog,
            reader=reader,
            classify=classify,
            checkpointer=checkpointer,
        )

        graph = compiler.graph(tree)
        assert graph is not None

    def test_compiler_caches_graph(self):
        """Compiler caches compiled graphs."""
        tree = Tree(
            version=1,
            leyes=[],
            nodos=(
                Node(
                    id="detectar.raiz",
                    fundamento=None,
                    predicado=None,
                    si=None,
                    no=None,
                    hoja=Leaf(agente="vigia", decision="titular", skill="vigia/contrato.md"),
                    sigue="fin.sin_alerta",
                ),
            )
        )

        leaves = {("vigia", "titular"): lambda x: {"title": {"text": "Test", "figures": []}}}
        metrics = MagicMock(spec=Metrics)
        metrics.catalog = {}
        catalog = MagicMock()
        catalog.columns = {}
        reader = MagicMock()
        classify = lambda x: "ninguno"
        checkpointer = InMemorySaver()

        compiler = Compiler(
            leaves=leaves,
            metrics=metrics,
            catalog=catalog,
            reader=reader,
            classify=classify,
            checkpointer=checkpointer,
        )

        graph1 = compiler.graph(tree)
        graph2 = compiler.graph(tree)

        assert graph1 is graph2


class TestGraphRouting:
    """Tests for alert routing through graph."""

    def test_start_alert_begins_in_detectar(self):
        """Starting an alert begins in detectar.raiz."""
        tree = Tree(
            version=1,
            leyes=[],
            nodos=(
                Node(
                    id="detectar.raiz",
                    fundamento=None,
                    predicado=None,
                    si=None,
                    no=None,
                    hoja=Leaf(agente="vigia", decision="titular", skill="vigia/contrato.md"),
                    sigue="fin.sin_alerta",
                ),
            )
        )

        leaves = {("vigia", "titular"): lambda x: {"title": {"text": "Test", "figures": []}}}
        metrics = MagicMock(spec=Metrics)
        metrics.catalog = {}
        metrics.descriptions = {}
        catalog = MagicMock()
        catalog.columns = {}
        reader = MagicMock()
        classify = lambda x: "ninguno"
        checkpointer = InMemorySaver()

        compiler = Compiler(
            leaves=leaves,
            metrics=metrics,
            catalog=catalog,
            reader=reader,
            classify=classify,
            checkpointer=checkpointer,
        )

        graph = compiler.graph(tree)

        detection = Detection(
            entry="detectar.raiz",
            metric="test_metric",
            entity=("entity_id",),
            path=[],
            row={},
        )

        state = start_alert(
            graph,
            detection,
            alert_id="alert_001",
            day="2026-10-03",
        )

        assert state["alert_id"] == "alert_001"
        assert state["status"] == "nueva"


class TestDecisionValidation:
    """Tests for decision validation."""

    def test_decision_problem_no_id(self):
        """Decision without ID is invalid."""
        decision = {"kind": "approve"}
        state = {"actions": [{"id": "a1"}]}

        problem = decision_problem(decision, state)

        assert problem is not None
        assert "no record" in problem

    def test_decision_problem_invalid_kind(self):
        """Decision with invalid kind is invalid."""
        decision = {
            "id": "decision_001",
            "kind": "invalid",
        }
        state = {"actions": []}

        problem = decision_problem(decision, state)

        assert problem is not None
        assert "no decision" in problem

    def test_decision_problem_no_simulated_day(self):
        """Decision without simulated_day is invalid."""
        decision = {
            "id": "decision_001",
            "kind": "approve",
        }
        state = {"actions": []}

        problem = decision_problem(decision, state)

        assert problem is not None
        assert "simulated day" in problem

    def test_decision_problem_reject_no_reason(self):
        """Reject decision without reason is invalid."""
        decision = {
            "id": "decision_001",
            "kind": "reject",
            "simulated_day": "2026-10-03",
        }
        state = {"actions": []}

        problem = decision_problem(decision, state)

        assert problem is not None
        assert "reason" in problem

    def test_decision_problem_approve_invalid_action(self):
        """Approve decision with invalid actionId is invalid."""
        decision = {
            "id": "decision_001",
            "kind": "approve",
            "simulated_day": "2026-10-03",
            "actionId": "invalid_action",
        }
        state = {"actions": [{"id": "a1"}]}

        problem = decision_problem(decision, state)

        assert problem is not None
        assert "no proposed action" in problem

    def test_decision_problem_valid_approve(self):
        """Valid approve decision passes."""
        decision = {
            "id": "decision_001",
            "kind": "approve",
            "simulated_day": "2026-10-03",
            "actionId": "a1",
        }
        state = {"actions": [{"id": "a1"}]}

        problem = decision_problem(decision, state)

        assert problem is None

    def test_decision_problem_request_changes_already_done(self):
        """Second request_changes is invalid."""
        decision = {
            "id": "decision_001",
            "kind": "request_changes",
            "simulated_day": "2026-10-03",
            "reason": "Try again",
        }
        state = {"actions": [], "proposal_returns": 1}

        problem = decision_problem(decision, state)

        assert problem is not None
        assert "already requested changes" in problem


class TestGraphState:
    """Tests for graph state management."""

    def test_state_status_transitions(self):
        """State transitions follow lifecycle."""
        tree = Tree(
            version=1,
            leyes=[],
            nodos=(
                Node(
                    id="detectar.raiz",
                    fundamento=None,
                    predicado=None,
                    si=None,
                    no=None,
                    hoja=Leaf(agente="vigia", decision="titular", skill="vigia/contrato.md"),
                    sigue="fin.sin_alerta",
                ),
            )
        )

        leaves = {("vigia", "titular"): lambda x: {"title": {"text": "Title", "figures": []}}}
        metrics = MagicMock(spec=Metrics)
        metrics.catalog = {}
        metrics.descriptions = {}
        catalog = MagicMock()
        catalog.columns = {}
        reader = MagicMock()
        classify = lambda x: "ninguno"
        checkpointer = InMemorySaver()

        compiler = Compiler(
            leaves=leaves,
            metrics=metrics,
            catalog=catalog,
            reader=reader,
            classify=classify,
            checkpointer=checkpointer,
        )

        graph = compiler.graph(tree)

        detection = Detection(
            entry="detectar.raiz",
            metric="test",
            entity=("e1",),
            path=[],
            row={},
        )

        state = start_alert(graph, detection, alert_id="a1", day="2026-10-03")

        assert state["status"] in ("nueva", "sin_alerta")
        assert len(state.get("transitions", [])) > 0


class TestGraphInterrupt:
    """Tests for interrupt at approval gate."""

    def test_gate_interrupt_constant(self):
        """GATE constant is set correctly."""
        from centinela_agents.graph import GATE as gate_from_graph
        from centinela_agents.schema import GATE as gate_from_schema

        assert gate_from_graph == gate_from_schema
        assert gate_from_graph == "aprobar.decision"
