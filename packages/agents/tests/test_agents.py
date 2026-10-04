"""
Tests for agent implementations.

Tests basic agent functionality without requiring full orchestrator.
"""

from unittest.mock import MagicMock, patch

import pytest

from centinela_agents.agents.analista import explain_cause
from centinela_agents.agents.ejecutor import execute_action
from centinela_agents.agents.estratega import propose_actions
from centinela_agents.agents.orquestador import classify_rejection
from centinela_agents.agents.vigia import redact_title
from centinela_agents.llm_provider import LLMResponse, LLMStructuredResponse, ModelConfig
from centinela_agents.schema import Figure
from centinela_agents.tools import ToolRegistry


class TestVigia:
    """Tests for Vigía agent."""

    def test_redact_title_success(self):
        """Vigía redacts title from detection."""
        provider = MagicMock()
        provider.generate_text.return_value = LLMResponse(
            text="Cliente cliente_123 tiene 45 días de retraso.",
            stop_reason="stop",
            usage={"prompt_tokens": 50, "completion_tokens": 10},
            model="qwen3:8b"
        )

        detection = {
            "metric": "saldo_vencido",
            "entity_type": "cliente_id",
            "entity": "cliente_123",
            "cifra": Figure(value=45, unit="days", queryId="q_dias_001"),
            "severity": "high",
        }

        result = redact_title(provider, detection)

        assert result["error"] is None
        assert "cliente_123" in result["title"]["text"]
        assert len(result["title"]["figures"]) > 0

    def test_redact_title_fallback(self):
        """Vigía falls back on LLM failure."""
        provider = MagicMock()
        provider.generate_text.side_effect = Exception("LLM error")

        detection = {
            "metric": "margen_pct",
            "entity_type": "linea",
            "entity": "linea_456",
            "cifra": Figure(value=3.5, unit="pts", queryId="q_margen"),
        }

        result = redact_title(provider, detection)

        assert result["error"] is not None
        assert "margen_pct" in result["title"]["text"]


class TestAnalista:
    """Tests for Analista agent."""

    def test_explain_cause_identified(self):
        """Analista returns identified cause."""
        provider = MagicMock()
        provider.generate_structured.return_value = LLMStructuredResponse(
            text='{"kind": "identified", "sentence": "Cliente acumula retraso", "evidence": []}',
            parsed={
                "kind": "identified",
                "sentence": "Cliente acumula retraso",
                "evidence": []
            },
            stop_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 20},
            model="qwen3:8b"
        )

        alert = {
            "metric": "saldo_vencido",
            "entity": "cliente_123",
            "day": "2026-10-03",
            "severity": "high",
        }

        tools = ToolRegistry()

        result = explain_cause(provider, alert, tools)

        assert result["error"] is None
        assert result["cause"]["kind"] == "identified"

    def test_explain_cause_no_evidence(self):
        """Analista returns no_evidence."""
        provider = MagicMock()
        provider.generate_structured.return_value = LLMStructuredResponse(
            text='{"kind": "no_evidence", "reason": "No data", "queriesReviewed": []}',
            parsed={
                "kind": "no_evidence",
                "reason": "No data",
                "queriesReviewed": []
            },
            stop_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 15},
            model="qwen3:8b"
        )

        alert = {
            "metric": "dias_pago_prom",
            "entity": "cliente_456",
            "day": "2026-10-03",
        }

        tools = ToolRegistry()

        result = explain_cause(provider, alert, tools)

        assert result["error"] is None
        assert result["cause"]["kind"] == "no_evidence"

    def test_explain_cause_fallback(self):
        """Analista falls back on LLM failure."""
        provider = MagicMock()
        provider.generate_structured.side_effect = Exception("LLM error")

        alert = {
            "metric": "cobertura_dias",
            "entity": "sku_789",
            "day": "2026-10-03",
        }

        tools = ToolRegistry()

        result = explain_cause(provider, alert, tools)

        assert result["error"] is not None
        assert result["cause"]["kind"] == "no_evidence"


class TestEstrategA:
    """Tests for Estratega agent."""

    def test_propose_actions_success(self):
        """Estratega proposes actions."""
        provider = MagicMock()
        provider.generate_structured.return_value = LLMStructuredResponse(
            text='{"actions": [{"id": "a1", "title": "Email", "description": "Send email", "type": "email_draft", "parameters": {"recipient": "c123"}, "confidence": {"level": "high"}}]}',
            parsed={
                "actions": [
                    {
                        "id": "a1",
                        "title": "Enviar recordatorio",
                        "description": "Email según FIN-POL-004 §4",
                        "type": "email_draft",
                        "parameters": {"recipient": "cliente_123"},
                        "impact": None,
                        "confidence": {"level": "high", "assumptions": []}
                    }
                ]
            },
            stop_reason="stop",
            usage={"prompt_tokens": 150, "completion_tokens": 30},
            model="qwen3:8b"
        )

        alert = {
            "metric": "saldo_vencido",
            "entity": "cliente_123",
            "day": "2026-10-03",
        }

        cause = {
            "kind": "identified",
            "sentence": "Cliente acumula retraso"
        }

        tools = ToolRegistry()

        result = propose_actions(provider, alert, cause, tools)

        assert result["error"] is None
        assert result["insufficient_cause"] is False
        assert len(result["actions"]) > 0

    def test_propose_actions_no_evidence(self):
        """Estratega returns insufficient_cause if no evidence."""
        provider = MagicMock()

        alert = {
            "metric": "margen_pct",
            "entity": "linea_456",
            "day": "2026-10-03",
        }

        cause = {
            "kind": "no_evidence",
            "reason": "No data"
        }

        tools = ToolRegistry()

        result = propose_actions(provider, alert, cause, tools)

        assert result["error"] is None
        assert result["insufficient_cause"] is True
        assert result["actions"] is None


class TestEjecutor:
    """Tests for Ejecutor agent."""

    def test_execute_task(self):
        """Ejecutor creates task."""
        provider = MagicMock()

        action = {
            "id": "a1",
            "type": "task",
            "title": "Revisar cliente",
            "parameters": {"owner": "Jefe de cartera", "cliente_id": "c123"}
        }

        decision = {
            "kind": "approve",
            "actionId": "a1",
            "parameters": {"owner": "Jefe de cartera", "cliente_id": "c123"}
        }

        tools = ToolRegistry()

        result = execute_action(provider, action, decision, tools)

        assert result["error"] is None
        assert result["executed_action"]["type"] == "task"
        assert result["executed_action"]["actionId"] == "a1"

    def test_execute_email_draft(self):
        """Ejecutor writes email body."""
        provider = MagicMock()
        provider.generate_text.return_value = MagicMock(
            text="Estimado cliente,\n\nSu factura tiene pendientes...",
        )

        action = {
            "id": "a2",
            "type": "email_draft",
            "title": "Email de cobro",
            "parameters": {"recipient": "cliente_123"}
        }

        decision = {
            "kind": "approve",
            "actionId": "a2",
            "parameters": {"recipient": "cliente_123"}
        }

        tools = ToolRegistry()

        result = execute_action(provider, action, decision, tools)

        assert result["error"] is None
        assert result["executed_action"]["type"] == "email_draft"
        assert "Estimado" in result["executed_action"]["result"]


class TestOrquestador:
    """Tests for Orquestador classifier."""

    def test_classify_rejection_causa(self):
        """Classify rejection as about cause."""
        provider = MagicMock()
        provider.generate_structured.return_value = LLMStructuredResponse(
            text='{"destino": "causa"}',
            parsed={"destino": "causa"},
            stop_reason="stop",
            usage={"prompt_tokens": 80, "completion_tokens": 5},
            model="qwen3:8b"
        )

        reason = "Los datos de retraso no son correctos"
        cause = {
            "kind": "identified",
            "sentence": "Cliente tiene 45 días de retraso"
        }
        actions = [{"title": "Email", "type": "email_draft"}]

        result = classify_rejection(provider, reason, cause, actions)

        assert result["error"] is None
        assert result["destino"] == "causa"

    def test_classify_rejection_propuesta(self):
        """Classify rejection as about proposal."""
        provider = MagicMock()
        provider.generate_structured.return_value = LLMStructuredResponse(
            text='{"destino": "propuesta"}',
            parsed={"destino": "propuesta"},
            stop_reason="stop",
            usage={"prompt_tokens": 80, "completion_tokens": 5},
            model="qwen3:8b"
        )

        reason = "No envíes email; mejor una llamada"
        cause = {
            "kind": "identified",
            "sentence": "Cliente tiene retraso"
        }
        actions = [{"title": "Email", "type": "email_draft"}]

        result = classify_rejection(provider, reason, cause, actions)

        assert result["error"] is None
        assert result["destino"] == "propuesta"

    def test_classify_rejection_ninguno(self):
        """Classify rejection as neither."""
        provider = MagicMock()
        provider.generate_structured.return_value = LLMStructuredResponse(
            text='{"destino": "ninguno"}',
            parsed={"destino": "ninguno"},
            stop_reason="stop",
            usage={"prompt_tokens": 80, "completion_tokens": 5},
            model="qwen3:8b"
        )

        reason = "Por ahora no vamos a hacer nada"
        cause = {"kind": "identified", "sentence": "Retraso"}
        actions = [{"title": "Email", "type": "email_draft"}]

        result = classify_rejection(provider, reason, cause, actions)

        assert result["error"] is None
        assert result["destino"] == "ninguno"

    def test_classify_rejection_fallback(self):
        """Fallback on LLM failure."""
        provider = MagicMock()
        provider.generate_structured.side_effect = Exception("LLM error")

        reason = "Algún motivo"
        cause = {"kind": "identified", "sentence": "Causa"}
        actions = []

        result = classify_rejection(provider, reason, cause, actions)

        assert result["error"] is not None
        assert result["destino"] == "ninguno"
