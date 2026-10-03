"""
Observability: cost tracking, structured logging, Langfuse tracing.

Tracks:
- Tokens: prompt_tokens, completion_tokens per agent
- Model calls: count per agent per step
- Latency: time per agent, per alert
- Retries: attempt count on failures
- Cost: calculated from tokens (configurable rates)
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


# Token costs (USD) - configure per provider
TOKEN_COSTS = {
    "ollama": {"input": 0.0, "output": 0.0},  # Local, free
    "openai": {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    },
    "anthropic": {
        "claude-opus-5-5": {"input": 0.003, "output": 0.015},
        "claude-sonnet-5-5": {"input": 0.003, "output": 0.015},
        "claude-haiku-4-5": {"input": 0.00008, "output": 0.0004},
    },
}


@dataclass
class TokenUsage:
    """Token usage for a single LLM call."""
    prompt_tokens: int
    completion_tokens: int
    model: str
    provider: str = "ollama"

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def cost(self) -> float:
        """Calculate cost in USD."""
        if self.provider == "ollama":
            return 0.0

        provider_rates = TOKEN_COSTS.get(self.provider, {})
        if isinstance(provider_rates, dict) and "input" in provider_rates:
            rates = provider_rates
        else:
            rates = provider_rates.get(self.model, {})

        input_rate = rates.get("input", 0.0)
        output_rate = rates.get("output", 0.0)

        return (self.prompt_tokens * input_rate) + (self.completion_tokens * output_rate)


@dataclass
class AgentMetrics:
    """Metrics for one agent (Vigía, Analista, etc.)."""
    agent: str
    calls: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    retries: int = 0
    failures: int = 0
    call_details: list[TokenUsage] = field(default_factory=list)

    def total_cost(self) -> float:
        """Total cost in USD for this agent."""
        return sum(call.cost() for call in self.call_details)

    def add_call(self, usage: TokenUsage, latency_ms: float):
        """Record a successful call."""
        self.calls += 1
        self.prompt_tokens += usage.prompt_tokens
        self.completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.latency_ms += latency_ms
        self.call_details.append(usage)

    def add_retry(self):
        """Record a retry attempt."""
        self.retries += 1

    def add_failure(self):
        """Record a failed call."""
        self.failures += 1

    def average_latency_ms(self) -> float:
        """Average latency per call."""
        if self.calls == 0:
            return 0.0
        return self.latency_ms / self.calls


@dataclass
class AlertMetrics:
    """Metrics for a single alert processing."""
    alert_id: str
    metric: str
    entity: str
    day: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: str = "processing"  # processing, completed, failed

    agent_metrics: dict[str, AgentMetrics] = field(default_factory=dict)

    def get_agent_metrics(self, agent: str) -> AgentMetrics:
        """Get or create metrics for an agent."""
        if agent not in self.agent_metrics:
            self.agent_metrics[agent] = AgentMetrics(agent=agent)
        return self.agent_metrics[agent]

    def total_cost(self) -> float:
        """Total cost across all agents."""
        return sum(m.total_cost() for m in self.agent_metrics.values())

    def total_tokens(self) -> int:
        """Total tokens across all agents."""
        return sum(m.total_tokens for m in self.agent_metrics.values())

    def total_calls(self) -> int:
        """Total LLM calls across all agents."""
        return sum(m.calls for m in self.agent_metrics.values())

    def duration_ms(self) -> float:
        """Total processing time."""
        if self.end_time is None:
            return (datetime.utcnow() - self.start_time).total_seconds() * 1000
        return (self.end_time - self.start_time).total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "alert_id": self.alert_id,
            "metric": self.metric,
            "entity": self.entity,
            "day": self.day,
            "status": self.status,
            "duration_ms": self.duration_ms(),
            "total_cost_usd": self.total_cost(),
            "total_tokens": self.total_tokens(),
            "total_calls": self.total_calls(),
            "agents": {
                name: {
                    "calls": m.calls,
                    "tokens": m.total_tokens,
                    "latency_ms": m.average_latency_ms(),
                    "cost_usd": m.total_cost(),
                    "retries": m.retries,
                    "failures": m.failures,
                }
                for name, m in self.agent_metrics.items()
            },
        }


class MetricsCollector:
    """Collects metrics for alert processing."""

    def __init__(self, alert_id: str, metric: str, entity: str, day: str):
        """Initialize collector for an alert."""
        self.metrics = AlertMetrics(
            alert_id=alert_id,
            metric=metric,
            entity=entity,
            day=day,
        )

    def record_agent_call(
        self,
        agent: str,
        usage: TokenUsage,
        latency_ms: float,
    ):
        """Record a successful agent call."""
        agent_metrics = self.metrics.get_agent_metrics(agent)
        agent_metrics.add_call(usage, latency_ms)

        logger.info(
            f"Agent call: {agent}",
            extra={
                "alert_id": self.metrics.alert_id,
                "agent": agent,
                "tokens": usage.total_tokens,
                "latency_ms": latency_ms,
                "cost_usd": usage.cost(),
            }
        )

    def record_retry(self, agent: str):
        """Record a retry."""
        agent_metrics = self.metrics.get_agent_metrics(agent)
        agent_metrics.add_retry()

    def record_failure(self, agent: str):
        """Record a failure."""
        agent_metrics = self.metrics.get_agent_metrics(agent)
        agent_metrics.add_failure()

    def finish(self, status: str = "completed"):
        """Mark processing as finished."""
        self.metrics.end_time = datetime.utcnow()
        self.metrics.status = status

        logger.info(
            f"Alert processing finished",
            extra={
                "alert_id": self.metrics.alert_id,
                "status": status,
                "duration_ms": self.metrics.duration_ms(),
                "total_cost_usd": self.metrics.total_cost(),
                "total_tokens": self.metrics.total_tokens(),
                "total_calls": self.metrics.total_calls(),
            }
        )

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        return self.metrics.to_dict()


class LangfuseTracer:
    """Optional Langfuse integration for distributed tracing."""

    def __init__(self, api_key: str | None = None, enabled: bool = True):
        """
        Initialize Langfuse tracer.

        Args:
            api_key: Langfuse API key (from LANGFUSE_SECRET_KEY env var)
            enabled: Whether tracing is enabled
        """
        self.enabled = enabled and api_key is not None
        self.api_key = api_key

        if self.enabled:
            try:
                # Would import langfuse here
                logger.info("Langfuse tracing enabled")
            except ImportError:
                logger.warning("Langfuse not installed, tracing disabled")
                self.enabled = False

    def trace_alert(self, alert_id: str, metrics: AlertMetrics):
        """
        Send alert metrics to Langfuse.

        Args:
            alert_id: Alert ID
            metrics: AlertMetrics with all measurements
        """
        if not self.enabled:
            return

        # Would send to Langfuse here
        # For now, just log
        logger.info(
            f"Langfuse trace: {alert_id}",
            extra={
                "metrics": metrics.to_dict(),
            }
        )

    def trace_agent_call(
        self,
        alert_id: str,
        agent: str,
        usage: TokenUsage,
        latency_ms: float,
    ):
        """
        Send agent call to Langfuse.

        Args:
            alert_id: Alert ID
            agent: Agent name
            usage: TokenUsage
            latency_ms: Call latency
        """
        if not self.enabled:
            return

        logger.info(
            f"Langfuse agent call: {agent}",
            extra={
                "alert_id": alert_id,
                "agent": agent,
                "tokens": usage.total_tokens,
                "latency_ms": latency_ms,
            }
        )


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure structured logging for Centinela.

    Args:
        level: Logging level

    Returns:
        Root logger configured with JSON-structured format
    """
    # Basic configuration; in production, use Python-json-logger or similar
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "extra": "%(extra)s"}',
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    )
    handler.setFormatter(formatter)

    logger_obj = logging.getLogger("centinela")
    logger_obj.setLevel(level)
    logger_obj.addHandler(handler)

    return logger_obj
