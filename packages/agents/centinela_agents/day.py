import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Generator, Iterable, Mapping, Sequence

from .catalog import Catalog
from .metrics import Metrics
from .graph import STEP_LABELS, stream_alert, thread
from .walk import Context, Detection, detect

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class Earlier:
    alert_id: str
    metric: str
    entity: tuple[Any, ...] | None
    severity: str
    status: str
    brief: Mapping[str, Any] = field(default_factory=dict)


def entity_key(entity: Sequence[Any]) -> str:
    return json.dumps(list(entity), ensure_ascii=False, separators=(",", ":"), default=str)


def alert_id(metric: str, entity: Sequence[Any], day: str) -> str:
    key = json.dumps([metric, list(entity), day], ensure_ascii=False, separators=(",", ":"), default=str)
    return "alerta_" + hashlib.sha256(key.encode()).hexdigest()[:16]


def covered(detection: Detection, earlier: Sequence[Earlier]) -> bool:
    key = entity_key(detection.entity)
    ranks = [
        SEVERITY_RANK.get(alert.severity, len(SEVERITY_RANK))
        for alert in earlier
        if alert.metric == detection.metric and alert.entity is not None and entity_key(alert.entity) == key
    ]
    return bool(ranks) and SEVERITY_RANK[detection.severity] >= min(ranks)


def rank(detection: Detection, day: str) -> tuple:
    pesos = detection.pesos["value"] if detection.pesos else None
    return (pesos is None, -(pesos or 0), SEVERITY_RANK[detection.severity], alert_id(detection.metric, detection.entity, day))


def ordered(detections: Sequence[Detection], day: str, limit: int) -> list[Detection]:
    ranked = sorted(detections, key=lambda detection: rank(detection, day))
    largest: dict[str, Detection] = {}
    for detection in ranked:
        largest.setdefault(detection.metric, detection)
    first = sorted(largest.values(), key=lambda detection: rank(detection, day))
    rest = [detection for detection in ranked if all(detection is not chosen for chosen in first)]
    return [*first, *rest][:limit]


def entity_labels(metric: str, entity: Sequence[Any], metrics: Metrics, catalog: Catalog) -> list[str]:
    kpi = catalog.kpis.get(metric)
    return [
        f"{metrics.dimension_labels.get(column, column)} {value}"
        for column, value in zip(kpi.entity if kpi else (), entity)
        if value is not None and not DATE.match(str(value))
    ]


def labels(metric: str, entity: Sequence[Any], metrics: Metrics, catalog: Catalog) -> list[str]:
    head = [metrics.labels[metric]] if metric in metrics.labels else []
    return head + entity_labels(metric, entity, metrics, catalog)


logger = logging.getLogger(__name__)
MERGEABLE = "propuesta"


@dataclass(frozen=True)
class Step:
    alert_id: str | None
    agent: str
    node: str
    status: str
    description: str
    failed: bool
    metric: str
    entity: tuple[Any, ...]


@dataclass(frozen=True)
class AlertRun:
    alert_id: str
    detection: Detection
    state: Mapping[str, Any]
    absorbed: Mapping[str, Detection]


@dataclass(frozen=True)
class AlertFailed:
    alert_id: str
    detection: Detection
    reason: str


@dataclass(frozen=True)
class Verdict:
    recorded: bool
    refused_merge: str | None = None
    absorbed: tuple[str, ...] = ()


def step_of(written: Mapping[str, Any], detection: Detection) -> Step:
    return Step(written.get("alert_id"), written["agent"], written["node"], written["status"], written["description"], bool(written.get("failed")), detection.metric, tuple(detection.entity))


def detected_step(current: str, detection: Detection) -> Step:
    return Step(current, "vigia", "detectar", "done", STEP_LABELS[("vigia", "detectar")], False, detection.metric, tuple(detection.entity))


def brief_of_detection(detection: Detection, ctx: Context) -> dict[str, Any]:
    return {"metric": detection.metric, "entity": entity_labels(detection.metric, detection.entity, ctx.metrics, ctx.catalog), "cause": None}


def brief_of_state(detection: Detection, state: Mapping[str, Any], ctx: Context) -> dict[str, Any]:
    cause = state.get("cause") or {}
    return {**brief_of_detection(detection, ctx), "cause": cause.get("sentence") if cause.get("kind") == "identified" else None}


def run_day(graph, ctx: Context, day: str, *, earlier: Iterable[Earlier] = (), watched=None, limit: int = 3, cause_rejections=None, proposal_rejections=None, tracer=None) -> Generator[Step | AlertRun | AlertFailed, Verdict | None, None]:
    earlier = list(earlier)
    found = [detection for detection in detect(ctx, day) if (watched is None or detection.metric in watched) and not covered(detection, earlier)]
    queue = {alert_id(detection.metric, detection.entity, day): detection for detection in ordered(found, day, limit)}
    candidates = {alert.alert_id: dict(alert.brief) for alert in earlier if alert.status == MERGEABLE}
    while queue:
        current, detection = next(iter(queue.items()))
        del queue[current]
        verdict, excluded = None, set()
        yield detected_step(current, detection)
        while True:
            known = {**{other: MERGEABLE for other in candidates}, **{other: "nueva" for other in queue}}
            briefs = {**candidates, **{other: brief_of_detection(pending, ctx) for other, pending in queue.items()}}
            try:
                for written in stream_alert(
                    graph, detection, alert_id=current, day=day,
                    earlier_alerts={other: status for other, status in known.items() if other not in excluded},
                    alert_briefs=briefs,
                    cause_rejections=(cause_rejections or {}).get(detection.metric, ()),
                    proposal_rejections=(proposal_rejections or {}).get(detection.metric, ()),
                    tracer=tracer,
                ):
                    yield step_of(written, detection)
                state = graph.get_state(thread(current)).values
            except Exception as error:
                logger.error("The run of %s failed: %s", current, error, exc_info=error)
                yield AlertFailed(current, detection, str(error))
                break
            absorbed = {other: queue[other] for other in state.get("merged_alerts") or [] if other in queue}
            verdict = yield AlertRun(current, detection, state, absorbed)
            if not isinstance(verdict, Verdict):
                raise RuntimeError(f"the caller sent no verdict for {current}")
            if verdict.refused_merge is not None and verdict.refused_merge not in excluded:
                excluded.add(verdict.refused_merge)
                candidates.pop(verdict.refused_merge, None)
                continue
            break
        if verdict is None:
            continue
        for other in verdict.absorbed:
            queue.pop(other, None)
            candidates.pop(other, None)
        if verdict.recorded and state.get("status") == MERGEABLE:
            candidates[current] = brief_of_state(detection, state, ctx)
