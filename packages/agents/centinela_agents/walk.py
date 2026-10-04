from dataclasses import dataclass, field
from typing import Any, Mapping

from .catalog import Catalog, KernelCall, KpiReader, thresholds_named
from .evidence import Ledger, call_from_reader, unit_of
from .metrics import Metrics, is_number
from .predicate import compare, is_kpi, kpi_column, threshold_value
from .schema import ROOT, Node, Predicate, Tree, index
from .severity import severity_of, tranche_of
from .state import approved_action, field_value


@dataclass(frozen=True)
class Context:
    nodes: Mapping[str, Node]
    metrics: Metrics
    catalog: Catalog
    reader: KpiReader
    owners: Mapping[str, str] = field(default_factory=dict)
    call: KernelCall | None = None
    version: int = 0

    @classmethod
    def of(cls, tree: Tree, metrics: Metrics, catalog: Catalog, reader: KpiReader, owners: Mapping[str, str] | None = None, call: KernelCall | None = None) -> "Context":
        return cls(index(tree), metrics, catalog, reader, dict(owners or {}), call, tree.version)


@dataclass(frozen=True)
class Detection:
    metric: str
    entity: tuple[Any, ...]
    entry: str
    path: tuple[tuple[str, str], ...]
    row: Mapping[str, Any]
    severity: str = "high"
    tranche: str | None = None
    figure: Mapping[str, Any] | None = None
    pesos: Mapping[str, Any] | None = None
    rule: str = ""
    threshold_source: str = ""
    query: Mapping[str, Any] | None = None


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
        if node.retirado is not None:
            passed = False
        elif is_kpi(predicate.lee):
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
    ledger = Ledger(ctx.call or call_from_reader(ctx.reader), ctx.catalog)
    found: list[Detection] = []
    for metric, kpi in ctx.catalog.kpis.items():
        qid, rows = ledger.consult(metric, day)
        for row in rows:
            candidate = {"candidato": {"metrica": metric, "descriptivo": kpi.descriptive}}
            target, path = walk_from(ROOT, candidate, row, ctx)
            if target in ctx.nodes:
                found.append(detection_of(metric, target, path, row, ledger.queries[qid], ctx))
    return found


def compared_column(path: list[tuple[str, str]], ctx: Context) -> str | None:
    columns = [kpi_column(ctx.nodes[node_id].predicado.lee)[1] for node_id, branch in path if branch == "si" and is_kpi(ctx.nodes[node_id].predicado.lee)]
    return columns[-1] if columns else None


def detection_of(metric: str, target: str, path: list[tuple[str, str]], row: Mapping[str, Any], query: Mapping[str, Any], ctx: Context) -> Detection:
    qid = query["queryId"]
    column = compared_column(path, ctx)
    value, pesos = row.get(column) if column else None, row.get("pesos_en_riesgo")
    return Detection(
        metric,
        tuple(row.get(name) for name in ctx.catalog.kpis[metric].entity),
        target,
        tuple(path),
        dict(row),
        severity=severity_of(metric, row, ctx.metrics) if metric in ctx.metrics.severities else "high",
        tranche=tranche_of(metric, row, ctx.metrics),
        figure={"value": value, "unit": unit_of(column), "queryId": qid} if is_number(value) else None,
        pesos={"value": pesos, "unit": "COP", "queryId": qid} if is_number(pesos) else None,
        rule=ctx.metrics.rules.get(metric, ""),
        threshold_source=ctx.metrics.threshold_sources.get(metric, ""),
        query=dict(query),
    )


def detection_state(detection: Detection) -> dict[str, Any]:
    return {
        "metric": detection.metric,
        "entity": list(detection.entity),
        "path": [list(step) for step in detection.path],
        "row": dict(detection.row),
        "cifra": detection.figure,
        "regla": detection.rule,
        "fuente_umbral": detection.threshold_source,
        "severity": detection.severity,
        "tramo": detection.tranche,
        "pesos_en_riesgo": detection.pesos,
    }


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
