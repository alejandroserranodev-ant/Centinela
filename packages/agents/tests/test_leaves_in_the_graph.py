from unittest.mock import MagicMock

from langgraph.checkpoint.memory import InMemorySaver

import pytest

from centinela_agents.agents.analista import explain_cause
from centinela_agents.agents.ejecutor import execute_action
from centinela_agents.agents.estratega import propose_actions
from centinela_agents.agents.vigia import redact_title
from centinela_agents.evidence import Sources, call_from_reader
from centinela_agents.graph import StartRefused
from centinela_agents.llm_provider import LLMResponse, LLMStructuredResponse
from centinela_agents.schema import index
from centinela_agents.metrics import load_metrics
from centinela_agents.orchestrator import CentinelaOrchestrator
from centinela_agents.state import AlertState
from centinela_agents.tools import ToolRegistry
from support import DAY, EMAIL, IDENTIFIED, KERNEL_CATALOG, METRICAS, SALDO_ROW, approve, base_tree, reader_from, saldo_detection


def started():
    provider = MagicMock()
    provider.generate_text.return_value = LLMResponse(text="Cartera vencida del cliente CLI-001.", stop_reason="stop", usage={}, model="m")
    provider.generate_structured.side_effect = RuntimeError("sin modelo")
    orchestrator = CentinelaOrchestrator(
        provider=provider,
        tools=ToolRegistry(),
        tree=base_tree(),
        metrics=load_metrics(METRICAS),
        catalog=KERNEL_CATALOG,
        reader=reader_from({DAY: {"saldo_vencido": [SALDO_ROW]}}),
        checkpointer=InMemorySaver(),
    )
    state = orchestrator.start(saldo_detection(), alert_id="A1", day=DAY)
    return provider, state


def prompts(mock_method):
    return [call.args[0].user_prompt for call in mock_method.call_args_list]


def test_vigia_prompts_with_the_metric_and_entity_of_the_detection():
    provider, _ = started()
    (prompt,) = prompts(provider.generate_text)
    assert "saldo_vencido" in prompt
    assert "CLI-001" in prompt
    assert "None" not in prompt


def test_analista_and_estratega_prompt_with_the_metric_entity_and_day_of_the_alert():
    provider, _ = started()
    analista, *estratega = prompts(provider.generate_structured)
    for prompt in (analista, *estratega):
        assert "saldo_vencido" in prompt
        assert "CLI-001" in prompt
        assert "None" not in prompt
    assert DAY in analista


def test_the_leaves_write_only_keys_the_state_declares():
    _, state = started()
    assert set(state) <= set(AlertState.__annotations__)


@pytest.mark.parametrize("fails", [False, True])
def test_each_leaf_returns_only_keys_the_state_declares(fails):
    provider = MagicMock()
    provider.generate_text.return_value = LLMResponse(text="Borrador.", stop_reason="stop", usage={}, model="m")
    provider.generate_structured.return_value = LLMStructuredResponse(
        text="{}", parsed={"kind": "no_evidence", "reason": "Nada.", "actions": [], "insufficient_cause": True}, stop_reason="stop", usage={}, model="m"
    )
    if fails:
        provider.generate_text.side_effect = RuntimeError("sin modelo")
        provider.generate_structured.side_effect = RuntimeError("sin modelo")
    _, state = started()
    sources = Sources(call_from_reader(reader_from({DAY: {"saldo_vencido": [SALDO_ROW]}})), KERNEL_CATALOG, load_metrics(METRICAS), index(base_tree()))
    leaves = [
        lambda: redact_title(provider, state, sources),
        lambda: explain_cause(provider, state, sources),
        lambda: propose_actions(provider, state, IDENTIFIED, sources),
        lambda: execute_action(provider, EMAIL, approve(), ToolRegistry()),
    ]
    for leaf in leaves:
        try:
            output = leaf()
        except Exception:
            assert fails
            continue
        assert set(output) <= set(AlertState.__annotations__)


def same_cause_orchestrator(named_in_order):
    named = iter(named_in_order)

    def structured(request):
        if "same_cause_as" not in request.schema.get("properties", {}):
            raise RuntimeError("sin modelo")
        parsed = {
            "kind": "identified",
            "sentence": "La mora coincide con el saldo vencido: {0}.",
            "sentence_figures": ["f1"],
            "evidence": [{"claim": "El saldo vencido es {0}.", "figures": ["f1"]}],
            "confidence": "medium",
            "assumptions": [],
            "same_cause_as": next(named),
        }
        return LLMStructuredResponse(text="{}", parsed=parsed, stop_reason="stop", usage={}, model="m")

    provider = MagicMock()
    provider.generate_text.return_value = LLMResponse(text="Cartera vencida del cliente CLI-001.", stop_reason="stop", usage={}, model="m")
    provider.generate_structured.side_effect = structured
    return CentinelaOrchestrator(
        provider=provider,
        tools=ToolRegistry(),
        tree=base_tree(),
        metrics=load_metrics(METRICAS),
        catalog=KERNEL_CATALOG,
        reader=reader_from({DAY: {"saldo_vencido": [SALDO_ROW]}}),
        checkpointer=InMemorySaver(),
    )


def test_three_alerts_of_one_cause_end_as_one_that_remains_and_two_unida():
    orchestrator = same_cause_orchestrator(["C1", "B1"])
    briefs = {"C1": {"metric": "dias_pago_prom", "entity": ["CLI-001"], "cause": None}}
    first = orchestrator.start(saldo_detection(), alert_id="B1", day=DAY, earlier_alerts={"C1": "nueva"}, alert_briefs=briefs)
    assert first["same_cause_as"] == "C1"
    assert first["merged_alerts"] == ["C1"]
    assert ["C1", "unida"] in first["transitions"]
    assert orchestrator.is_awaiting_decision("B1")
    second = orchestrator.start(saldo_detection(), alert_id="A1", day=DAY, earlier_alerts={"B1": "propuesta"}, alert_briefs={"B1": {"metric": "dias_pago_prom", "entity": ["CLI-001"], "cause": first["cause"]["sentence"]}})
    assert second["fin"] == "fin.unida"
    assert second["merged_into"] == "B1"
    assert [status for alert, status in second["transitions"] if alert == "A1"] == ["nueva", "en análisis", "unida"]
    assert not orchestrator.is_awaiting_decision("A1")


def test_a_start_again_on_an_ended_alert_runs_clean_without_the_refused_target():
    orchestrator = same_cause_orchestrator(["B1", None])
    briefs = {"B1": {"metric": "dias_pago_prom", "entity": ["CLI-001"], "cause": None}}
    merged = orchestrator.start(saldo_detection(), alert_id="A1", day=DAY, earlier_alerts={"B1": "propuesta"}, alert_briefs=briefs)
    assert merged["fin"] == "fin.unida"
    again = orchestrator.start(saldo_detection(), alert_id="A1", day=DAY, earlier_alerts={}, alert_briefs={})
    assert again["same_cause_as"] is None
    assert again.get("merged_into") is None and again.get("fin") is None
    assert again["transitions"] == [["A1", "nueva"], ["A1", "en análisis"], ["A1", "propuesta"]]
    assert orchestrator.is_awaiting_decision("A1")


def test_a_start_on_an_alert_that_awaits_a_decision_is_refused():
    orchestrator = same_cause_orchestrator([None])
    orchestrator.start(saldo_detection(), alert_id="A1", day=DAY)
    with pytest.raises(StartRefused):
        orchestrator.start(saldo_detection(), alert_id="A1", day=DAY)
    assert orchestrator.is_awaiting_decision("A1")
