from pathlib import Path

import pytest

from centinela_agents.catalog import Catalog, Kpi, thresholds_named
from centinela_agents.metrics import load_metrics, threshold_shape_problem
from centinela_agents.predicate import compare, is_kpi, kpi_column, threshold_value

METRICAS = Path(__file__).resolve().parents[3] / "data" / "metricas.yaml"


@pytest.mark.parametrize(
    "op, left, right, expected",
    [
        (">", 16, 15, True),
        (">", 15, 15, False),
        (">=", 10, 10, True),
        ("<", 9.5, 10, True),
        ("<=", 11, 10, False),
        ("=", False, False, True),
        ("!=", "a", "b", True),
        ("en", "edit", ["approve", "edit"], True),
        ("en", None, ["approve", "edit"], False),
        ("existe", None, None, False),
        ("existe", [], None, False),
        ("existe", "A0", None, True),
    ],
)
def test_compare_applies_one_operator(op, left, right, expected):
    assert compare(op, left, right) is expected


@pytest.mark.parametrize("op", [">", ">=", "<", "<=", "=", "!="])
def test_a_null_on_either_side_is_false(op):
    assert compare(op, None, 10) is False
    assert compare(op, 10, None) is False


def test_a_threshold_is_a_value_a_column_or_a_value_by_dimension():
    row = {"cupo_credito": 5000, "clase_abc": "B"}
    assert threshold_value(15, row) == 15
    assert threshold_value({"columna": "cupo_credito"}, row) == 5000
    assert threshold_value({"por": "clase_abc", "valores": {"A": 10, "B": 7}}, row) == 7
    assert threshold_value({"por": "clase_abc", "valores": {"A": 10, "B": 7}}, {"clase_abc": "C"}) is None


def test_a_kpi_path_names_one_metric_and_one_column():
    assert is_kpi("kpi.saldo_vencido.max_dias_vencido")
    assert not is_kpi("estado.cause.kind")
    assert kpi_column("kpi.saldo_vencido.max_dias_vencido") == ("saldo_vencido", "max_dias_vencido")


def test_metricas_holds_a_threshold_per_column_for_every_metric():
    metrics = load_metrics(METRICAS)
    assert metrics.thresholds["saldo_vencido"] == {"max_dias_vencido": 15, "saldo_abierto": {"columna": "cupo_credito"}}
    assert metrics.thresholds["dias_retraso"]["recibida"] is False
    assert all(metrics.thresholds[name] for name in metrics.names)
    assert all(threshold_shape_problem(spec) is None for columns in metrics.thresholds.values() for spec in columns.values())


@pytest.mark.parametrize("spec", ["15", {"columna": 3}, {"por": "clase_abc"}, {"por": "c", "valores": {"A": "diez"}}])
def test_a_threshold_of_another_shape_is_a_problem(spec):
    assert threshold_shape_problem(spec) is not None


def test_an_umbral_names_a_metric_or_an_approved_kpi():
    metrics = load_metrics(METRICAS)
    catalog = Catalog({"retraso_habito": Kpi(("cliente_id",), frozenset({"cliente_id", "dias_sobre_habito"}), thresholds={"dias_sobre_habito": 0})})
    assert thresholds_named("saldo_vencido", metrics, catalog)["max_dias_vencido"] == 15
    assert thresholds_named("retraso_habito", metrics, catalog) == {"dias_sobre_habito": 0}
    assert thresholds_named("inventada", metrics, catalog) is None
