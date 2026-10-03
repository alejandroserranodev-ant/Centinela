from dataclasses import dataclass
from typing import Any, Mapping

from .catalog import Catalog, KpiReader, thresholds_named
from .metrics import Metrics
from .predicate import compare, is_kpi, kpi_column, threshold_value
from .schema import ROOT, Node, Predicate, Tree, index
from .state import approved_action, field_value


@dataclass(frozen=True)
class Context:
    nodes: Mapping[str, Node]
    metrics: Metrics
    catalog: Catalog
    reader: KpiReader

    @classmethod
    def of(cls, tree: Tree, metrics: Metrics, catalog: Catalog, reader: KpiReader) -> "Context":
        return cls(index(tree), metrics, catalog, reader)


@dataclass(frozen=True)
class Detection:
    metric: str
    entity: tuple[Any, ...]
    entry: str
    path: tuple[tuple[str, str], ...]
    row: Mapping[str, Any]


def kpi_holds(predicate: Predicate, row: Mapping[str, Any], ctx: Context) -> bool:
    _, column = kpi_column(predicate.lee)
    thresholds = thresholds_named(predicate.umbral, ctx.metrics, ctx.catalog) or {}
    return compare(predicate.op, row.get(column), threshold_value(thresholds.get(column), row))


def read(state: Mapping[str, Any], path: str, ctx: Context) -> Any:
    if path == "estado.detection.vigente":
        return still_breaks(state, ctx)
    if path == "estado.action.type":
        action = approved_action(state)
        return None if action is None else action.get("type")
    if path == "estado.same_cause_as.status":
        return (state.get("earlier_alerts") or {}).get(state.get("same_cause_as"))
    return field_value(state, path)


def state_holds(predicate: Predicate, state: Mapping[str, Any], ctx: Context) -> bool:
    if is_kpi(predicate.lee):
        raise ValueError(f"{predicate.lee} is a KPI, and an alert reads its measure through ejecutar.vigente")
    return compare(predicate.op, read(state, predicate.lee, ctx), predicate.valor)


def walk_from(start: str, state: Mapping[str, Any], row: Mapping[str, Any], ctx: Context) -> tuple[str, list[tuple[str, str]]]:
    current, path = start, []
    while current in ctx.nodes and ctx.nodes[current].hoja is None:
        node = ctx.nodes[current]
        predicate = node.predicado
        if is_kpi(predicate.lee):
            metric, _ = kpi_column(predicate.lee)
            if metric != state["candidato"]["metrica"]:
                raise ValueError(f"{node.id} reads {metric} on a row of {state['candidato']['metrica']}")
            passed = kpi_holds(predicate, row, ctx)
        else:
            passed = state_holds(predicate, state, ctx)
        branch = "si" if passed else "no"
        path.append((current, branch))
        current = node.si if passed else node.no
    return current, path


def detect(ctx: Context, day: str) -> list[Detection]:
    found: list[Detection] = []
    for metric, kpi in ctx.catalog.kpis.items():
        for row in ctx.reader(metric, day):
            candidate = {"candidato": {"metrica": metric, "descriptivo": kpi.descriptive}}
            target, path = walk_from(ROOT, candidate, row, ctx)
            if target in ctx.nodes:
                entity = tuple(row.get(column) for column in kpi.entity)
                found.append(Detection(metric, entity, target, tuple(path), dict(row)))
    return found


def still_breaks(state: Mapping[str, Any], ctx: Context) -> bool:
    detection = state["detection"]
    day = state["decision"]["simulated_day"]
    kpi = ctx.catalog.kpis[detection["metric"]]
    entity = list(detection["entity"])
    rows = [row for row in ctx.reader(detection["metric"], day) if [row.get(column) for column in kpi.entity] == entity]
    if len(rows) > 1:
        raise ValueError(f"{detection['metric']} returns {len(rows)} rows for {entity} on {day}, and its entity names one")
    passed = [
        ctx.nodes[node_id].predicado
        for node_id, branch in detection["path"]
        if branch == "si" and node_id in ctx.nodes and is_kpi(ctx.nodes[node_id].predicado.lee)
    ]
    if not rows or not passed:
        return False
    return all(kpi_holds(predicate, rows[0], ctx) for predicate in passed)
