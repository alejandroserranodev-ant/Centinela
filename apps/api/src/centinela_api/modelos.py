from typing import Annotated, Literal, Union
from enum import Enum

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
Agent = Literal["vigia", "analista", "estratega", "ejecutor"]
LogEventType = Literal["alert", "evidence", "proposal", "decision", "action", "result"]


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
    value: float
    unit: FigureUnit
    query_id: str


class Sentence(Esquema):
    text: str
    figures: list[Figure] = Field(default_factory=list)


class Confidence(Esquema):
    level: ConfidenceLevel
    assumptions: list[str] = Field(default_factory=list)


class SeriesPoint(Esquema):
    date: str
    value: float


class Evidence(Esquema):
    claim: Sentence
    query_id: str
    series: list[SeriesPoint] | None = None


class CauseIdentified(Esquema):
    kind: Literal["identified"] = "identified"
    sentence: Sentence
    evidence: list[Evidence]


class CauseNoEvidence(Esquema):
    kind: Literal["no_evidence"] = "no_evidence"
    reason: str
    queries_reviewed: list[str] = Field(default_factory=list)


Cause = Annotated[Union[CauseIdentified, CauseNoEvidence], Field(discriminator="kind")]


class Impact(Esquema):
    figure: Figure
    period: Literal["month", "once"]


class Action(Esquema):
    id: str
    title: str
    description: Sentence
    type: ActionType
    impact: Impact | None
    confidence: Confidence
    parameters: dict[str, str | float] = Field(default_factory=dict)


class ExecutedAction(Esquema):
    action_id: str
    result: str


class Alert(Esquema):
    id: str
    status: AlertStatus
    severity: Severity
    metric: Metric
    title: Sentence
    pesos_at_risk: Figure
    recoverable_per_month: Figure | None
    confidence: Confidence
    simulated_date: str
    cause: Cause
    actions: list[Action] = Field(default_factory=list, min_length=0, max_length=3)
    executed_action: ExecutedAction | None = None


class AgentStep(Esquema):
    alert_id: str | None
    agent: Agent
    status: Literal["running", "done"]
    description: str
    start: str
    end: str | None = None


class ActorAgent(Esquema):
    kind: Literal["agent"] = "agent"
    agent: Agent


class ActorPerson(Esquema):
    kind: Literal["person"] = "person"
    name: str
    role: str


Actor = Annotated[Union[ActorAgent, ActorPerson], Field(discriminator="kind")]


class LogEvent(Esquema):
    id: str
    date: str
    simulated_day: str
    alert_id: str
    type: LogEventType
    actor: Actor
    detail: str
    query_id: str | None = None


class ChatMessage(Esquema):
    id: str
    role: Literal["user", "centinela"]
    text: str
    figures: list[Figure] = Field(default_factory=list)
    alert_id: str | None = None
    series: list[SeriesPoint] | None = None
    enough_evidence: bool
    date: str


class ChatQuestion(Esquema):
    question: str


class SimulatedDay(Esquema):
    """Current simulated day in ISO 8601 format."""
    dia: str = Field(..., description="Current simulated day (YYYY-MM-DD)", example="2026-10-03")


class DecisionApprove(Esquema):
    kind: Literal["approve"] = "approve"
    action_id: str


class DecisionEdit(Esquema):
    kind: Literal["edit"] = "edit"
    action_id: str
    parameters: dict[str, str | float]


class DecisionReject(Esquema):
    kind: Literal["reject"] = "reject"
    reason: str


Decision = Annotated[
    Union[DecisionApprove, DecisionEdit, DecisionReject], Field(discriminator="kind")
]


class AgentAlertInput(Esquema):
    """Entrada de Vigía: una nueva alerta detectada."""

    severity: Severity
    metric: Metric
    title: Sentence
    pesos_at_risk: Figure
    recoverable_per_month: Figure | None = None
    confidence: Confidence
    simulated_date: str


class AgentCauseInput(Esquema):
    """Entrada de Analista: causa e evidencia de una alerta."""

    cause: Cause
    evidence: list[Evidence] = Field(default_factory=list)


class AgentProposalInput(Esquema):
    """Entrada de Estratega: acciones propuestas para una alerta."""

    actions: list[Action] = Field(min_length=1, max_length=3)


class AgentExecutionInput(Esquema):
    """Entrada de Ejecutor: resultado de ejecutar una acción."""

    action_id: str
    status: Literal["success", "failed", "partial"]
    result: str
    error: str | None = None


class CostoAgente(Esquema):
    """Registro de costo: tokens, modelo, latencia por paso."""

    agent: Agent
    step: str
    modelo: str
    tokens_entrada: int
    tokens_salida: int
    latencia_ms: int
