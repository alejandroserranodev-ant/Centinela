from unittest.mock import MagicMock, patch

import pytest

from langgraph.checkpoint.memory import InMemorySaver

from centinela_agents.day import AlertRun, Verdict
from centinela_agents.graph import GATE, classified
from centinela_agents.llm_provider import LLMResponse, LLMStructuredResponse
from centinela_agents.metrics import Metrics, load_metrics
from centinela_agents.orchestrator import CentinelaOrchestrator
from centinela_agents.action_tools import TaskStub
from centinela_agents.tools import ToolRegistry
from centinela_agents.walk import Context
from support import DAY, DECISION_DAY, EMAIL, IDENTIFIED, KERNEL_CATALOG, METRICAS, SALDO_ROW, approve, base_tree, reader_from, saldo_detection, split_tree

STATE = {
    "alert_id": "A1",
    "decision": {"id": "dec-1", "kind": "reject", "reason": "La cifra de mora está mal", "simulated_day": "2026-10-04"},
    "cause": {"kind": "identified", "sentence": "El cliente paga tarde"},
    "actions": [{"title": "Correo", "type": "email_draft"}],
}


def wired_classifier(destino):
    provider = MagicMock()
    provider.generate_structured.return_value = LLMStructuredResponse(
        text=f'{{"destino": "{destino}"}}', parsed={"destino": destino}, stop_reason="stop", usage={}, model="m",
    )
    with patch("centinela_agents.orchestrator.Compiler") as compiler:
        CentinelaOrchestrator(provider=provider, tools=MagicMock(), tree=MagicMock(), metrics=Metrics(descriptions={}, thresholds={}), catalog=MagicMock(), reader=MagicMock(), checkpointer=MagicMock())
    return provider, compiler.call_args.kwargs["classify"]


def test_the_classifier_the_orchestrator_wires_returns_the_model_target():
    for destino in ("causa", "propuesta", "ambos", "ninguno"):
        _, classify = wired_classifier(destino)
        assert classified(classify, STATE) == destino


def test_the_classifier_hands_the_model_the_reason_the_cause_and_the_actions():
    provider, classify = wired_classifier("causa")
    classify(STATE)
    prompt = provider.generate_structured.call_args.args[0].user_prompt
    assert "La cifra de mora está mal" in prompt
    assert "El cliente paga tarde" in prompt
    assert "Correo" in prompt


def paused_saldo_alert():
    provider = MagicMock()
    provider.generate_text.return_value = LLMResponse(text="Cartera vencida", stop_reason="stop", usage={}, model="m")
    provider.generate_structured.side_effect = RuntimeError("sin modelo")
    orchestrator = CentinelaOrchestrator(
        provider=provider,
        tools=ToolRegistry(task=TaskStub()),
        tree=base_tree(),
        metrics=load_metrics(METRICAS),
        catalog=KERNEL_CATALOG,
        reader=reader_from({DAY: {"saldo_vencido": [SALDO_ROW]}, DECISION_DAY: {"saldo_vencido": [SALDO_ROW]}}),
        checkpointer=InMemorySaver(),
    )
    state = orchestrator.start(saldo_detection(), alert_id="A1", day=DAY)
    return orchestrator, state["actions"][0]["id"]


def test_the_approval_recheck_reads_the_thresholds_the_orchestrator_was_built_with():
    orchestrator, action_id = paused_saldo_alert()
    assert ["ejecutar.vigente", "si"] in orchestrator.resume("A1", approve(action_id=action_id))["camino"]


def test_use_thresholds_swaps_what_the_recheck_reads_and_keeps_the_graph_and_the_paused_alert():
    orchestrator, action_id = paused_saldo_alert()
    graph = orchestrator.graph
    orchestrator.use_thresholds({"saldo_vencido": {"max_dias_vencido": 30, "saldo_abierto": {"columna": "cupo_credito"}}})
    assert orchestrator.graph is graph
    assert orchestrator.is_awaiting_decision("A1")
    assert orchestrator.metrics.thresholds["saldo_vencido"]["max_dias_vencido"] == 30
    assert orchestrator.metrics.thresholds["margen_pct"]["caida_pts"] == 3
    state = orchestrator.resume("A1", approve(action_id=action_id))
    assert state["fin"] == "fin.ya_no_aplica"
    assert state.get("executed_action") is None


def test_a_paused_alert_resumes_on_the_graph_of_the_version_it_started_on():
    orchestrator, action_id = paused_saldo_alert()
    first = orchestrator.graph
    orchestrator.use_tree(split_tree().model_copy(update={"version": 2}))
    assert orchestrator.graph is not first
    assert orchestrator.graph_of("A1") is first
    assert orchestrator.get_state("A1")["arbol_version"] == 1
    assert orchestrator.is_awaiting_decision("A1")
    assert ["ejecutar.vigente", "si"] in orchestrator.resume("A1", approve(action_id=action_id))["camino"]
    assert orchestrator.start(saldo_detection(), alert_id="A2", day=DAY)["arbol_version"] == 2


def test_run_day_walks_the_tree_in_use_whatever_tree_its_context_carries():
    orchestrator, _ = paused_saldo_alert()
    orchestrator.use_tree(base_tree().model_copy(update={"version": 5}))
    ctx = Context.of(base_tree(), load_metrics(METRICAS), KERNEL_CATALOG, reader_from({DAY: {"saldo_vencido": [SALDO_ROW]}}))
    run, sent, states = orchestrator.run_day(ctx, DAY), None, []
    while True:
        try:
            event = run.send(sent)
        except StopIteration:
            break
        sent = Verdict(recorded=True) if isinstance(event, AlertRun) else None
        if isinstance(event, AlertRun):
            states.append(event.state)
    assert [state["arbol_version"] for state in states] == [5]


def test_a_request_for_changes_returns_a_paused_alert_through_the_nodes_of_its_own_version(monkeypatch):
    monkeypatch.setattr("centinela_agents.orchestrator.rejection_target", lambda provider, state: "propuesta")
    split = "proponer.cartera.saldo_vencido.division_1"
    monkeypatch.setattr("centinela_agents.orchestrator.explain_cause", lambda provider, state, sources: {"cause": IDENTIFIED, "same_cause_as": None})
    monkeypatch.setattr("centinela_agents.orchestrator.propose_actions", lambda provider, state, cause, sources: {"actions": [EMAIL], "insufficient_cause": None})
    orchestrator, _ = paused_saldo_alert()
    orchestrator.use_tree(split_tree().model_copy(update={"version": 2}))
    reject = {"id": "dec-1", "kind": "request_changes", "reason": "La propuesta no sirve", "simulated_day": DECISION_DAY}
    returned = orchestrator.resume("A1", reject)
    walked = [node for node, _ in returned["camino"]]
    assert "hoja.estratega.proponer" in walked[walked.index(GATE):]
    assert returned["arbol_version"] == 1
    assert split not in walked
    assert split in [node for node, _ in orchestrator.start(saldo_detection(), alert_id="A2", day=DAY)["camino"]]


def test_use_tree_points_the_sources_at_the_nodes_of_the_tree_in_use():
    orchestrator, _ = paused_saldo_alert()
    split = "proponer.cartera.saldo_vencido.division_1"
    assert split not in orchestrator.sources.nodes
    orchestrator.use_tree(split_tree().model_copy(update={"version": 2}))
    assert split in orchestrator.sources.nodes


def test_an_alert_that_started_on_a_version_the_orchestrator_does_not_hold_has_no_paused_graph():
    orchestrator, action_id = paused_saldo_alert()
    orchestrator._graphs.clear()
    assert orchestrator.graph_of("A1") is None
    assert not orchestrator.is_awaiting_decision("A1")
    assert orchestrator.get_state("A1") == {}
    with pytest.raises(LookupError):
        orchestrator.resume("A1", approve(action_id=action_id))
