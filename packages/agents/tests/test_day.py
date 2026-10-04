# The day run of packages/agents: the alert id, the coverage by earlier alerts, the order of a day,
# and run_day driven with verdicts over the compiled base tree with stub leaves.
import datetime as dt
import hashlib
import json

import pytest

from centinela_agents.day import AlertFailed, AlertRun, Earlier, Step, Verdict, alert_id, covered, entity_labels, labels, ordered, run_day
from centinela_agents.metrics import load_metrics
from centinela_agents.walk import Context, Detection
from support import DAY, IDENTIFIED, KERNEL_CATALOG, METRICAS, Recorder, base_tree, compiled, reader_from


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


RECORDED = Verdict(recorded=True)


def saldo(cliente, pesos=500, dias=20):
    return {"cliente_id": cliente, "cupo_credito": 5000000, "saldo_abierto": 1200000, "saldo_vencido": pesos, "max_dias_vencido": dias, "pesos_en_riesgo": pesos}


def context(*rows):
    return Context.of(base_tree(), load_metrics(METRICAS), KERNEL_CATALOG, reader_from({DAY: {"saldo_vencido": list(rows)}}))


def drive(run, answer=lambda event: RECORDED):
    events, sent = [], None
    while True:
        try:
            event = run.send(sent)
        except StopIteration:
            return events
        sent = answer(event) if isinstance(event, AlertRun) else None
        events.append(event)


def runs(events):
    return [event for event in events if isinstance(event, AlertRun)]


def test_orq_a_day_of_three_tied_alerts_runs_the_critical_first_then_by_id():
    rows = [saldo("CLI-001"), saldo("CLI-002", dias=61), saldo("CLI-003")]
    events = drive(run_day(compiled(Recorder()), context(*rows), DAY, limit=3))
    tail = sorted(("CLI-001", "CLI-003"), key=lambda name: alert_id("saldo_vencido", (name,), DAY))
    assert [run.detection.entity[0] for run in runs(events)] == ["CLI-002", *tail]
    assert all(run.state["status"] == "propuesta" for run in runs(events))


def test_orq_an_earlier_alert_of_equal_severity_covers_a_detection_and_a_higher_one_does_not():
    earlier = [Earlier("E1", "saldo_vencido", ("CLI-001",), "high", "rechazada"), Earlier("E2", "saldo_vencido", ("CLI-002",), "high", "ejecutada")]
    events = drive(run_day(compiled(Recorder()), context(saldo("CLI-001"), saldo("CLI-002", dias=61)), DAY, earlier=earlier))
    assert [run.detection.entity[0] for run in runs(events)] == ["CLI-002"]


def test_the_same_day_run_twice_proposes_the_same_ids():
    rows = [saldo("CLI-001"), saldo("CLI-002", pesos=900)]
    first = [run.alert_id for run in runs(drive(run_day(compiled(Recorder()), context(*rows), DAY)))]
    second = [run.alert_id for run in runs(drive(run_day(compiled(Recorder()), context(*rows), DAY)))]
    assert first == second == [alert_id("saldo_vencido", ("CLI-002",), DAY), alert_id("saldo_vencido", ("CLI-001",), DAY)]


def test_orq_a_refused_transition_ends_its_alert_and_the_day_goes_on():
    recorder = Recorder()
    rows = [saldo("CLI-001", pesos=900), saldo("CLI-002")]
    first_id = alert_id("saldo_vencido", ("CLI-001",), DAY)
    events = drive(run_day(compiled(recorder), context(*rows), DAY), answer=lambda run: Verdict(recorded=run.alert_id != first_id))
    assert len(runs(events)) == 2
    assert first_id not in recorder.received[("analista", "explicar")]["earlier_alerts"]


def test_orq_a_recorded_proposal_is_a_merge_candidate_for_the_next_alert():
    recorder = Recorder()
    rows = [saldo("CLI-001", pesos=900), saldo("CLI-002")]
    drive(run_day(compiled(recorder), context(*rows), DAY))
    first_id = alert_id("saldo_vencido", ("CLI-001",), DAY)
    assert recorder.received[("analista", "explicar")]["earlier_alerts"] == {first_id: "propuesta"}
    assert recorder.received[("analista", "explicar")]["alert_briefs"][first_id]["entity"] == ["cliente CLI-001"]


def absorbing(state):
    pending = [other for other, status in state["earlier_alerts"].items() if status == "nueva"]
    return {"cause": IDENTIFIED, "same_cause_as": pending[0] if pending else None}


def test_orq_an_accepted_absorption_removes_the_later_alert_from_the_run():
    rows = [saldo("CLI-001", pesos=900), saldo("CLI-002")]
    later = alert_id("saldo_vencido", ("CLI-002",), DAY)
    graph = compiled(Recorder(), overrides={("analista", "explicar"): absorbing})
    events = drive(run_day(graph, context(*rows), DAY), answer=lambda run: Verdict(recorded=True, absorbed=tuple(run.absorbed)))
    (only,) = runs(events)
    assert set(only.absorbed) == {later} and only.absorbed[later].entity == ("CLI-002",)


def test_a_refused_absorption_leaves_the_later_alert_to_run():
    rows = [saldo("CLI-001", pesos=900), saldo("CLI-002")]
    graph = compiled(Recorder(), overrides={("analista", "explicar"): absorbing})
    assert len(runs(drive(run_day(graph, context(*rows), DAY)))) == 2


def test_orq_a_refused_merge_runs_the_alert_again_without_that_target():
    earlier = [Earlier("E1", "saldo_vencido", ("CLI-009",), "high", "propuesta", {"metric": "saldo_vencido", "entity": ["cliente CLI-009"], "cause": None})]
    naming = lambda state: {"cause": IDENTIFIED, "same_cause_as": "E1" if "E1" in state["earlier_alerts"] else None}
    graph = compiled(Recorder(), overrides={("analista", "explicar"): naming})
    answer = lambda run: Verdict(recorded=False, refused_merge="E1") if run.state["status"] == "unida" else RECORDED
    first, second = runs(drive(run_day(graph, context(saldo("CLI-001")), DAY, earlier=earlier), answer=answer))
    assert first.alert_id == second.alert_id
    assert (first.state["status"], second.state["status"]) == ("unida", "propuesta")
    events = drive(run_day(graph, context(saldo("CLI-001")), DAY, earlier=earlier), answer=answer)
    assert [(e.agent, e.node) for e in events if isinstance(e, Step)].count(("vigia", "detectar")) == 1


def test_only_a_proposed_earlier_alert_is_a_merge_candidate():
    recorder = Recorder()
    earlier = [Earlier("E1", "saldo_vencido", ("CLI-008",), "high", "en análisis"), Earlier("E2", "saldo_vencido", ("CLI-009",), "high", "propuesta")]
    drive(run_day(compiled(recorder), context(saldo("CLI-001")), DAY, earlier=earlier))
    assert recorder.received[("analista", "explicar")]["earlier_alerts"] == {"E2": "propuesta"}


def test_each_alert_opens_with_its_detection_then_its_leaves():
    events = drive(run_day(compiled(Recorder()), context(saldo("CLI-001")), DAY))
    steps = [(event.agent, event.node, event.status) for event in events if isinstance(event, Step)]
    assert steps[0] == ("vigia", "detectar", "done")
    assert steps[1:3] == [("vigia", "hoja.vigia.titular", "running"), ("vigia", "hoja.vigia.titular", "done")]
    assert all(isinstance(event, Step) and event.entity == ("CLI-001",) for event in events if not isinstance(event, AlertRun))


def test_a_caller_that_sends_no_verdict_is_refused():
    run = run_day(compiled(Recorder()), context(saldo("CLI-001")), DAY)
    event = next(run)
    while not isinstance(event, AlertRun):
        event = run.send(None)
    with pytest.raises(RuntimeError, match="no verdict"):
        run.send(None)


def test_a_failed_alert_is_yielded_and_the_day_goes_on(monkeypatch):
    import centinela_agents.day as day_module

    real = day_module.stream_alert
    first_id = alert_id("saldo_vencido", ("CLI-001",), DAY)

    def breaking(graph, detection, *, alert_id, **options):
        if alert_id == first_id:
            raise RuntimeError("el grafo cayó")
        yield from real(graph, detection, alert_id=alert_id, **options)

    monkeypatch.setattr(day_module, "stream_alert", breaking)
    events = drive(run_day(compiled(Recorder()), context(saldo("CLI-001", pesos=900), saldo("CLI-002")), DAY))
    failed = [event for event in events if isinstance(event, AlertFailed)]
    assert [event.alert_id for event in failed] == [first_id] and len(runs(events)) == 1


def test_an_unwatched_metric_raises_no_alert():
    assert runs(drive(run_day(compiled(Recorder()), context(saldo("CLI-001")), DAY, watched={"margen_pct"}))) == []


def test_orq_each_alert_of_a_day_carries_the_version_of_the_tree_it_walked():
    tree = base_tree().model_copy(update={"version": 7})
    ctx = Context.of(tree, load_metrics(METRICAS), KERNEL_CATALOG, reader_from({DAY: {"saldo_vencido": [saldo("CLI-001")]}}))
    (run,) = runs(drive(run_day(compiled(Recorder(), tree=tree), ctx, DAY)))
    assert run.state["arbol_version"] == 7
