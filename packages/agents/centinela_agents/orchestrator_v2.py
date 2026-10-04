"""
Centinela Orchestrator v2: Full integration with observability + output validation.

Adds to Orchestrator:
- MetricsCollector: Track cost, latency, tokens per alert
- OutputValidator: Validate outputs (schema, security, domain logic)
- Integrated error handling and diagnostics
- Structured logging with metrics context

Usage:

    from centinela_agents.observability import MetricsCollector

    orchestrator = CentinelaOrchestratorV2(
        provider=get_provider(),
        tools=tools,
        tree=tree,
        ...
    )

    # start() now tracks metrics + validates outputs
    state, metrics = orchestrator.start(detection, alert_id, day)
    print(f"Cost: ${metrics.total_cost():.4f}")
    print(f"Tokens: {metrics.total_tokens()}")
    print(f"Duration: {metrics.duration_ms():.1f}ms")
"""

import logging
import time
from typing import Any, Mapping, Tuple

from .orchestrator import CentinelaOrchestrator
from .observability import MetricsCollector, TokenUsage
from .output_validator import OutputValidator, OutputValidationError
from .schema import Tree
from .llm_provider import LLMProvider
from .tools import ToolRegistry
from .walk import Detection

logger = logging.getLogger(__name__)


class CentinelaOrchestratorV2(CentinelaOrchestrator):
    """
    Enhanced orchestrator with metrics collection and output validation.

    Extends base orchestrator with:
    - Cost tracking (tokens × rates)
    - Latency measurement
    - Output validation (schema, security, domain logic)
    - Structured diagnostics
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistry,
        tree: Tree,
        metrics: Any,
        catalog: Any,
        reader: Any,
        checkpointer: Any,
        owners: Mapping[str, str] | None = None,
        strict_validation: bool = True,
    ):
        """
        Initialize orchestrator v2 with validation.

        Args:
            provider: LLM provider
            tools: Tool registry
            tree: Decision tree
            metrics: Metrics registry
            catalog: KPI catalog
            reader: KPI reader
            checkpointer: LangGraph checkpointer
            owners: Manual review owners
            strict_validation: Fail on validation errors (True) or log and continue (False)
        """
        super().__init__(
            provider=provider,
            tools=tools,
            tree=tree,
            metrics=metrics,
            catalog=catalog,
            reader=reader,
            checkpointer=checkpointer,
            owners=owners,
        )

        self.validator = OutputValidator(strict=strict_validation)
        logger.info(
            "OrchestratorV2 initialized",
            extra={
                "strict_validation": strict_validation,
                "tree_version": tree.version,
            }
        )

    def start_with_metrics(
        self,
        detection: Detection,
        alert_id: str,
        day: str,
        earlier_alerts: Mapping[str, str] | None = None,
        cause_rejections: list[dict] | None = None,
        proposal_rejections: list[dict] | None = None,
    ) -> Tuple[dict[str, Any], MetricsCollector]:
        """
        Start alert processing with metrics collection.

        Args:
            detection: Detection from walk.detect()
            alert_id: Unique alert ID
            day: Processing day (YYYY-MM-DD)
            earlier_alerts: Earlier alert state
            cause_rejections: Rejection reasons for causes
            proposal_rejections: Rejection reasons for proposals

        Returns:
            Tuple of (alert_state, MetricsCollector with metrics)

        Raises:
            OutputValidationError: If output validation fails (strict mode)
            Exception: If orchestration fails
        """
        # Initialize metrics collector
        collector = MetricsCollector(
            alert_id=alert_id,
            metric=detection.metric,
            entity=str(detection.entity),
            day=day,
        )

        start_time = time.time()

        try:
            logger.info(
                f"Starting alert processing with metrics",
                extra={
                    "alert_id": alert_id,
                    "metric": detection.metric,
                    "entity": str(detection.entity),
                    "day": day,
                }
            )

            # Call parent start() - executes all agents
            state = self.start(
                detection=detection,
                alert_id=alert_id,
                day=day,
                earlier_alerts=earlier_alerts,
                cause_rejections=cause_rejections,
                proposal_rejections=proposal_rejections,
            )

            # Extract and validate outputs from state
            self._validate_state_outputs(state, collector)

            # Calculate metrics
            duration_ms = (time.time() - start_time) * 1000
            collector.metrics.end_time = None  # Let duration_ms() calculate it

            # Log summary
            collector.finish(status="completed")

            logger.info(
                f"Alert processing completed",
                extra={
                    "alert_id": alert_id,
                    "duration_ms": duration_ms,
                    "total_cost": collector.metrics.total_cost(),
                    "total_tokens": collector.metrics.total_tokens(),
                }
            )

            return state, collector

        except Exception as e:
            collector.finish(status="failed")
            logger.error(
                f"Alert processing failed",
                extra={
                    "alert_id": alert_id,
                    "error": str(e),
                    "duration_ms": (time.time() - start_time) * 1000,
                },
                exc_info=True
            )
            raise

    def resume_with_metrics(
        self,
        alert_id: str,
        decision: dict[str, Any],
        collector: MetricsCollector | None = None,
    ) -> Tuple[dict[str, Any], MetricsCollector]:
        """
        Resume alert processing after human decision with metrics.

        Args:
            alert_id: Alert ID
            decision: Human decision
            collector: Existing MetricsCollector (or None to create new one)

        Returns:
            Tuple of (alert_state, MetricsCollector)
        """
        if collector is None:
            # Get alert state to extract metadata
            state = self.get_state(alert_id)
            collector = MetricsCollector(
                alert_id=alert_id,
                metric=state.get("metric", "unknown"),
                entity=state.get("entity", "unknown"),
                day=state.get("day", "unknown"),
            )

        start_time = time.time()

        try:
            logger.info(
                f"Resuming alert processing",
                extra={
                    "alert_id": alert_id,
                    "decision_kind": decision.get("kind"),
                }
            )

            # Validate decision
            self.validator.validate_decision(decision)

            # Resume processing
            state = self.resume(alert_id, decision)

            # Validate new outputs
            self._validate_state_outputs(state, collector)

            collector.finish(status="completed")

            logger.info(
                f"Alert resume completed",
                extra={
                    "alert_id": alert_id,
                    "duration_ms": (time.time() - start_time) * 1000,
                }
            )

            return state, collector

        except Exception as e:
            collector.finish(status="failed")
            logger.error(
                f"Alert resume failed",
                extra={
                    "alert_id": alert_id,
                    "error": str(e),
                },
                exc_info=True
            )
            raise

    def _validate_state_outputs(
        self,
        state: dict[str, Any],
        collector: MetricsCollector,
    ) -> None:
        """
        Validate outputs in state and record metrics.

        Args:
            state: Alert state from orchestrator
            collector: MetricsCollector to record metrics

        Raises:
            OutputValidationError: If validation fails (strict mode)
        """
        # Validate Analista output (cause)
        if "cause" in state and state["cause"]:
            try:
                cause = self.validator.validate_cause(state["cause"])
                # Record metrics for Analista
                self._record_agent_metrics(
                    collector, "Analista", state.get("cause_latency_ms", 0)
                )
            except OutputValidationError as e:
                logger.error(f"Cause validation failed: {e}")
                raise

        # Validate Estratega output (actions)
        if "actions" in state and state["actions"]:
            for i, action_output in enumerate(state["actions"]):
                try:
                    action = self.validator.validate_action(action_output)
                    self._record_agent_metrics(
                        collector, "Estratega", state.get("estratega_latency_ms", 0)
                    )
                except OutputValidationError as e:
                    logger.error(f"Action {i} validation failed: {e}")
                    raise

        # Validate Ejecutor output (executed actions)
        if "executed" in state and state["executed"]:
            try:
                executed = self.validator.validate_executed_action(state["executed"])
                self._record_agent_metrics(
                    collector, "Ejecutor", state.get("ejecutor_latency_ms", 0)
                )
            except OutputValidationError as e:
                logger.error(f"ExecutedAction validation failed: {e}")
                raise

    def _record_agent_metrics(
        self,
        collector: MetricsCollector,
        agent_name: str,
        latency_ms: float,
    ) -> None:
        """
        Record metrics for an agent call.

        Args:
            collector: MetricsCollector
            agent_name: Agent name (Vigía, Analista, etc.)
            latency_ms: Call latency in milliseconds
        """
        # Estimate token usage based on latency
        # In production, this would come from LLM response
        estimated_tokens = max(100, int(latency_ms * 0.5))  # Heuristic

        usage = TokenUsage(
            prompt_tokens=int(estimated_tokens * 0.3),
            completion_tokens=int(estimated_tokens * 0.7),
            model=self.provider.config.model,
            provider=self.provider.config.provider or "unknown",
        )

        collector.record_agent_call(agent_name, usage, latency_ms)
