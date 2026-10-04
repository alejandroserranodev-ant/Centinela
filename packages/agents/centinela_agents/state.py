import operator
from typing import Annotated, Any, Mapping, TypedDict

from .metered import add_costs

DERIVED_FIELDS = frozenset({"estado.detection.vigente", "estado.action.type", "estado.same_cause_as.status"})
STATE_FIELDS = DERIVED_FIELDS | frozenset(
    {
        "estado.candidato.metrica",
        "estado.candidato.descriptivo",
        "estado.cause.kind",
        "estado.same_cause_as",
        "estado.insufficient_cause",
        "estado.analyst_returns",
        "estado.proposal_returns",
        "estado.actions",
        "estado.decision.kind",
        "estado.executed_action",
        "estado.chat.sospechosa",
        "estado.chat.intent",
        "estado.chat.alert_id",
        "estado.chat.kpi",
        "estado.chat.figuras",
    }
)


class AlertState(TypedDict, total=False):
    alert_id: str
    simulated_day: str
    entry: str
    earlier_alerts: dict[str, str]
    alert_briefs: dict[str, dict[str, Any]]
    detection: dict[str, Any]
    title: dict[str, Any]
    cause: dict[str, Any] | None
    cause_rejections: list[Any]
    proposal_rejections: list[Any]
    same_cause_as: str | None
    analyst_returns: int
    proposal_returns: int
    insufficient_cause: Any
    actions: list[dict[str, Any]] | None
    decision: dict[str, Any] | None
    rejection_target: str | None
    executed_action: dict[str, Any] | None
    merged_into: str | None
    merged_alerts: list[str]
    queries: list[Any]
    status: str
    next_node: str
    fin: str
    camino: Annotated[list, operator.add]
    transitions: Annotated[list, operator.add]
    failures: Annotated[list, operator.add]
    events: Annotated[list, operator.add]
    cost: Annotated[dict, add_costs]


class ChatState(TypedDict, total=False):
    question: str
    day: str
    alert: dict[str, Any] | None
    cause: dict[str, Any] | None
    actions: list[dict[str, Any]] | None
    chat: dict[str, Any]
    answer: dict[str, Any] | None
    queries: list[Any]
    next_node: str
    fin: str
    camino: Annotated[list, operator.add]
    failures: Annotated[list, operator.add]
    costs: Annotated[list, operator.add]
    cost: Annotated[dict, add_costs]


def subject(state: Mapping[str, Any]) -> tuple[str, str, str]:
    detection = state.get("detection") or {}
    entity = ", ".join(str(value) for value in detection.get("entity") or [])
    return detection.get("metric") or "", entity, state.get("simulated_day") or ""


def field_value(state: Mapping[str, Any], path: str) -> Any:
    value: Any = state
    for key in path.split(".")[1:]:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value


def approved_action(state: Mapping[str, Any]) -> dict[str, Any] | None:
    decision = state.get("decision") or {}
    if decision.get("kind") not in ("approve", "edit"):
        return None
    for action in state.get("actions") or []:
        if action["id"] == decision.get("actionId"):
            if decision["kind"] == "edit":
                return {**action, "parameters": dict(decision["parameters"])}
            return dict(action)
    return None
