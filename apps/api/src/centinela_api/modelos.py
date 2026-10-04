from typing import Annotated, Literal, Union
from enum import Enum

from centinela_agents.agents.chat import MAX_QUESTION
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

AlertStatus = Literal["new", "analyzing", "proposed", "approved", "rejected", "executed"]
Severity = Literal["critical", "high", "medium", "low"]
ConfidenceLevel = Literal["high", "medium", "low"]
Metric = Literal[
    "margen_pct",
    "saldo_vencido",
    "dias_pago_prom",
    "cobertura_dias",
    "descuento_en_exceso",
    "veces_intervalo_habitual",
]
FigureUnit = Literal["COP", "points", "percent", "days", "units"]
ActionType = Literal["email_draft", "task", "purchase_order_draft", "price_change_draft"]
Agent = Literal["vigia", "analista", "estratega", "ejecutor", "chat"]
LogEventType = Literal["alert", "evidence", "proposal", "decision", "action", "result", "question", "answer", "refusal"]
ChatOutcome = Literal["answered", "no_evidence", "out_of_scope", "refused"]


class AlertEstadoEnum(str, Enum):
    """Valid alert estado values (Spanish names for API contract)."""
    NUEVA = "nueva"
    EN_ANALISIS = "en_analisis"
    PROPUESTA = "propuesta"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    EJECUTADA = "ejecutada"


class Esquema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Figure(Esquema):
    """Quantitative measurement with unit and traceability."""
    value: float = Field(..., description="Numeric value", example=42000000)
    unit: FigureUnit = Field(..., description="Unit of measurement (COP, percent, days, etc.)")
    query_id: str = Field(..., description="Reference to SQL query that produced this figure")


class Sentence(Esquema):
    """Natural language statement with optional supporting figures."""
    text: str = Field(..., description="Human-readable statement")
    figures: list[Figure] = Field(default_factory=list, description="Numeric evidence supporting the statement")


class Confidence(Esquema):
    """Confidence assessment with assumptions."""
    level: ConfidenceLevel = Field(..., description="Confidence level: high, medium, or low")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions underlying the confidence assessment")


class SeriesPoint(Esquema):
    """Single data point in a time series."""
    date: str = Field(..., description="ISO 8601 date", example="2026-10-01")
    value: float = Field(..., description="Value at this date")


class Evidence(Esquema):
    """Supporting data for a claim: statement + historical series."""
    claim: Sentence = Field(..., description="Statement with figures")
    query_id: str = Field(..., description="SQL query ID that retrieved this evidence")
    series: list[SeriesPoint] | None = Field(None, description="Historical series supporting the claim")


class CauseIdentified(Esquema):
    """Root cause found with evidence."""
    kind: Literal["identified"] = Field("identified", description="Discriminator: cause was identified")
    sentence: Sentence = Field(..., description="Root cause statement with figures")
    evidence: list[Evidence] = Field(..., description="Supporting evidence", min_length=1)


class CauseNoEvidence(Esquema):
    """Root cause could not be identified with available data."""
    kind: Literal["no_evidence"] = Field("no_evidence", description="Discriminator: cause could not be identified")
    reason: str = Field(..., description="Explanation why cause could not be determined")
    queries_reviewed: list[str] = Field(default_factory=list, description="Query IDs that were searched")


Cause = Annotated[Union[CauseIdentified, CauseNoEvidence], Field(discriminator="kind")]


class Impact(Esquema):
    """Expected business impact of an action."""
    figure: Figure = Field(..., description="Impact magnitude (pesos, percent, etc.)")
    period: Literal["month", "once"] = Field(..., description="Recurrence: monthly or one-time")


class Action(Esquema):
    """Proposed mitigation action with impact and parameters."""
    id: str = Field(..., description="Unique action ID", example="action_raise_price_3pct")
    title: str = Field(..., description="Short action title")
    description: Sentence = Field(..., description="Detailed action description with impact figures")
    type: ActionType = Field(..., description="Type: email_draft, task, purchase_order_draft, or price_change_draft")
    impact: Impact | None = Field(None, description="Expected business impact if executed")
    confidence: Confidence = Field(..., description="Confidence in the action's effectiveness")
    parameters: dict[str, str | float] = Field(default_factory=dict, description="Editable parameters (price, qty, etc.)")


class ExecutedAction(Esquema):
    """Result of executing an approved action."""
    action_id: str = Field(..., description="ID of the executed action")
    result: str = Field(..., description="Execution outcome: success, failed, or partial")


class Alert(Esquema):
    """Complete alert lifecycle state."""
    id: str = Field(..., description="Unique alert ID", example="alerta_abc123def456")
    status: AlertStatus = Field(..., description="Current status in lifecycle: new → analyzing → proposed → approved/rejected → executed")
    severity: Severity = Field(..., description="Alert severity: critical, high, medium, or low")
    metric: Metric = Field(..., description="Metric that triggered this alert")
    title: Sentence = Field(..., description="Alert title with initial impact figures")
    pesos_at_risk: Figure = Field(..., description="Pesos at risk (COP)")
    recoverable_per_month: Figure | None = Field(None, description="Potential monthly recovery if action taken")
    confidence: Confidence = Field(..., description="Confidence in the alert detection")
    simulated_date: str = Field(..., description="Simulated date when alert was created (ISO 8601)")
    cause: Cause = Field(..., description="Root cause (identified with evidence or no_evidence)")
    actions: list[Action] = Field(default_factory=list, min_length=0, max_length=3, description="Proposed mitigation actions")
    executed_action: ExecutedAction | None = Field(None, description="Action executed (only when status=executed)")


class AgentStep(Esquema):
    """Progress event during agent processing (for SSE streams)."""
    alert_id: str | None = Field(None, description="Alert ID being processed")
    agent: Agent = Field(..., description="Agent name")
    node: str | None = Field(None, description="Node of the decision tree the step walked, if any")
    status: Literal["running", "done"] = Field(..., description="Step status")
    description: str = Field(..., description="Human-readable step description")
    start: str = Field(..., description="UTC start time (ISO 8601)")
    end: str | None = Field(None, description="UTC end time (ISO 8601), null if running")


class ActorAgent(Esquema):
    """Alert action performed by an agent."""
    kind: Literal["agent"] = Field("agent", description="Discriminator: action by agent")
    agent: Agent = Field(..., description="Agent name (vigia, analista, estratega, ejecutor, chat)")


class ActorPerson(Esquema):
    """Alert decision made by a human."""
    kind: Literal["person"] = Field("person", description="Discriminator: action by person")
    name: str = Field(..., description="Person name (percent-encoded)")
    role: str = Field(..., description="Person role (gerente, lider_proceso)")


Actor = Annotated[Union[ActorAgent, ActorPerson], Field(discriminator="kind")]


class LogEvent(Esquema):
    """Audit log entry for alert lifecycle event."""
    id: str = Field(..., description="Log entry ID")
    date: str = Field(..., description="UTC timestamp of event (ISO 8601)")
    simulated_day: str = Field(..., description="Simulated date when event occurred")
    alert_id: str | None = Field(None, description="Alert ID, null for a chat question asked from no alert")
    type: LogEventType = Field(..., description="Event type: alert, evidence, proposal, decision, action, result, question, answer, refusal")
    actor: Actor = Field(..., description="Who/what performed the action (agent or person)")
    detail: str = Field(..., description="Human-readable description or JSON cost data")
    query_id: str | None = Field(None, description="SQL query ID if relevant to this event")


class ChatMessage(Esquema):
    """Chat response from Centinela (the agent chat)."""
    id: str = Field(..., description="Message ID")
    role: Literal["user", "centinela"] = Field(..., description="Message source: user question or centinela answer")
    text: str = Field(..., description="Message text")
    figures: list[Figure] = Field(default_factory=list, description="Numeric evidence in the message")
    alert_id: str | None = Field(None, description="Related alert ID if any")
    series: list[SeriesPoint] | None = Field(None, description="Historical series if relevant")
    enough_evidence: bool = Field(..., description="Whether answer is based on sufficient evidence")
    outcome: ChatOutcome = Field("answered", description="How the walk of conversar ended: answered, no_evidence, out_of_scope or refused")
    date: str = Field(..., description="Message timestamp (ISO 8601)")


class ChatQuestion(Esquema):
    """User question for Centinela (the agent chat)."""
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION, description="Natural language question about alert or metric")
    alert_id: str | None = Field(None, description="Alert the question is asked from, if any")


class Query(Esquema):
    """A query of the kernel that produced a figure, recorded when an agent ran it."""
    id: str = Field(..., description="The figure's queryId")
    source: Literal["kernel"] = Field("kernel", description="Where the query runs: the KPI kernel of packages/tools")
    sql: str = Field(..., description="The call the kernel ran")
    description: str = Field(..., description="The KPI and the simulated day it was read on")


class SimulatedDay(Esquema):
    """Current simulated day in ISO 8601 format."""
    dia: str = Field(..., description="Current simulated day (YYYY-MM-DD)", example="2026-10-03")


class DecisionApprove(Esquema):
    """Human decision: approve and execute action."""
    kind: Literal["approve"] = Field("approve", description="Discriminator: approve decision")
    action_id: str = Field(..., description="ID of action to approve")


class DecisionEdit(Esquema):
    """Human decision: approve with modified parameters."""
    kind: Literal["edit"] = Field("edit", description="Discriminator: edit and approve decision")
    action_id: str = Field(..., description="ID of action to modify and approve")
    parameters: dict[str, str | float] = Field(..., description="Modified parameters (price, qty, etc.)")


class DecisionReject(Esquema):
    """Human decision: reject alert."""
    kind: Literal["reject"] = Field("reject", description="Discriminator: reject decision")
    reason: str = Field(..., description="Reason for rejection")


Decision = Annotated[
    Union[DecisionApprove, DecisionEdit, DecisionReject], Field(discriminator="kind")
]


class AgentAlertInput(Esquema):
    """Vigía input: new alert detected from metric anomaly."""
    severity: Severity = Field(..., description="Alert severity (critical, high, medium, low)")
    metric: Metric = Field(..., description="Metric that triggered alert")
    title: Sentence = Field(..., description="Alert title with figures")
    pesos_at_risk: Figure = Field(..., description="Pesos at risk (COP)")
    recoverable_per_month: Figure | None = Field(None, description="Monthly recovery potential")
    confidence: Confidence = Field(..., description="Confidence in the alert detection")
    simulated_date: str = Field(..., description="Simulated date of detection (ISO 8601)")


class AgentCauseInput(Esquema):
    """Analista input: root cause explanation with evidence."""
    cause: Cause = Field(..., description="Root cause (identified or no_evidence)")
    evidence: list[Evidence] = Field(default_factory=list, description="Additional evidence queries run by Analista")


class AgentProposalInput(Esquema):
    """Estratega input: proposed mitigation actions."""
    actions: list[Action] = Field(..., min_length=1, max_length=3, description="1-3 proposed actions with impact and parameters")


class AgentExecutionInput(Esquema):
    """Ejecutor input: result of executing an approved action."""
    action_id: str = Field(..., description="ID of the action executed")
    status: Literal["success", "failed", "partial"] = Field(..., description="Execution result")
    result: str = Field(..., description="Human-readable result or error message")
    error: str | None = Field(None, description="Detailed error if status != success")


class CostoAgente(Esquema):
    """Agent cost tracking: tokens, model, and latency."""
    agent: Agent = Field(..., description="Agent that ran (vigia, analista, estratega, ejecutor)")
    step: str = Field(..., description="Step name (e.g., search_policies, generate_actions)")
    modelo: str = Field(..., description="Model used (e.g., claude-opus-5)")
    tokens_entrada: int = Field(..., description="Input tokens consumed")
    tokens_salida: int = Field(..., description="Output tokens generated")
    latencia_ms: int = Field(..., description="Total latency in milliseconds")
