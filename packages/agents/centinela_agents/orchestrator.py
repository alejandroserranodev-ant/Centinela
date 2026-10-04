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
from .catalog import KernelCall
from .evidence import Sources, call_from_reader
from .graph import Compiler, awaiting_decision, manual_owners, manual_review, resume, start_alert, thread
from .llm_provider import LLMProvider
from .metrics import Metrics
from .schema import Tree, index
from .skills import skill
from .tools import ToolRegistry
from .walk import Context, Detection

logger = logging.getLogger(__name__)


def rejection_target(provider: LLMProvider, state: Mapping[str, Any]) -> str:
    reason = (state.get("decision") or {}).get("reason") or ""
    return classify_rejection(provider, reason, state.get("cause") or {}, state.get("actions"))["destino"]


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
        kernel: KernelCall | None = None,
        reasoning_provider: LLMProvider | None = None,
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
            owners: Manual review owners by metric, read from acciones.md when absent
            kernel: the kernel's call; the leaves consult kpi_consultar through it
            reasoning_provider: the provider of Analista and Estratega, when it differs
        """
        self.provider = provider
        self.tools = tools
        self.tree = tree
        self.metrics = metrics

        owners = dict(owners) if owners is not None else manual_owners(skill("estratega", "acciones"))
        sources = Sources(kernel or call_from_reader(reader), catalog, metrics, index(tree))
        reasoning = reasoning_provider or provider

        self.leaves = {
            ("vigia", "titular"): lambda state: redact_title(provider, state, sources),
            ("analista", "explicar"): lambda state: explain_cause(reasoning, state, sources),
            ("estratega", "proponer"): lambda state: propose_actions(reasoning, state, state.get("cause"), sources),
            ("estratega", "revision_manual"): lambda state: {
                "actions": [manual_review(state["detection"]["metric"], owners)],
                "insufficient_cause": None,
            },
            ("ejecutor", "ejecutar"): lambda state: execute_action(
                provider, state.get("action"), state.get("decision"), tools
            ),
            ("ejecutor", "nota_manual"): lambda state: execute_action(
                provider, state.get("action"), state.get("decision"), tools
            ),
        }

        self.compiler = Compiler(
            leaves=self.leaves,
            metrics=metrics,
            catalog=catalog,
            reader=reader,
            classify=lambda state: rejection_target(provider, state),
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
