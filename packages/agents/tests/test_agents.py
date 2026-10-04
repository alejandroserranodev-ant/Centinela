"""
Tests for agent implementations.

Tests basic agent functionality without requiring full orchestrator.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from centinela_agents.agents.analista import explain_cause
from centinela_agents.agents.ejecutor import execute_action
from centinela_agents.agents.estratega import propose_actions
from centinela_agents.agents.orquestador import classify_rejection
from centinela_agents.agents.vigia import redact_title
from centinela_agents.llm_provider import LLMResponse, LLMStructuredResponse, ModelConfig
from centinela_agents.evidence import Sources, query_id
from centinela_agents.failures import SchemaRefused
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import index
from centinela_agents.tools import ToolRegistry
from support import KERNEL_CATALOG, METRICAS, base_tree


DAY = "2026-10-03"
ROWS = {
    "saldo_vencido": [{"cliente_id": "C1", "saldo_vencido": 800000.0, "saldo_abierto": 1200000.0, "max_dias_vencido": 45, "cupo_credito": 5000000, "pesos_en_riesgo": 800000.0}],
    "dias_pago_prom": [{"cliente_id": "C1", "dias_pago_prom": 52.0, "dias_pago_prom_base": 30.0, "aumento_pct": 73.3, "pesos_en_riesgo": 0.0}],
    "concentracion_vencida_pct": [{"cliente_id": "C2", "saldo_vencido": 1.0, "concentracion_vencida_pct": 9.0, "pesos_en_riesgo": 1.0}],
}
DETECTION = {
    "metric": "saldo_vencido",
    "entity": ["C1"],
    "path": [["detectar.cartera.saldo_vencido.dias", "si"]],
    "row": ROWS["saldo_vencido"][0],
}
STATE = {"alert_id": "A1", "detection": DETECTION, "simulated_day": DAY}


def kernel(name, arguments):
    kpi = arguments["kpi"]
    return {"kpi": kpi, "dia": arguments["dia"], "consulta": f"SELECT * FROM k_{kpi}(%(dia)s)", "filas": ROWS.get(kpi, [])}


def sources():
    return Sources(kernel, KERNEL_CATALOG, load_metrics(METRICAS), index(base_tree()))


def structured(parsed):
    return LLMStructuredResponse(text=json.dumps(parsed), parsed=parsed, stop_reason="stop", usage={}, model="m")


def saldo_query():
    return query_id("SELECT * FROM k_saldo_vencido(%(dia)s)", DAY)


class TestVigia:
    """Tests for Vigía agent."""

    def test_the_title_cites_the_kernel_figures_with_their_query(self):
        provider = MagicMock()
        provider.generate_text.return_value = LLMResponse(text="El cliente C1 tiene {0} días de mora y {1} en riesgo.", stop_reason="stop", usage={}, model="m")

        result = redact_title(provider, STATE, sources())

        figures = result["title"]["figures"]
        assert [figure["value"] for figure in figures] == [45, 800000.0]
        assert {figure["queryId"] for figure in figures} == {saldo_query()}
        assert result["queries"][0]["consulta"] == "SELECT * FROM k_saldo_vencido(%(dia)s)"
        prompt = provider.generate_text.call_args.args[0].user_prompt
        assert "saldo_vencido" in prompt and "C1" in prompt

    def test_a_placeholder_with_no_figure_is_refused(self):
        provider = MagicMock()
        provider.generate_text.return_value = LLMResponse(text="Mora de {7} días.", stop_reason="stop", usage={}, model="m")

        with pytest.raises(SchemaRefused):
            redact_title(provider, STATE, sources())


class TestAnalista:
    """Tests for Analista agent."""

    def test_the_cause_cites_facts_the_kernel_returned(self):
        provider = MagicMock()
        provider.generate_structured.return_value = structured(
            {
                "kind": "identified",
                "sentence": "La mora coincide con pagos más lentos: {0} días.",
                "sentence_figures": ["f6"],
                "evidence": [{"claim": "El promedio de pago subió a {0} días.", "figures": ["f6"]}],
                "confidence": "medium",
                "assumptions": [],
            }
        )

        result = explain_cause(provider, STATE, sources())

        cause = result["cause"]
        assert cause["kind"] == "identified"
        assert cause["sentence"]["figures"][0]["value"] == 52.0
        assert cause["evidence"][0]["figures"][0]["queryId"] == query_id("SELECT * FROM k_dias_pago_prom(%(dia)s)", DAY)
        prompt = provider.generate_structured.call_args.args[0].user_prompt
        assert "dias_pago_prom.dias_pago_prom de C1 = 52.0" in prompt
        assert "C2" not in prompt
        assert {query["kpi"] for query in result["queries"]} >= {"saldo_vencido", "dias_pago_prom"}

    def test_a_cited_fact_no_query_returned_is_refused(self):
        provider = MagicMock()
        provider.generate_structured.return_value = structured(
            {"kind": "identified", "sentence": "x {0}", "sentence_figures": ["f99"], "evidence": [{"claim": "x {0}", "figures": ["f99"]}], "confidence": "low"}
        )

        with pytest.raises(SchemaRefused):
            explain_cause(provider, STATE, sources())

    def test_a_figure_written_outside_a_placeholder_is_refused(self):
        provider = MagicMock()
        provider.generate_structured.return_value = structured(
            {"kind": "identified", "sentence": "Paga en 52 días.", "sentence_figures": ["f6"], "evidence": [], "confidence": "low"}
        )

        with pytest.raises(SchemaRefused):
            explain_cause(provider, STATE, sources())

    def test_a_claim_with_a_written_figure_is_dropped_and_the_sentence_stands_in(self):
        provider = MagicMock()
        provider.generate_structured.return_value = structured(
            {
                "kind": "identified",
                "sentence": "La mora de C1 coincide con pagos a {0} días.",
                "sentence_figures": ["f6"],
                "evidence": [{"claim": "Subió 73 por ciento.", "figures": ["f8"]}],
                "confidence": "low",
            }
        )

        cause = explain_cause(provider, STATE, sources())["cause"]

        assert [item["claim"] for item in cause["evidence"]] == ["La mora de C1 coincide con pagos a {0} días."]

    def test_no_evidence_lists_every_query_reviewed(self):
        provider = MagicMock()
        provider.generate_structured.return_value = structured({"kind": "no_evidence", "reason": "Nada coincide.", "confidence": "low"})

        result = explain_cause(provider, STATE, sources())

        assert result["cause"]["kind"] == "no_evidence"
        assert saldo_query() in result["cause"]["queriesReviewed"]


class TestEstrategA:
    """Tests for Estratega agent."""

    def test_the_action_takes_its_parameters_and_impact_from_the_kpi(self):
        provider = MagicMock()
        provider.generate_structured.return_value = structured(
            {"actions": [{"row": "r1", "title": "Recordatorio de pago", "description": "Enviar un recordatorio cortés."}], "insufficient_cause": False}
        )

        result = propose_actions(provider, STATE, {"kind": "identified", "sentence": "Paga tarde", "confidence": {"level": "high"}}, sources())

        (action,) = result["actions"]
        assert action["id"] == "act-saldo_vencido-r1"
        assert action["type"] == "email_draft"
        assert action["parameters"] == {"recipient": "C1"}
        assert action["impact"] == {"value": 800000.0, "unit": "COP", "queryId": saldo_query()}
        assert result["insufficient_cause"] is None

    def test_a_row_the_list_does_not_hold_is_insufficient(self):
        provider = MagicMock()
        provider.generate_structured.return_value = structured({"actions": [{"row": "r99", "title": "x", "description": "y"}], "insufficient_cause": False})

        result = propose_actions(provider, STATE, {"kind": "identified", "sentence": "Paga tarde"}, sources())

        assert result["actions"] is None
        assert result["insufficient_cause"] is True

    def test_propose_actions_no_evidence(self):
        provider = MagicMock()

        result = propose_actions(provider, STATE, {"kind": "no_evidence", "reason": "Sin datos"}, sources())

        assert result["insufficient_cause"] is True
        provider.generate_structured.assert_not_called()


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
