"""Integration tests for Phase 9: Observability + Validation integration."""

import pytest
from unittest.mock import MagicMock, patch

from centinela_agents.output_validator import (
    OutputValidator,
    OutputValidationError,
)
from centinela_agents.schema import (
    CauseIdentified,
    CauseNoEvidence,
    Action,
    ExecutedAction,
    Decision,
    RejectionClassifierOutput,
    Figure,
    Evidence,
    Confidence,
)
from centinela_agents.observability import MetricsCollector, TokenUsage


class TestOutputValidator:
    """Test OutputValidator with all agent outputs."""

    def test_validator_init(self):
        """Initialize validator."""
        validator = OutputValidator(strict=True)
        assert validator.strict is True

    def test_validator_init_non_strict(self):
        """Initialize validator in non-strict mode."""
        validator = OutputValidator(strict=False)
        assert validator.strict is False

    def test_validate_cause_identified_valid(self):
        """Validate valid identified cause."""
        validator = OutputValidator()
        output = {
            "kind": "identified",
            "sentence": "AWS pricing increased 15%",
            "evidence": [
                {
                    "claim": "Price change observed",
                    "figures": [
                        {"value": 15, "unit": "%", "queryId": "q1"}
                    ]
                }
            ]
        }

        cause = validator.validate_cause(output)
        assert cause.kind == "identified"

    def test_validate_cause_no_evidence_valid(self):
        """Validate valid no_evidence cause."""
        validator = OutputValidator()
        output = {
            "kind": "no_evidence",
            "reason": "Insufficient data to determine root cause",
            "queriesReviewed": ["q1", "q2"]
        }

        cause = validator.validate_cause(output)
        assert cause.kind == "no_evidence"

    def test_validate_cause_invalid_schema(self):
        """Reject cause with missing required field."""
        validator = OutputValidator(strict=True)
        output = {
            "kind": "identified",
            "sentence": "Test",
        }

        with pytest.raises(OutputValidationError) as exc_info:
            validator.validate_cause(output)
        assert exc_info.value.category == "schema"

    def test_validate_cause_security_issue(self):
        """Reject cause with security issues."""
        validator = OutputValidator(strict=True)
        output = {
            "kind": "identified",
            "sentence": "Test {placeholder} not filled",
            "evidence": [
                {
                    "claim": "Some claim",
                    "figures": [{"value": 10, "unit": "%", "queryId": "q1"}]
                }
            ]
        }

        with pytest.raises(OutputValidationError) as exc_info:
            validator.validate_cause(output)
        assert exc_info.value.category == "security"

    def test_validate_action_valid(self):
        """Validate valid action."""
        validator = OutputValidator()
        output = {
            "id": "action-1",
            "title": "Downsize EC2 instances",
            "description": "Section 3.2: reduce instance size",
            "type": "email_draft",
            "parameters": {"recipient": "ops@company.com"},
            "confidence": {
                "level": "high",
                "assumptions": []
            }
        }

        action = validator.validate_action(output)
        assert action.id == "action-1"

    def test_validate_action_invalid_type(self):
        """Reject action with invalid type."""
        validator = OutputValidator(strict=True)
        output = {
            "id": "action-1",
            "title": "Test",
            "description": "Test action",
            "type": "invalid_type",
            "parameters": {},
            "confidence": {"level": "low"}
        }

        with pytest.raises(OutputValidationError) as exc_info:
            validator.validate_action(output)
        assert exc_info.value.category == "schema"

    def test_validate_executed_action_valid(self):
        """Validate valid executed action."""
        validator = OutputValidator()
        output = {
            "actionId": "action-1",
            "type": "task",
            "result": "Created JIRA task OPS-123",
            "parameters": {"assigned_to": "ops-team"}
        }

        executed = validator.validate_executed_action(output)
        assert executed.type == "task"

    def test_validate_decision_valid(self):
        """Validate valid decision."""
        validator = OutputValidator()
        output = {
            "kind": "approve",
            "actionId": "action-1"
        }

        decision = validator.validate_decision(output)
        assert decision.kind == "approve"

    def test_validate_decision_invalid_kind(self):
        """Reject decision with invalid kind."""
        validator = OutputValidator()
        output = {
            "kind": "invalid_kind"
        }

        with pytest.raises(OutputValidationError) as exc_info:
            validator.validate_decision(output)
        assert exc_info.value.category == "schema"

    def test_validate_rejection_classifier_valid(self):
        """Validate valid rejection classifier."""
        validator = OutputValidator()
        output = {
            "destino": "ambos"
        }

        classifier = validator.validate_rejection_classifier(output)
        assert classifier.destino == "ambos"

    def test_validate_rejection_classifier_all_destinos(self):
        """Validate all valid destino values."""
        validator = OutputValidator()

        for destino in ["causa", "propuesta", "ambos", "ninguno"]:
            classifier = validator.validate_rejection_classifier({"destino": destino})
            assert classifier.destino == destino


class TestMetricsCollectionIntegration:
    """Test integration of MetricsCollector with validators."""

    def test_metrics_with_single_agent(self):
        """Record metrics for single agent."""
        collector = MetricsCollector(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            model="gpt-4o-mini",
            provider="openai"
        )

        collector.record_agent_call("Vigía", usage, 150.0)
        collector.finish("completed")

        summary = collector.get_summary()
        assert summary["total_calls"] == 1
        assert summary["total_tokens"] == 150
        assert summary["status"] == "completed"

    def test_metrics_with_multiple_agents(self):
        """Record metrics for multiple agents."""
        collector = MetricsCollector(
            alert_id="alert-456",
            metric="spend_spike",
            entity="customer-2",
            day="2026-10-03"
        )

        usage1 = TokenUsage(100, 50, "gpt-4o-mini", "openai")
        usage2 = TokenUsage(200, 100, "gpt-4o-mini", "openai")

        collector.record_agent_call("Vigía", usage1, 150.0)
        collector.record_agent_call("Analista", usage2, 200.0)
        collector.record_retry("Vigía")
        collector.record_failure("Analista")

        collector.finish("completed")

        summary = collector.get_summary()
        assert summary["total_calls"] == 2
        assert summary["total_tokens"] == 450
        assert summary["agents"]["Vigía"]["retries"] == 1
        assert summary["agents"]["Analista"]["failures"] == 1

    def test_metrics_cost_tracking(self):
        """Track costs across agents."""
        collector = MetricsCollector(
            alert_id="alert-789",
            metric="test",
            entity="test",
            day="2026-10-03"
        )

        openai_usage = TokenUsage(100, 50, "gpt-4o-mini", "openai")
        collector.record_agent_call("Agent1", openai_usage, 100.0)

        ollama_usage = TokenUsage(200, 100, "llama2", "ollama")
        collector.record_agent_call("Agent2", ollama_usage, 200.0)

        collector.finish()

        summary = collector.get_summary()
        assert summary["total_cost_usd"] > 0
        assert summary["agents"]["Agent2"]["cost_usd"] == 0.0

    def test_metrics_with_error_handling(self):
        """Handle retries and failures in metrics."""
        collector = MetricsCollector(
            alert_id="alert-error",
            metric="test",
            entity="test",
            day="2026-10-03"
        )

        usage = TokenUsage(100, 50, "gpt-4o-mini", "openai")

        collector.record_failure("Agent")

        collector.record_retry("Agent")

        collector.record_retry("Agent")

        collector.record_agent_call("Agent", usage, 300.0)

        collector.finish("completed")

        summary = collector.get_summary()
        assert summary["agents"]["Agent"]["failures"] == 1
        assert summary["agents"]["Agent"]["retries"] == 2
        assert summary["agents"]["Agent"]["calls"] == 1


class TestValidatorErrorHandling:
    """Test error handling in validators."""

    def test_strict_mode_fails_on_error(self):
        """Strict mode raises on validation error."""
        validator = OutputValidator(strict=True)
        invalid_cause = {
            "kind": "identified",
            "sentence": "Test",
        }

        with pytest.raises(OutputValidationError):
            validator.validate_cause(invalid_cause)

    def test_non_strict_mode_logs_warning(self, caplog):
        """Non-strict mode logs warning instead of raising."""
        validator = OutputValidator(strict=False)
        invalid_cause = {
            "kind": "identified",
            "sentence": "Test",
        }

        result = validator.validate_cause(invalid_cause)
        assert result is None
        assert len(caplog.records) > 0

    def test_validation_error_contains_category(self):
        """ValidationError includes category info."""
        validator = OutputValidator(strict=True)

        try:
            validator.validate_cause({"kind": "invalid_kind", "sentence": "test"})
        except OutputValidationError as e:
            assert e.category in ["schema", "security", "domain", "hallucination"]
            assert hasattr(e, "message")
            assert hasattr(e, "output")


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_full_alert_flow_with_metrics(self):
        """Complete alert processing with metrics collection."""
        collector = MetricsCollector(
            alert_id="e2e-alert-1",
            metric="cost_anomaly",
            entity="customer-acme",
            day="2026-10-03"
        )
        validator = OutputValidator(strict=False)

        vigia_usage = TokenUsage(100, 50, "gpt-4o-mini", "openai")
        collector.record_agent_call("Vigía", vigia_usage, 150.0)

        analista_output = {
            "kind": "identified",
            "sentence": "Pricing change detected",
            "evidence": [{
                "claim": "15% price increase",
                "figures": [{"value": 15, "unit": "%", "queryId": "q1"}]
            }]
        }
        cause = validator.validate_cause(analista_output)
        analista_usage = TokenUsage(200, 100, "gpt-4o-mini", "openai")
        collector.record_agent_call("Analista", analista_usage, 200.0)

        action_output = {
            "id": "a1",
            "title": "Downsize instances",
            "description": "Section 3.2",
            "type": "email_draft",
            "parameters": {"recipient": "ops@company.com"},
            "confidence": {"level": "high"}
        }
        action = validator.validate_action(action_output)
        estratega_usage = TokenUsage(150, 75, "gpt-4o-mini", "openai")
        collector.record_agent_call("Estratega", estratega_usage, 180.0)

        collector.finish("completed")

        summary = collector.get_summary()
        assert summary["total_calls"] == 3
        assert len(summary["agents"]) == 3
        assert summary["status"] == "completed"
        assert summary["total_cost_usd"] > 0
