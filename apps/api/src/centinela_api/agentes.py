"""
Orchestrator singleton for Centinela API.

Initialized lazily on first use. The orchestrator runs Vigía, Analista, Estratega and Ejecutor, and answers the chat,
over the kernel's KPIs, which centinela_agents.catalog.connect_kernel reaches with the DSNs of the
root .env, using LangGraph with InMemorySaver (state is per-process).
"""

import hashlib
from functools import cache
import logging
import os
import re
from collections.abc import Collection, Mapping
from dataclasses import replace
from typing import Any

from centinela_agents.action_tools import EmailDraftStub, PriceChangeDraftStub, PurchaseOrderDraftStub, TaskStub
from centinela_agents.buscar_politica import BuscarPoliticaStub
from centinela_agents.calcular_impacto import CalcularImpactoStub
from centinela_agents.catalog import Catalog, KernelAccess, connect_kernel
from centinela_agents.evidence import Ledger
from centinela_agents.metrics import Metrics, load_metrics
from centinela_agents.orchestrator import CentinelaOrchestrator
from centinela_agents.provider_factory import get_provider, get_reasoning_provider
from centinela_agents.schema import Tree
from centinela_agents.tools import ToolRegistry
from centinela_agents.walk import Context, Detection
from centinela_agents.yaml_loader import load_yaml
from langgraph.checkpoint.memory import InMemorySaver

from . import config
from .modelos import (
    Action,
    Alert,
    CauseIdentified,
    CauseNoEvidence,
    Confidence,
    Evidence,
    ExecutedAction,
    Figure,
    Impact,
    MergedAlert,
    Sentence,
)

logger = logging.getLogger(__name__)

_ROOT = config.RAIZ
_ARBOL = _ROOT / "packages" / "agents" / "arbol" / "base.yaml"
METRICAS = _ROOT / "data" / "metricas.yaml"

API_METRICS = frozenset({
    "margen_pct", "saldo_vencido", "dias_pago_prom",
    "cobertura_dias", "descuento_en_exceso", "veces_intervalo_habitual",
})
ALERTS_PER_DAY = "CENTINELA_ALERTAS_POR_DIA"

_kernel: KernelAccess | None = None
_orchestrator: CentinelaOrchestrator | None = None
_context: Context | None = None


def get_kernel() -> KernelAccess:
    """Return the kernel's catalogue, reader and call, connecting on first use."""
    global _kernel
    if _kernel is None:
        _kernel = connect_kernel(os.environ)
    return _kernel


def get_orchestrator() -> CentinelaOrchestrator:
    """Return the orchestrator singleton, building it on first call."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = _build_orchestrator()
    return _orchestrator


def get_context() -> Context:
    """Return the walk context singleton, building it on first call."""
    global _context
    if _context is None:
        kernel = get_kernel()
        _context = Context.of(_load_tree(), load_metrics(METRICAS), kernel.catalog, kernel.reader)
    return _context


def with_thresholds(ctx: Context, thresholds: Mapping[str, Mapping[str, Any]]) -> Context:
    """The context with these metrics' thresholds in place of data/metricas.yaml's, the rest untouched."""
    return replace(ctx, metrics=replace(ctx.metrics, thresholds={**ctx.metrics.thresholds, **thresholds}))


def _load_tree() -> Tree:
    return Tree.model_validate(load_yaml(_ARBOL))


def _build_orchestrator() -> CentinelaOrchestrator:
    kernel = get_kernel()
    tools = ToolRegistry(
        buscar_politica=BuscarPoliticaStub(),
        calcular_impacto=CalcularImpactoStub(),
        email_draft=EmailDraftStub(),
        task=TaskStub(),
        purchase_order_draft=PurchaseOrderDraftStub(),
        price_change_draft=PriceChangeDraftStub(),
    )
    return CentinelaOrchestrator(
        provider=get_provider(),
        tools=tools,
        tree=_load_tree(),
        metrics=load_metrics(METRICAS),
        catalog=kernel.catalog,
        reader=kernel.reader,
        checkpointer=InMemorySaver(),
        kernel=kernel.call,
        reasoning_provider=get_reasoning_provider(),
    )


@cache
def _etiquetas() -> Mapping[str, str]:
    return load_metrics(METRICAS).labels


def etiqueta(kpi: str) -> str:
    return _etiquetas().get(kpi, kpi)


def detalle_de_consulta(query: Mapping[str, Any]) -> str:
    return f"Consulta de {etiqueta(query['kpi'])} del {query['dia']}"


def alert_id_of(detection: Detection) -> str:
    """One alert per metric and entity: the id is derived from both."""
    key = "|".join([detection.metric, *map(str, detection.entity)])
    return "alerta_" + hashlib.sha256(key.encode()).hexdigest()[:16]


def pesos_of(detection: Detection) -> float:
    value = detection.row.get("pesos_en_riesgo")
    return float(value) if isinstance(value, (int, float)) else 0.0


def prioritized(detections: list[Detection], known: set[str], watched: Collection[str]) -> list[Detection]:
    """The day's new detections of the API's watched metrics, at most CENTINELA_ALERTAS_POR_DIA: the largest of each metric first, then the rest, each by pesos at risk."""
    fresh = sorted(
        (d for d in detections if d.metric in API_METRICS and d.metric in watched and alert_id_of(d) not in known),
        key=pesos_of,
        reverse=True,
    )
    largest = list({d.metric: d for d in reversed(fresh)}.values())
    first = sorted(largest, key=pesos_of, reverse=True)
    rest = [d for d in fresh if all(d is not f for f in first)]
    return [*first, *rest][: int(os.environ.get(ALERTS_PER_DAY, "3"))]


_STATUS_MAP: dict[str, str] = {
    "nueva": "new",
    "en análisis": "analyzing",
    "propuesta": "proposed",
    "aprobada": "approved",
    "rechazada": "rejected",
    "ejecutada": "executed",
    "unida": "merged",
}
STATUS_A_ESTADO: dict[str, str] = {status: estado for estado, status in _STATUS_MAP.items()}

_UNIT_MAP: dict[str, str] = {
    "COP": "COP", "%": "percent", "percent": "percent", "pts": "points", "points": "points",
    "days": "days", "días": "days", "units": "units", "unidades": "units",
}


def _safe_unit(unit: str | None) -> str:
    return _UNIT_MAP.get(unit or "units", "units")


def _derive_severity(metric: str, row: dict) -> str:
    if metric == "saldo_vencido":
        dias = float(row.get("max_dias_vencido") or 0)
        if dias > 60:
            return "critical"
        if dias > 30:
            return "high"
        return "medium"
    if metric == "cobertura_dias":
        cobertura = float(row.get("cobertura_dias") or 10)
        if cobertura < 2:
            return "critical"
        if cobertura < 5:
            return "high"
        return "medium"
    return "high"


def _convert_figures(raw: list | None) -> list[Figure]:
    result = []
    for f in raw or []:
        query_id = f.get("queryId") or f.get("query_id") if isinstance(f, dict) else None
        if not query_id:
            continue
        try:
            result.append(Figure(value=float(f["value"]), unit=_safe_unit(f.get("unit")), query_id=query_id))
        except (KeyError, TypeError, ValueError):
            logger.warning(f"Dropped a figure that is no number: {f}")
    return result


def _convert_cause(cause_data: dict | None) -> Any:
    if not cause_data:
        return CauseNoEvidence(kind="no_evidence", reason="Pendiente de análisis", queries_reviewed=[])

    if cause_data.get("kind") == "identified":
        sentence_raw = cause_data.get("sentence", "")
        if isinstance(sentence_raw, dict):
            sentence = Sentence(
                text=sentence_raw.get("text", ""),
                figures=_convert_figures(sentence_raw.get("figures")),
            )
        else:
            sentence = Sentence(text=str(sentence_raw), figures=[])

        evidence_list = []
        for e in cause_data.get("evidence") or []:
            claim_raw = e.get("claim", "")
            if isinstance(claim_raw, dict):
                claim_raw = claim_raw.get("text", "")
            figures = _convert_figures(e.get("figures"))
            if figures:
                evidence_list.append(Evidence(claim=Sentence(text=str(claim_raw), figures=figures), query_id=figures[0].query_id))

        if not evidence_list:
            return CauseNoEvidence(kind="no_evidence", reason="La causa no trajo evidencia con consultas.", queries_reviewed=[])

        return CauseIdentified(kind="identified", sentence=sentence, evidence=evidence_list)

    return CauseNoEvidence(
        kind="no_evidence",
        reason=cause_data.get("reason") or "Sin evidencia disponible",
        queries_reviewed=cause_data.get("queriesReviewed") or [],
    )


def _convert_action(action_data: dict) -> Action | None:
    if not isinstance(action_data, dict):
        return None
    try:
        description = action_data.get("description", "")
        if isinstance(description, dict):
            description = description.get("text", "")

        impact_figures = _convert_figures([action_data["impact"]] if isinstance(action_data.get("impact"), dict) else [])
        api_impact = Impact(figure=impact_figures[0], period="once") if impact_figures else None

        conf = action_data.get("confidence") or {}
        if isinstance(conf, dict):
            confidence = Confidence(
                level=conf.get("level", "medium"),
                assumptions=list(conf.get("assumptions") or []),
            )
        else:
            confidence = Confidence(level="medium")

        return Action(
            id=action_data["id"],
            title=action_data.get("title") or "Acción propuesta",
            description=Sentence(text=str(description), figures=[]),
            type=action_data.get("type", "task"),
            impact=api_impact,
            confidence=confidence,
            parameters=action_data.get("parameters") or {},
        )
    except Exception as e:
        logger.warning(f"Could not convert action {action_data.get('id')}: {e}")
        return None


def converted_actions(state: dict) -> list[Action]:
    return [a for a in (_convert_action(a) for a in (state.get("actions") or [])) if a]


def status_path(alert_id: str, state: dict) -> list[str]:
    """The API statuses the graph took the alert through, in order."""
    return [
        _STATUS_MAP[status]
        for alert, status in state.get("transitions") or []
        if alert == alert_id and status in _STATUS_MAP
    ]


def consulta_del_kpi(metric: str, day: str) -> dict[str, Any]:
    """The kernel's call for a KPI on a day, under the queryId the leaves would record for it."""
    kernel = get_kernel()
    ledger = Ledger(kernel.call, kernel.catalog)
    qid, _ = ledger.consult(metric, day)
    return ledger.queries[qid]


def con_consulta(state: dict, metric: str, day: str) -> dict:
    """The state with its alert's KPI among its queries, read from the kernel when no leaf recorded it."""
    if detection_query(state, metric):
        return state
    return {**state, "queries": [*(state.get("queries") or []), consulta_del_kpi(metric, day)]}


def nombre(alerta: Alert) -> str:
    return " · ".join(alerta.labels) or alerta.id


def detection_query(state: dict, metric: str) -> str | None:
    """The queryId under which the leaves recorded the alert's KPI, if one did."""
    for query in state.get("queries") or []:
        if isinstance(query, dict) and query.get("kpi") == metric:
            return query.get("queryId")
    return None


def _labels(metric: str, entity: tuple, metrics: Metrics, catalog: Catalog) -> list[str]:
    """The metric's short name and its entity as `<dimension> <value>`, skipping the time bucket."""
    kpi = catalog.kpis.get(metric)
    head = [metrics.labels[metric]] if metric in metrics.labels else []
    return head + [
        f"{metrics.dimension_labels.get(column, column)} {value}"
        for column, value in zip(kpi.entity if kpi else (), entity)
        if value is not None and not re.match(r"\d{4}-\d{2}-\d{2}", str(value))
    ]
def state_to_alert(alert_id: str, state: dict, detection: Detection, day_str: str) -> Alert:
    """Convert a LangGraph alert state to an API Alert model."""
    metric = detection.metric
    row = detection.row

    ctx = get_context()
    labels = _labels(metric, detection.entity, ctx.metrics, ctx.catalog)

    status = _STATUS_MAP.get(state.get("status", "nueva"), "new")
    severity = _derive_severity(metric, row)

    title_data = state.get("title") or {}
    title = Sentence(
        text=title_data.get("text") or f"Alerta {metric}",
        figures=_convert_figures(title_data.get("figures")),
    )

    cause_data = state.get("cause") or {}
    cause = _convert_cause(cause_data)
    actions = converted_actions(state)
    cause_confidence = cause_data.get("confidence") if isinstance(cause_data, dict) else None
    confidence = (
        Confidence(level=cause_confidence.get("level", "low"), assumptions=list(cause_confidence.get("assumptions") or []))
        if isinstance(cause_confidence, dict)
        else Confidence(level="low", assumptions=[])
    )

    executed_action = None
    ea = state.get("executed_action")
    if ea and isinstance(ea, dict):
        executed_action = ExecutedAction(
            action_id=ea.get("actionId") or ea.get("action_id") or "",
            result=str(ea.get("result") or ""),
        )

    return Alert(
        id=alert_id,
        status=status,
        severity=severity,
        metric=metric,
        labels=labels,
        title=title,
        pesos_at_risk=Figure(
            value=pesos_of(detection),
            unit="COP",
            query_id=detection_query(state, metric) or f"kpi_consultar:{metric}:{day_str}",
        ),
        recoverable_per_month=None,
        confidence=confidence,
        simulated_date=day_str,
        cause=cause,
        actions=actions,
        executed_action=executed_action,
        merged_into=state.get("merged_into") if status == "merged" else None,
    )


def _entity_labels(metric: str, entity: tuple) -> list[str]:
    ctx = get_context()
    return _labels(metric, entity, ctx.metrics, ctx.catalog)[1 if metric in ctx.metrics.labels else 0:]


def brief_of_alert(alerta: Alert) -> dict[str, Any]:
    """What Analista reads of an earlier alert: its metric, its entity and the sentence of its cause."""
    ctx = get_context()
    skip = 1 if alerta.metric in ctx.metrics.labels and alerta.labels[:1] == [ctx.metrics.labels[alerta.metric]] else 0
    cause = alerta.cause.sentence.model_dump(by_alias=True) if isinstance(alerta.cause, CauseIdentified) else None
    return {"metric": alerta.metric, "entity": alerta.labels[skip:], "cause": cause}


def brief_of_detection(detection: Detection) -> dict[str, Any]:
    """What Analista reads of a detection of the day not yet run: its metric and its entity, no cause."""
    return {"metric": detection.metric, "entity": _entity_labels(detection.metric, detection.entity), "cause": None}


def merged_summary(alerta: Alert) -> MergedAlert:
    return MergedAlert(
        id=alerta.id,
        metric=alerta.metric,
        simulated_date=alerta.simulated_date,
        title=alerta.title,
        pesos_at_risk=alerta.pesos_at_risk,
        cause=alerta.cause,
    )


ABSORBIDA = "La explica la causa de la alerta que queda."


def absorbed_alert(alert_id: str, detection: Detection, into: str, day_str: str, consulta: Mapping[str, Any]) -> Alert:
    """A detection of the day another alert's cause absorbed before its run: stored merged, never run, citing its KPI's call."""
    description = get_context().metrics.descriptions.get(detection.metric, detection.metric)
    state = {
        "status": "unida",
        "merged_into": into,
        "queries": [dict(consulta)],
        "title": {"text": ": ".join([description, ", ".join(_entity_labels(detection.metric, detection.entity))]), "figures": []},
        "cause": {"kind": "no_evidence", "reason": ABSORBIDA, "queriesReviewed": [consulta["queryId"]]},
    }
    return state_to_alert(alert_id, state, detection, day_str)
