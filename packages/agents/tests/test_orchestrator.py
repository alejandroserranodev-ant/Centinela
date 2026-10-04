from unittest.mock import MagicMock, patch

from centinela_agents.graph import classified
from centinela_agents.llm_provider import LLMStructuredResponse
from centinela_agents.orchestrator import CentinelaOrchestrator

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
        CentinelaOrchestrator(provider=provider, tools=MagicMock(), tree=MagicMock(), metrics=MagicMock(), catalog=MagicMock(), reader=MagicMock(), checkpointer=MagicMock())
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
