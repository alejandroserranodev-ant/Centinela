from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .metrics import Metrics

KpiReader = Callable[[str, str], list[Mapping[str, Any]]]


@dataclass(frozen=True)
class Kpi:
    entity: tuple[str, ...]
    columns: frozenset[str]
    descriptive: bool = False
    thresholds: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Catalog:
    kpis: Mapping[str, Kpi]


def thresholds_named(name: str, metrics: Metrics, catalog: Catalog) -> Mapping[str, Any] | None:
    if name in metrics.thresholds:
        return metrics.thresholds[name]
    kpi = catalog.kpis.get(name)
    return kpi.thresholds if kpi is not None and kpi.thresholds else None
