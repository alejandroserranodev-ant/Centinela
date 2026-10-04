# The day run of packages/agents: the alert id, the coverage by earlier alerts, the order of a day,
# and run_day driven with verdicts over the compiled base tree with stub leaves.
import datetime as dt
import hashlib
import json

import pytest

from centinela_agents.day import Earlier, alert_id, covered, entity_labels, labels, ordered
from centinela_agents.metrics import load_metrics
from centinela_agents.walk import Detection
from support import DAY, KERNEL_CATALOG, METRICAS


def detection(metric="saldo_vencido", entity=("CLI-001",), pesos=500.0, severity="high"):
    figure = None if pesos is None else {"value": pesos, "unit": "COP", "queryId": "q"}
    return Detection(metric, tuple(entity), "hoja.vigia.titular", (), {}, severity=severity, pesos=figure)


def test_the_alert_id_hashes_metric_entity_and_day():
    expected = "alerta_" + hashlib.sha256(json.dumps(["saldo_vencido", ["CLI-001"], DAY], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:16]
    assert alert_id("saldo_vencido", ("CLI-001",), DAY) == expected
    assert alert_id("saldo_vencido", ("CLI-001",), DAY) != alert_id("saldo_vencido", ("CLI-001",), "2026-03-03")
    assert alert_id("margen_pct", ("Línea Hogar",), DAY).startswith("alerta_")


@pytest.mark.parametrize(
    "earlier_severity, detected, is_covered",
    [("high", "high", True), ("critical", "high", True), ("high", "critical", False)],
)
def test_an_earlier_alert_covers_a_detection_unless_its_severity_rises(earlier_severity, detected, is_covered):
    earlier = [Earlier("E1", "saldo_vencido", ("CLI-001",), earlier_severity, "rechazada")]
    assert covered(detection(severity=detected), earlier) is is_covered


def test_coverage_compares_the_highest_earlier_severity_and_ignores_other_entities():
    earlier = [
        Earlier("E1", "saldo_vencido", ("CLI-001",), "high", "ejecutada"),
        Earlier("E2", "saldo_vencido", ("CLI-001",), "critical", "unida"),
        Earlier("E3", "saldo_vencido", ("CLI-002",), "low", "propuesta"),
        Earlier("E4", "saldo_vencido", None, "low", "propuesta"),
    ]
    assert covered(detection(severity="critical"), earlier)
    assert not covered(detection(entity=("CLI-003",)), earlier)


def test_coverage_matches_an_entity_read_back_from_json():
    stored = tuple(json.loads(json.dumps(["VEN-01", dt.date(2026, 3, 2)], default=str)))
    earlier = [Earlier("E1", "descuento_en_exceso", stored, "high", "propuesta")]
    assert covered(detection("descuento_en_exceso", ("VEN-01", dt.date(2026, 3, 2))), earlier)


def test_a_day_orders_a_metric_first_then_pesos_then_severity_then_id_and_caps():
    tied = [detection(entity=(name,), pesos=500.0) for name in ("CLI-003", "CLI-001")]
    critical = detection(entity=("CLI-002",), pesos=500.0, severity="critical")
    other = detection("margen_pct", ("Hogar",), pesos=10.0)
    unmeasured = detection(entity=("CLI-004",), pesos=None)
    chosen = ordered([*tied, unmeasured, other, critical], DAY, 5)
    by_id = sorted(("CLI-001", "CLI-003"), key=lambda name: alert_id("saldo_vencido", (name,), DAY))
    assert [d.entity[0] for d in chosen] == ["CLI-002", "Hogar", *by_id, "CLI-004"]
    assert len(ordered([*tied, unmeasured, other, critical], DAY, 2)) == 2


def test_the_labels_name_the_metric_then_the_entity_without_the_time_bucket():
    metrics = load_metrics(METRICAS)
    assert labels("saldo_vencido", ("CLI-001",), metrics, KERNEL_CATALOG) == ["Cartera vencida", "cliente CLI-001"]
    assert entity_labels("descuento_en_exceso", ("VEN-01", "2026-03-02"), metrics, KERNEL_CATALOG) == ["vendedor VEN-01"]
