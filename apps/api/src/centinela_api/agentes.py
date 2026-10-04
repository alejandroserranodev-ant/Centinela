"""
Orchestrator singleton for Centinela API.

Initialized lazily on first use. The orchestrator runs Vigía, Analista, Estratega,
and Ejecutor agents using LangGraph with InMemorySaver (state is per-process).
"""

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.metrics import Metrics, load_metrics
from centinela_agents.orchestrator import CentinelaOrchestrator
from centinela_agents.provider_factory import get_provider
from centinela_agents.schema import Tree
from centinela_agents.tools import ToolRegistry
from centinela_agents.walk import Context, Detection
from centinela_agents.yaml_loader import load_yaml
from langgraph.checkpoint.memory import InMemorySaver

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
    Sentence,
)

logger = logging.getLogger(__name__)

# --- Paths ---
# agentes.py lives at: apps/api/src/centinela_api/agentes.py
# parents[4] = project root
_ROOT = Path(__file__).resolve().parents[4]
_ARBOL = _ROOT / "packages" / "agents" / "arbol" / "base.yaml"
_METRICAS = _ROOT / "data" / "metricas.yaml"


# --- KPI Catalog (mirrors packages/agents/tests/support.py VIEW_CATALOG) ---

def _kpi(entity: list, *columns: str) -> Kpi:
    return Kpi(entity=tuple(entity), columns=frozenset({*entity, *columns}))


VIEW_CATALOG = Catalog({
    "margen_pct": _kpi(["semana", "linea"], "ventas", "costo", "margen_pct", "caida_pts", "margen_minimo_pct"),
    "saldo_vencido": _kpi(["cliente_id"], "segmento", "cupo_credito", "plazo_dias", "saldo_abierto", "saldo_vencido", "max_dias_vencido", "dias_pago_prom_120d"),
    "concentracion_vencida_pct": _kpi(["cliente_id"], "saldo_vencido", "concentracion_vencida_pct"),
    "dias_pago_prom": _kpi(["cliente_id", "mes_factura"], "dias_pago_prom", "facturas_pagadas", "aumento_pct"),
    "cobertura_dias": _kpi(["sku", "bodega_id"], "linea", "clase_abc", "existencia", "demanda_prom_30d", "cobertura_dias", "unidades_pendientes"),
    "variacion_costo_pct": _kpi(["sku"], "linea", "clase_abc", "proveedor_id", "costo_unitario", "costo_anterior", "variacion_pct", "fecha_vigencia", "dias_habiles_sin_traslado"),
    "dias_retraso": _kpi(["oc_id"], "proveedor_id", "sku", "bodega_id", "fecha_esperada", "cantidad", "costo_unitario", "recibida", "dias_retraso"),
    "descuento_en_exceso": _kpi(["vendedor_id", "semana"], "descuento_en_exceso"),
    "margen_bruto_negativo": _kpi(["pedido_id", "linea_n"], "sku", "margen_bruto"),
    "veces_intervalo_habitual": _kpi(["cliente_id"], "pedidos", "ultima_compra", "intervalo_prom_dias", "dias_sin_comprar", "veces_intervalo_habitual"),
})

# Metrics supported by the API Alert model
API_METRICS = frozenset({
    "margen_pct", "saldo_vencido", "dias_pago_prom",
    "cobertura_dias", "descuento_en_exceso", "veces_intervalo_habitual",
})

# --- Demo KPI rows (satisfy detection predicates in arbol/base.yaml) ---
_DEMO_ROWS: dict[str, list[dict]] = {
    "saldo_vencido": [
        {
            "cliente_id": "CLI-001",
            "segmento": "Mayorista",
            "cupo_credito": 5_000_000,
            "saldo_abierto": 1_200_000,
            "saldo_vencido": 800_000,
            "max_dias_vencido": 20,     # > 15 → detectar.cartera.saldo_vencido.dias
            "plazo_dias": 30,
            "dias_pago_prom_120d": 35,
        },
    ],
    "cobertura_dias": [
        {
            "sku": "SKU-A01",
            "bodega_id": "BOD-01",
            "linea": "Electrodomesticos",
            "clase_abc": "A",
            "existencia": 50,
            "demanda_prom_30d": 20.0,
            "cobertura_dias": 2.5,      # < 10 for class A → detectar.inventario.cobertura_dias.minima
            "unidades_pendientes": 0,
        },
    ],
}


def _demo_reader(metric: str, day: str) -> list[dict]:
    """Demo KPI reader: returns sample rows regardless of simulated day."""
    return _DEMO_ROWS.get(metric, [])


# --- Lazy singletons ---

_orchestrator: CentinelaOrchestrator | None = None
_context: Context | None = None


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
        tree = _load_tree()
        metrics = load_metrics(_METRICAS)
        _context = Context.of(tree, metrics, VIEW_CATALOG, _demo_reader)
    return _context


def _load_tree() -> Tree:
    return Tree.model_validate(load_yaml(_ARBOL))


def _build_orchestrator() -> CentinelaOrchestrator:
    tree = _load_tree()
    metrics = load_metrics(_METRICAS)
    provider = get_provider()
    tools = ToolRegistry()          # all tool providers optional; agents degrade gracefully
    checkpointer = InMemorySaver()  # per-process state; lost on restart
    return CentinelaOrchestrator(
        provider=provider,
        tools=tools,
        tree=tree,
        metrics=metrics,
        catalog=VIEW_CATALOG,
        reader=_demo_reader,
        checkpointer=checkpointer,
    )


# --- Graph state → API Alert conversion ---

_STATUS_MAP: dict[str, str] = {
    "nueva": "new",
    "en análisis": "analyzing",
    "propuesta": "proposed",
    "aprobada": "approved",
    "rechazada": "rejected",
    "ejecutada": "executed",
}

_UNIT_MAP: dict[str, str] = {
    "COP": "COP", "%": "percent", "pts": "points", "points": "points",
    "days": "days", "días": "days", "units": "units", "unidades": "units",
}


def _safe_unit(unit: str | None) -> str:
    return _UNIT_MAP.get(unit or "COP", "COP")


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


def _derive_pesos_at_risk(metric: str, row: dict) -> float:
    if metric == "saldo_vencido":
        return float(row.get("saldo_vencido") or 0)
    if metric == "margen_pct":
        ventas = float(row.get("ventas") or 0)
        caida = float(row.get("caida_pts") or 0)
        return ventas * caida / 100
    if metric == "cobertura_dias":
        demanda = float(row.get("demanda_prom_30d") or 0)
        return demanda * 10 * 30_000  # rough: 10 days of stock * avg unit price
    return 0.0


def _convert_figures(raw: list | None) -> list[Figure]:
    result = []
    for f in raw or []:
        if not isinstance(f, dict):
            continue
        try:
            result.append(Figure(
                value=float(f.get("value", 0)),
                unit=_safe_unit(f.get("unit")),
                query_id=f.get("queryId") or f.get("query_id") or "q_0",
            ))
        except Exception:
            pass
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
            figs = e.get("figures") or []
            first_qid = figs[0].get("queryId", "q_0") if figs else "q_0"
            evidence_list.append(Evidence(
                claim=Sentence(text=str(claim_raw), figures=_convert_figures(figs)),
                query_id=first_qid,
            ))

        if not evidence_list:
            evidence_list = [Evidence(claim=Sentence(text="Análisis completado"), query_id="q_0")]

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

        agent_impact = action_data.get("impact")
        api_impact = None
        if isinstance(agent_impact, dict) and agent_impact.get("value") is not None:
            api_impact = Impact(
                figure=Figure(
                    value=float(agent_impact["value"]),
                    unit=_safe_unit(agent_impact.get("unit")),
                    query_id=agent_impact.get("queryId") or agent_impact.get("query_id") or "q_0",
                ),
                period="once",
            )

        conf = action_data.get("confidence") or {}
        if isinstance(conf, dict):
            confidence = Confidence(
                level=conf.get("level", "medium"),
                assumptions=list(conf.get("assumptions") or []),
            )
        else:
            confidence = Confidence(level="medium")

        return Action(
            id=action_data.get("id") or f"act_{uuid.uuid4().hex[:8]}",
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
    pesos_val = _derive_pesos_at_risk(metric, row)

    title_data = state.get("title") or {}
    title = Sentence(
        text=title_data.get("text") or f"Alerta {metric}",
        figures=_convert_figures(title_data.get("figures")),
    )

    cause = _convert_cause(state.get("cause"))
    actions = [a for a in (_convert_action(a) for a in (state.get("actions") or [])) if a]

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
        pesos_at_risk=Figure(value=pesos_val, unit="COP", query_id="q_detect"),
        recoverable_per_month=None,
        confidence=Confidence(level="medium", assumptions=[]),
        simulated_date=day_str,
        cause=cause,
        actions=actions,
        executed_action=executed_action,
    )
