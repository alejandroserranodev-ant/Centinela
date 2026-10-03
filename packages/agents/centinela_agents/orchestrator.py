"""
Centinela Orchestrator: Complete integration of agents, tools, and LangGraph.

Orchestrates alert processing from detection through execution:
1. Detect (Vigía) → 2. Explain (Analista) → 3. Propose (Estratega)
→ 4. Approve (Human) → 5. Execute (Ejecutor) → 6. Close

Usage:

    orchestrator = CentinelaOrchestrator(
        provider=get_provider(),
        tools=ToolRegistry(...),
        tree=load_tree(),
        checkpointer=PostgresCheckpointer()
    )

    # Start an alert
    state = orchestrator.start(
        detection=Detection(...),
        alert_id="alert_001",
        day="2026-10-03"
    )

    # Resume after human decision
    state = orchestrator.resume(
        alert_id="alert_001",
        decision=Decision(kind="approve", actionId="a1")
    )
"""

import logging
from typing import Any, Mapping

from langgraph.types import Command

from .agents.analista import explain_cause
from .agents.ejecutor import execute_action
from .agents.estratega import propose_actions
from .agents.orquestador import classify_rejection
from .agents.vigia import redact_title
from .graph import Compiler, awaiting_decision, resume, start_alert, thread
from .llm_provider import LLMProvider
from .metrics import Metrics
from .schema import Tree
from .tools import ToolRegistry
from .walk import Context, Detection

logger = logging.getLogger(__name__)


class CentinelaOrchestrator:
    """
    Complete orchestrator for Centinela alert processing.

    Integrates:
    - LLM provider (Ollama, OpenAI, or Anthropic)
    - Tool registry (SQL, policy, impact, actions)
    - Alert state machine (LangGraph)
    - 5 agents (Vigía, Analista, Estratega, Ejecutor, Orquestador)
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistry,
        tree: Tree,
        metrics: Metrics,
        catalog: Any,
        reader: Any,
        checkpointer: Any,
        owners: Mapping[str, str] | None = None,
    ):
        """
        Initialize orchestrator.

        Args:
            provider: LLM provider (Ollama, OpenAI, Anthropic)
            tools: ToolRegistry with sql_vistas, policy, impact, action tools
            tree: Decision tree from base.yaml
            metrics: Metrics from data/metricas.yaml
            catalog: KPI catalog
            reader: KPI reader
            checkpointer: LangGraph checkpointer (for state persistence)
            owners: Manual review owners by metric
        """
        self.provider = provider
        self.tools = tools
        self.tree = tree
        self.metrics = metrics

        # Build leaf functions (agents)
        self.leaves = {
            ("vigia", "titular"): lambda state: redact_title(provider, state),
            ("analista", "explicar"): lambda state: explain_cause(provider, state, tools),
            ("estratega", "proponer"): lambda state: propose_actions(
                provider, state, state.get("cause"), tools
            ),
            ("estratega", "revision_manual"): lambda state: propose_actions(
                provider, state, state.get("cause"), tools
            ),
            ("ejecutor", "ejecutar"): lambda state: execute_action(
                provider, state.get("action"), state.get("decision"), tools
            ),
            ("ejecutor", "nota_manual"): lambda state: execute_action(
                provider, state.get("action"), state.get("decision"), tools
            ),
        }

        # Compile tree to LangGraph
        self.compiler = Compiler(
            leaves=self.leaves,
            metrics=metrics,
            catalog=catalog,
            reader=reader,
            classify=lambda state: classify_rejection(provider, state),
            checkpointer=checkpointer,
            owners=owners,
        )

        self.graph = self.compiler.graph(tree)
        logger.info(f"Orchestrator initialized with tree v{tree.version}")

    def start(
        self,
        detection: Detection,
        alert_id: str,
        day: str,
        earlier_alerts: Mapping[str, str] | None = None,
        cause_rejections: list[dict] | None = None,
        proposal_rejections: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Start processing an alert.

        Args:
            detection: Detection from walk.detect()
            alert_id: Unique alert ID
            day: Simulated day (YYYY-MM-DD)
            earlier_alerts: State of earlier alerts (for merge detection)
            cause_rejections: Rejection reasons about causes (from API)
            proposal_rejections: Rejection reasons about proposals (from API)

        Returns:
            Alert state after reaching first human decision point (or end)

        Raises:
            Exception: If tree compilation or graph execution fails
        """
        logger.info(
            f"Orchestrator.start: {detection.metric}:{detection.entity[0]} on {day}",
            extra={"alert_id": alert_id, "metric": detection.metric}
        )

        try:
            state = start_alert(
                self.graph,
                detection,
                alert_id=alert_id,
                day=day,
                earlier_alerts=earlier_alerts or {},
                cause_rejections=cause_rejections or [],
                proposal_rejections=proposal_rejections or [],
            )

            if awaiting_decision(self.graph, alert_id):
                logger.info(f"Alert {alert_id} awaits decision at {self.tree.nodos[0].id}")
            else:
                logger.info(f"Alert {alert_id} processing complete")

            return state

        except Exception as e:
            logger.error(f"Orchestrator.start failed: {e}", exc_info=True)
            raise

    def is_awaiting_decision(self, alert_id: str) -> bool:
        """
        Check if an alert is waiting for human decision.

        Args:
            alert_id: Alert ID

        Returns:
            True if alert is at approval gate (aprobar.decision)
        """
        return awaiting_decision(self.graph, alert_id)

    def resume(
        self,
        alert_id: str,
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resume alert processing with human decision.

        Args:
            alert_id: Alert ID
            decision: {
                kind: "approve" | "edit" | "reject" | "request_changes",
                actionId: str (if approve/edit),
                parameters: dict (if edit),
                reason: str (if reject/request_changes),
            }

        Returns:
            Alert state after resuming

        Raises:
            Exception: If decision is invalid or graph execution fails
        """
        logger.info(
            f"Orchestrator.resume: {alert_id} with decision kind={decision.get('kind')}",
            extra={"alert_id": alert_id}
        )

        try:
            state = resume(self.graph, alert_id, decision)

            if awaiting_decision(self.graph, alert_id):
                logger.info(f"Alert {alert_id} awaits next decision")
            else:
                logger.info(f"Alert {alert_id} processing complete")

            return state

        except Exception as e:
            logger.error(f"Orchestrator.resume failed: {e}", exc_info=True)
            raise

    def get_state(self, alert_id: str) -> dict[str, Any]:
        """
        Get current state of an alert.

        Args:
            alert_id: Alert ID

        Returns:
            Complete alert state
        """
        return self.graph.get_state(thread(alert_id)).values
