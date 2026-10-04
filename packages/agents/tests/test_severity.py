# The severity and tranches of data/metricas.yaml: the base loads clean, each planted violation is
# refused by the validator, and a KPI row takes the level its conditions or tranche name.
from dataclasses import replace

import pytest

from centinela_agents.metrics import load_metrics
from centinela_agents.severity import severity_of, severity_problems, tranche_of
from centinela_agents.validator import problems
from support import KERNEL_CATALOG, METRICAS, base_data, grounds

REAL = load_metrics(METRICAS)
DEFAULT = {"nivel": "high", "fuente": "supuesto"}
LOW_STOCK = {"columna": "cobertura_dias", "op": "<", "umbral": 5}
TRANCHES = {
    "fuente": "FIN-POL-004 §4",
    "columna": "max_dias_vencido",
    "niveles": [
        {"tramo": "tramo_1", "desde": 1, "hasta": 15},
        {"tramo": "tramo_2", "desde": 16, "hasta": 30},
        {"tramo": "tramo_3", "desde": 31, "hasta": 60},
        {"tramo": "tramo_4", "desde": 61},
    ],
}


def critical_when(*conditions, **extra):
    return {"por_defecto": DEFAULT, "niveles": [{"nivel": "critical", "fuente": "OPE-POL-007 §2", "cuando": list(conditions), **extra}]}


def severities(metric, block):
    kept = {name: value for name, value in REAL.severities.items() if name != metric}
    return replace(REAL, severities=kept if block is None else {**kept, metric: block})


def tranches(levels, **block):
    return replace(REAL, tranches={**REAL.tranches, "saldo_vencido": {**TRANCHES, "niveles": levels, **block}})


def test_the_base_metrics_carry_valid_severity_and_tranches():
    assert severity_problems(REAL, KERNEL_CATALOG) == []


@pytest.mark.parametrize(
    "block, message",
    [
        (None, "has no severidad"),
        ({"por_defecto": {"nivel": "high"}}, "por_defecto needs"),
        ({"por_defecto": {"nivel": "urgente", "fuente": "x"}}, "por_defecto needs"),
        (critical_when({"columna": "nada", "op": "<", "umbral": 5}), "reads nada"),
        (critical_when({"columna": "cobertura_dias", "op": "~", "umbral": 5}), "compares with"),
        (critical_when({"columna": "cobertura_dias", "op": "<", "umbral": "cinco"}), "is no number"),
        (critical_when({"columna": "cobertura_dias", "op": "<", "umbral": {"columna": "nada"}}), "is no column"),
        (critical_when({"columna": "cobertura_dias", "op": "<"}), "not columna, op and umbral"),
        ({"por_defecto": DEFAULT, "niveles": [{"nivel": "critical", "cuando": [LOW_STOCK]}]}, "has no fuente"),
        (critical_when(LOW_STOCK, tramo="tramo_4"), "cuando or tramo"),
        ({"por_defecto": DEFAULT, "niveles": [{"nivel": "medium", "fuente": "x", "cuando": [LOW_STOCK]}]}, "no higher than por_defecto"),
        ({"por_defecto": DEFAULT, "niveles": [{"nivel": "critical", "fuente": "x", "tramo": "tramo_9"}]}, "absent from the metric's tramos"),
    ],
)
def test_a_planted_severity_violation_is_refused(block, message):
    found = severity_problems(severities("cobertura_dias", block), KERNEL_CATALOG)
    assert any(message in problem for problem in found), found


@pytest.mark.parametrize(
    "metrics, message",
    [
        (tranches([{"tramo": "tramo_1", "desde": 1, "hasta": 15}, {"tramo": "tramo_2", "desde": 17}]), "a gap or an overlap"),
        (tranches([{"tramo": "tramo_1", "desde": 1, "hasta": 15}, {"tramo": "tramo_2", "desde": 15}]), "a gap or an overlap"),
        (tranches([{"tramo": "tramo_1", "desde": 1}, {"tramo": "tramo_2", "desde": 16}]), "has no hasta and is not the last"),
        (tranches(TRANCHES["niveles"], columna="nada"), "reads nada"),
        (tranches(TRANCHES["niveles"], fuente=" "), "has no fuente"),
        (tranches([{"tramo": "tramo_1", "desde": "uno"}]), "needs tramo, a number desde"),
    ],
)
def test_a_planted_tranche_violation_is_refused(metrics, message):
    found = severity_problems(metrics, KERNEL_CATALOG)
    assert any(message in problem for problem in found), found


def test_the_validator_refuses_a_metric_with_no_severidad():
    found = problems(base_data(), grounds(metrics=severities("margen_pct", None)))
    assert "metric margen_pct has no severidad" in found


@pytest.mark.parametrize(
    "row, expected",
    [
        ({"cobertura_dias": 4.0, "pedidos_pendientes": 2}, "critical"),
        ({"cobertura_dias": 4.0, "pedidos_pendientes": 0}, "high"),
        ({"cobertura_dias": 8.0, "pedidos_pendientes": 3}, "high"),
        ({"cobertura_dias": None, "pedidos_pendientes": 3}, "high"),
    ],
)
def test_cobertura_is_critical_under_five_days_with_orders_pending(row, expected):
    assert severity_of("cobertura_dias", row, REAL) == expected


@pytest.mark.parametrize(
    "days, tranche, expected",
    [(0, None, "high"), (20, "tramo_2", "high"), (60, "tramo_3", "high"), (61, "tramo_4", "critical"), (None, None, "high")],
)
def test_saldo_vencido_takes_its_tranche_and_the_tranche_its_severity(days, tranche, expected):
    row = {"max_dias_vencido": days}
    assert tranche_of("saldo_vencido", row, REAL) == tranche
    assert severity_of("saldo_vencido", row, REAL) == expected


def test_a_metric_with_no_level_holding_takes_por_defecto():
    assert severity_of("margen_pct", {"caida_pts": 9.0}, REAL) == "high"
