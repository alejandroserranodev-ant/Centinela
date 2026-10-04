from unittest.mock import MagicMock, patch

from langgraph.checkpoint.memory import InMemorySaver

from centinela_agents.graph import classified
from centinela_agents.llm_provider import LLMResponse, LLMStructuredResponse
from centinela_agents.metrics import Metrics, load_metrics
from centinela_agents.orchestrator import CentinelaOrchestrator
from centinela_agents.action_tools import TaskStub
from centinela_agents.tools import ToolRegistry
from support import DAY, DECISION_DAY, KERNEL_CATALOG, METRICAS, SALDO_ROW, approve, base_tree, reader_from, saldo_detection

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
