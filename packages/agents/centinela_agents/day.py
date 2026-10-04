import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalog import Catalog
from .metrics import Metrics
from .walk import Detection

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
