"""Tests for observability: cost tracking, metrics, Langfuse integration."""

import json
import logging
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from centinela_agents.observability import (
    TokenUsage,
    AgentMetrics,
    AlertMetrics,
    MetricsCollector,
    LangfuseTracer,
    setup_logging,
    TOKEN_COSTS,
)


class TestTokenUsage:
    """Tests for TokenUsage: token counting and cost calculation."""

    def test_total_tokens(self):
        """Total tokens = prompt + completion."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")
        assert usage.total_tokens == 150

    def test_total_tokens_zero(self):
        """Handle zero tokens."""
        usage = TokenUsage(prompt_tokens=0, completion_tokens=0, model="gpt-4o-mini", provider="openai")
        assert usage.total_tokens == 0

    def test_cost_ollama_free(self):
        """Ollama is free."""
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, model="llama2", provider="ollama")
        assert usage.cost() == 0.0

    def test_cost_openai_gpt4o_mini(self):
        """OpenAI gpt-4o-mini cost calculation."""
        # gpt-4o-mini: input=0.00015, output=0.0006
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")
        expected = (100 * 0.00015) + (50 * 0.0006)
        assert usage.cost() == pytest.approx(expected)

    def test_cost_openai_gpt4_turbo(self):
        """OpenAI gpt-4-turbo cost calculation."""
        # gpt-4-turbo: input=0.01, output=0.03
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4-turbo", provider="openai")
        expected = (100 * 0.01) + (50 * 0.03)
        assert usage.cost() == pytest.approx(expected)

    def test_cost_anthropic_opus(self):
        """Anthropic Claude Opus cost calculation."""
        # claude-opus-5-5: input=0.003, output=0.015
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            model="claude-opus-5-5",
            provider="anthropic"
        )
        expected = (100 * 0.003) + (50 * 0.015)
        assert usage.cost() == pytest.approx(expected)

    def test_cost_anthropic_sonnet(self):
        """Anthropic Claude Sonnet cost calculation."""
        # claude-sonnet-5-5: input=0.003, output=0.015
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            model="claude-sonnet-5-5",
            provider="anthropic"
        )
        expected = (100 * 0.003) + (50 * 0.015)
        assert usage.cost() == pytest.approx(expected)

    def test_cost_anthropic_haiku(self):
        """Anthropic Claude Haiku cost calculation."""
        # claude-haiku-4-5: input=0.00008, output=0.0004
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            model="claude-haiku-4-5",
            provider="anthropic"
        )
        expected = (100 * 0.00008) + (50 * 0.0004)
        assert usage.cost() == pytest.approx(expected)

    def test_cost_unknown_model_defaults_to_zero(self):
        """Unknown model defaults to zero cost."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            model="unknown-model",
            provider="openai"
        )
        assert usage.cost() == 0.0

    def test_cost_unknown_provider_defaults_to_zero(self):
        """Unknown provider defaults to zero cost."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            model="gpt-4o-mini",
            provider="unknown-provider"
        )
        assert usage.cost() == 0.0

    def test_provider_default_is_ollama(self):
        """Default provider is ollama (free)."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="llama2")
        assert usage.provider == "ollama"
        assert usage.cost() == 0.0


class TestAgentMetrics:
    """Tests for AgentMetrics: per-agent call tracking and aggregation."""

    def test_init(self):
        """Initialize metrics for an agent."""
        metrics = AgentMetrics(agent="Vigía")
        assert metrics.agent == "Vigía"
        assert metrics.calls == 0
        assert metrics.total_tokens == 0
        assert metrics.latency_ms == 0.0
        assert metrics.retries == 0
        assert metrics.failures == 0

    def test_add_call_single(self):
        """Record a single call."""
        metrics = AgentMetrics(agent="Vigía")
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        metrics.add_call(usage, latency_ms=150.5)

        assert metrics.calls == 1
        assert metrics.total_tokens == 150
        assert metrics.prompt_tokens == 100
        assert metrics.completion_tokens == 50
        assert metrics.latency_ms == 150.5
        assert len(metrics.call_details) == 1

    def test_add_call_multiple(self):
        """Record multiple calls."""
        metrics = AgentMetrics(agent="Vigía")
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=100, model="gpt-4o-mini", provider="openai")

        metrics.add_call(usage1, latency_ms=150.0)
        metrics.add_call(usage2, latency_ms=200.0)

        assert metrics.calls == 2
        assert metrics.total_tokens == 450
        assert metrics.prompt_tokens == 300
        assert metrics.completion_tokens == 150
        assert metrics.latency_ms == 350.0

    def test_average_latency_ms_single_call(self):
        """Average latency with one call."""
        metrics = AgentMetrics(agent="Vigía")
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        metrics.add_call(usage, latency_ms=150.0)

        assert metrics.average_latency_ms() == 150.0

    def test_average_latency_ms_multiple_calls(self):
        """Average latency with multiple calls."""
        metrics = AgentMetrics(agent="Vigía")
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        metrics.add_call(usage, latency_ms=100.0)
        metrics.add_call(usage, latency_ms=200.0)
        metrics.add_call(usage, latency_ms=300.0)

        assert metrics.average_latency_ms() == pytest.approx(200.0)

    def test_average_latency_ms_no_calls(self):
        """Average latency with no calls returns 0."""
        metrics = AgentMetrics(agent="Vigía")
        assert metrics.average_latency_ms() == 0.0

    def test_add_retry(self):
        """Record retry attempts."""
        metrics = AgentMetrics(agent="Vigía")

        metrics.add_retry()
        metrics.add_retry()

        assert metrics.retries == 2

    def test_add_failure(self):
        """Record failure attempts."""
        metrics = AgentMetrics(agent="Vigía")

        metrics.add_failure()
        metrics.add_failure()

        assert metrics.failures == 2

    def test_total_cost_single_call(self):
        """Total cost calculation for single call."""
        metrics = AgentMetrics(agent="Vigía")
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        metrics.add_call(usage, latency_ms=150.0)

        expected = usage.cost()
        assert metrics.total_cost() == pytest.approx(expected)

    def test_total_cost_multiple_calls(self):
        """Total cost calculation for multiple calls."""
        metrics = AgentMetrics(agent="Vigía")
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=100, model="gpt-4o-mini", provider="openai")

        metrics.add_call(usage1, latency_ms=150.0)
        metrics.add_call(usage2, latency_ms=200.0)

        expected = usage1.cost() + usage2.cost()
        assert metrics.total_cost() == pytest.approx(expected)

    def test_total_cost_zero(self):
        """Total cost with no calls."""
        metrics = AgentMetrics(agent="Vigía")
        assert metrics.total_cost() == 0.0


class TestAlertMetrics:
    """Tests for AlertMetrics: per-alert aggregations and serialization."""

    def test_init(self):
        """Initialize alert metrics."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )
        assert metrics.alert_id == "alert-123"
        assert metrics.metric == "cost_anomaly"
        assert metrics.entity == "customer-1"
        assert metrics.day == "2026-10-03"
        assert metrics.status == "processing"
        assert len(metrics.agent_metrics) == 0

    def test_get_agent_metrics_creates_on_first_access(self):
        """Get or create agent metrics."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        agent_metrics = metrics.get_agent_metrics("Vigía")

        assert agent_metrics.agent == "Vigía"
        assert "Vigía" in metrics.agent_metrics

    def test_get_agent_metrics_returns_same_instance(self):
        """Multiple accesses return same instance."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        agent_metrics_1 = metrics.get_agent_metrics("Vigía")
        agent_metrics_2 = metrics.get_agent_metrics("Vigía")

        assert agent_metrics_1 is agent_metrics_2

    def test_total_cost_no_agents(self):
        """Total cost with no agents."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )
        assert metrics.total_cost() == 0.0

    def test_total_cost_multiple_agents(self):
        """Total cost aggregated from multiple agents."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        vigia_metrics = metrics.get_agent_metrics("Vigía")
        analista_metrics = metrics.get_agent_metrics("Analista")

        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=100, model="gpt-4o-mini", provider="openai")

        vigia_metrics.add_call(usage1, latency_ms=150.0)
        analista_metrics.add_call(usage2, latency_ms=200.0)

        expected = usage1.cost() + usage2.cost()
        assert metrics.total_cost() == pytest.approx(expected)

    def test_total_tokens_no_agents(self):
        """Total tokens with no agents."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )
        assert metrics.total_tokens() == 0

    def test_total_tokens_multiple_agents(self):
        """Total tokens aggregated from multiple agents."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        vigia_metrics = metrics.get_agent_metrics("Vigía")
        analista_metrics = metrics.get_agent_metrics("Analista")

        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=100, model="gpt-4o-mini", provider="openai")

        vigia_metrics.add_call(usage1, latency_ms=150.0)
        analista_metrics.add_call(usage2, latency_ms=200.0)

        assert metrics.total_tokens() == 450

    def test_total_calls_no_agents(self):
        """Total calls with no agents."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )
        assert metrics.total_calls() == 0

    def test_total_calls_multiple_agents(self):
        """Total calls aggregated from multiple agents."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        vigia_metrics = metrics.get_agent_metrics("Vigía")
        analista_metrics = metrics.get_agent_metrics("Analista")

        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        vigia_metrics.add_call(usage, latency_ms=150.0)
        vigia_metrics.add_call(usage, latency_ms=160.0)
        analista_metrics.add_call(usage, latency_ms=200.0)

        assert metrics.total_calls() == 3

    def test_duration_ms_while_processing(self):
        """Duration while still processing."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        # Mock the start time
        past = datetime.utcnow() - timedelta(seconds=2)
        metrics.start_time = past

        duration_ms = metrics.duration_ms()

        # Should be approximately 2000ms, allowing for execution time
        assert duration_ms >= 1900  # At least 1.9 seconds

    def test_duration_ms_after_finish(self):
        """Duration after finishing."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        start = datetime.utcnow()
        metrics.start_time = start
        metrics.end_time = start + timedelta(seconds=2.5)

        duration_ms = metrics.duration_ms()

        assert duration_ms == pytest.approx(2500, abs=1)

    def test_to_dict_serialization(self):
        """Serialize alert metrics to dict."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        vigia_metrics = metrics.get_agent_metrics("Vigía")
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")
        vigia_metrics.add_call(usage, latency_ms=150.0)

        metrics.status = "completed"
        metrics.end_time = metrics.start_time + timedelta(seconds=1)

        result = metrics.to_dict()

        assert result["alert_id"] == "alert-123"
        assert result["metric"] == "cost_anomaly"
        assert result["entity"] == "customer-1"
        assert result["day"] == "2026-10-03"
        assert result["status"] == "completed"
        assert result["total_tokens"] == 150
        assert result["total_calls"] == 1
        assert "Vigía" in result["agents"]
        assert result["agents"]["Vigía"]["calls"] == 1

    def test_to_dict_structure(self):
        """to_dict returns correct structure."""
        metrics = AlertMetrics(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        result = metrics.to_dict()

        required_keys = {
            "alert_id", "metric", "entity", "day", "status",
            "duration_ms", "total_cost_usd", "total_tokens", "total_calls", "agents"
        }
        assert set(result.keys()) == required_keys


class TestMetricsCollector:
    """Tests for MetricsCollector: end-to-end metrics recording."""

    def test_init(self):
        """Initialize collector."""
        collector = MetricsCollector(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )
        assert collector.metrics.alert_id == "alert-123"
        assert collector.metrics.metric == "cost_anomaly"

    def test_record_agent_call(self, caplog):
        """Record an agent call."""
        collector = MetricsCollector(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        collector.record_agent_call("Vigía", usage, latency_ms=150.0)

        agent_metrics = collector.metrics.get_agent_metrics("Vigía")
        assert agent_metrics.calls == 1
        assert agent_metrics.total_tokens == 150

    def test_record_retry(self):
        """Record a retry."""
        collector = MetricsCollector(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        collector.record_retry("Vigía")
        collector.record_retry("Vigía")

        agent_metrics = collector.metrics.get_agent_metrics("Vigía")
        assert agent_metrics.retries == 2

    def test_record_failure(self):
        """Record a failure."""
        collector = MetricsCollector(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        collector.record_failure("Vigía")

        agent_metrics = collector.metrics.get_agent_metrics("Vigía")
        assert agent_metrics.failures == 1

    def test_finish_sets_status_and_end_time(self):
        """finish() sets status and end_time."""
        collector = MetricsCollector(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        collector.finish(status="completed")

        assert collector.metrics.status == "completed"
        assert collector.metrics.end_time is not None

    def test_finish_default_status(self):
        """finish() defaults to 'completed'."""
        collector = MetricsCollector(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )

        collector.finish()

        assert collector.metrics.status == "completed"

    def test_get_summary(self):
        """get_summary() returns metrics dict."""
        collector = MetricsCollector(
            alert_id="alert-123",
            metric="cost_anomaly",
            entity="customer-1",
            day="2026-10-03"
        )
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        collector.record_agent_call("Vigía", usage, latency_ms=150.0)
        collector.finish()

        summary = collector.get_summary()

        assert summary["alert_id"] == "alert-123"
        assert summary["status"] == "completed"
        assert summary["total_tokens"] == 150

    def test_end_to_end_workflow(self):
        """Complete workflow: record calls, retries, failures, finish."""
        collector = MetricsCollector(
            alert_id="alert-456",
            metric="spend_spike",
            entity="customer-2",
            day="2026-10-03"
        )

        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=100, model="gpt-4o-mini", provider="openai")

        # Vigía calls
        collector.record_agent_call("Vigía", usage1, latency_ms=150.0)
        collector.record_retry("Vigía")

        # Analista calls
        collector.record_agent_call("Analista", usage2, latency_ms=200.0)
        collector.record_failure("Analista")

        # Finish
        collector.finish("completed")

        summary = collector.get_summary()

        assert summary["total_calls"] == 2
        assert summary["total_tokens"] == 450
        assert summary["status"] == "completed"
        assert summary["agents"]["Vigía"]["retries"] == 1
        assert summary["agents"]["Analista"]["failures"] == 1


class TestLangfuseTracer:
    """Tests for LangfuseTracer: distributed tracing integration."""

    def test_init_disabled_by_default_without_api_key(self):
        """Tracer is disabled without API key."""
        tracer = LangfuseTracer(api_key=None)
        assert tracer.enabled is False

    def test_init_enabled_with_api_key(self):
        """Tracer is enabled with API key."""
        tracer = LangfuseTracer(api_key="test-api-key", enabled=True)
        assert tracer.enabled is True
        assert tracer.api_key == "test-api-key"

    def test_init_disabled_when_enabled_false(self):
        """Tracer can be explicitly disabled."""
        tracer = LangfuseTracer(api_key="test-api-key", enabled=False)
        assert tracer.enabled is False

    def test_trace_alert_disabled(self):
        """trace_alert does nothing when disabled."""
        tracer = LangfuseTracer(enabled=False)
        metrics = AlertMetrics("alert-123", "cost_anomaly", "customer-1", "2026-10-03")

        # Should not raise
        tracer.trace_alert("alert-123", metrics)

    def test_trace_alert_enabled(self, caplog):
        """trace_alert logs when enabled."""
        tracer = LangfuseTracer(api_key="test-api-key", enabled=True)
        metrics = AlertMetrics("alert-123", "cost_anomaly", "customer-1", "2026-10-03")

        with caplog.at_level(logging.INFO):
            tracer.trace_alert("alert-123", metrics)

        assert "Langfuse trace: alert-123" in caplog.text

    def test_trace_agent_call_disabled(self):
        """trace_agent_call does nothing when disabled."""
        tracer = LangfuseTracer(enabled=False)
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        # Should not raise
        tracer.trace_agent_call("alert-123", "Vigía", usage, 150.0)

    def test_trace_agent_call_enabled(self, caplog):
        """trace_agent_call logs when enabled."""
        tracer = LangfuseTracer(api_key="test-api-key", enabled=True)
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, model="gpt-4o-mini", provider="openai")

        with caplog.at_level(logging.INFO):
            tracer.trace_agent_call("alert-123", "Vigía", usage, 150.0)

        assert "Langfuse agent call: Vigía" in caplog.text


class TestSetupLogging:
    """Tests for setup_logging: logger configuration."""

    def test_setup_logging_creates_logger(self):
        """setup_logging creates a logger."""
        logger = setup_logging()
        assert logger is not None
        assert logger.name == "centinela"

    def test_setup_logging_sets_level(self):
        """setup_logging sets the logging level."""
        logger = setup_logging(level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_setup_logging_default_level(self):
        """setup_logging defaults to INFO."""
        logger = setup_logging()
        assert logger.level == logging.INFO

    def test_setup_logging_has_handlers(self):
        """setup_logging adds handlers."""
        logger = setup_logging()
        assert len(logger.handlers) > 0

    def test_setup_logging_returns_logger(self):
        """setup_logging returns configured logger."""
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)

    def test_setup_logging_multiple_calls(self):
        """Multiple calls to setup_logging work."""
        logger1 = setup_logging()
        logger2 = setup_logging()

        # Both should be the same logger
        assert logger1.name == logger2.name
