# The orchestrator's cases of evals/AGENTS.md that need no apps/api and no model: the tree is
# compiled with stub leaves and a stub KPI reader, and each test names its case. The cases that
# need apps/api's record (a second avanzar, the order of a day, a reason handed to the next run)
# are not here.
import pytest

from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.failures import StepTimeout
from centinela_agents.graph import REASONS, ResumeRefused, awaiting_decision, manual_owners, resume, start_alert
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Tree
from centinela_agents.validator import InvalidTree, checked_base, load_registry, problems
from centinela_agents.walk import Context, detect
from support import (
    ARBOL, DAY, DECISION_DAY, EMAIL, MANUAL_TASK, METRICAS, SALDO_ROW, SKILLS, KERNEL_CATALOG,
    Recorder, approve, base_data, base_tree, compiled, grounds, node_of, reader_from, saldo_detection, statuses,
)

CALL = {"id": "act-call", "title": "Llamada al cliente", "type": "llamada", "impact": None, "parameters": {"cliente_id": "CLI-001"}}


def started(recorder, alert_id="A1", earlier=None, **options):
    graph = compiled(recorder, **options)
    state = start_alert(graph, saldo_detection(), alert_id=alert_id, day=DAY, earlier_alerts=earlier)
    return graph, state


def test_orq_start_reports_each_agent_as_it_runs():
    entered = []
    graph = compiled(Recorder())

    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY, on_step=lambda agent, node: entered.append(agent))

    assert entered == ["vigia", "analista", "estratega"]
    assert awaiting_decision(graph, "A1")


def test_orq_a_tree_with_a_missing_no_is_refused_at_startup():
    data = base_data()
    node_of(data, "explicar.con_evidencia").pop("no")
    with pytest.raises(InvalidTree) as refused:
        checked_base(data, load_registry(ARBOL / "fundamentos.yaml"), load_metrics(METRICAS), KERNEL_CATALOG, SKILLS)
    assert "explicar.con_evidencia lacks its no" in refused.value.problems


def test_orq_a_path_to_ejecutor_without_aprobar_is_refused():
    data = base_data()
    node_of(data, "proponer.con_acciones")["si"] = "ejecutar.vigente"
    assert "hoja.ejecutor.ejecutar is reached without passing aprobar.decision" in problems(data, grounds())


def test_orq_request_changes_reproposes_once_and_refuses_a_second():
    recorder = Recorder()
    graph, _ = started(recorder)
    state = resume(graph, "A1", {"id": "dec-1", "kind": "request_changes", "reason": "Prefiero una llamada", "simulated_day": DECISION_DAY})
    assert recorder.count("estratega", "proponer") == 2
    assert awaiting_decision(graph, "A1")
    assert state["proposal_rejections"] == ["Prefiero una llamada"]
    assert state["decision"] is None
    assert statuses(state) == ["nueva", "en análisis", "propuesta"]
    with pytest.raises(ResumeRefused, match="already requested changes once"):
        resume(graph, "A1", {"id": "dec-2", "kind": "request_changes", "reason": "Otra vez", "simulated_day": DECISION_DAY})
    assert awaiting_decision(graph, "A1")
    assert resume(graph, "A1", approve(decision_id="dec-3"))["fin"] == "fin.ejecutada"


def test_orq_an_action_type_with_no_tool_becomes_one_manual_task():
    recorder = Recorder()
    graph, _ = started(recorder, overrides={("estratega", "proponer"): lambda state: {"actions": [CALL], "insufficient_cause": None}})
    final = resume(graph, "A1", approve(action_id="act-call"))
    assert recorder.count("ejecutor", "nota_manual") == 1
    assert recorder.count("ejecutor", "ejecutar") == 0
    assert final["executed_action"] == {"actionId": "act-call", "result": "Tarea creada"}
    assert final["fin"] == "fin.ejecutada"


@pytest.mark.parametrize(
    "rows",
    [{DECISION_DAY: {"saldo_vencido": [{**SALDO_ROW, "max_dias_vencido": 0}]}}, {}],
    ids=["paid", "no row"],
)
def test_orq_an_action_whose_kpi_no_longer_breaks_ends_at_ya_no_aplica(rows):
    recorder = Recorder()
    graph, _ = started(recorder, rows=rows)
    final = resume(graph, "A1", approve())
    assert final["fin"] == "fin.ya_no_aplica"
    assert final["status"] == "aprobada"
    assert recorder.count("ejecutor", "ejecutar") == 0
    assert "ejecutada" not in statuses(final)


def test_orq_two_alerts_of_one_cause_join_the_one_analysed_first():
    recorder = Recorder()
    graph, state = started(recorder, earlier={"A0": "propuesta"}, overrides={("analista", "explicar"): lambda state: {"cause": {"kind": "identified", "sentence": {"text": "x", "figures": []}, "evidence": []}, "same_cause_as": "A0"}})
    assert state["fin"] == "fin.unida"
    assert state["merged_into"] == "A0"
    assert statuses(state) == ["nueva", "en análisis", "unida"]
    assert recorder.count("estratega", "proponer") == 0


def test_orq_a_larger_alert_absorbs_a_smaller_one_still_nueva():
    recorder = Recorder()
    graph, state = started(recorder, earlier={"S1": "nueva"}, overrides={("analista", "explicar"): lambda state: {"cause": {"kind": "identified", "sentence": {"text": "x", "figures": []}, "evidence": []}, "same_cause_as": "S1"}})
    assert state["merged_alerts"] == ["S1"]
    assert ["S1", "unida"] in state["transitions"]
    assert awaiting_decision(graph, "A1")


def test_orq_three_alerts_of_one_cause_end_as_one_that_remains_and_two_unida():
    named = iter(["C1", "B1"])
    explained = {("analista", "explicar"): lambda state: {"cause": {"kind": "identified", "sentence": {"text": "x", "figures": []}, "evidence": []}, "same_cause_as": next(named)}}
    graph = compiled(Recorder(), overrides=explained)
    first = start_alert(graph, saldo_detection(), alert_id="B1", day=DAY, earlier_alerts={"C1": "nueva"})
    second = start_alert(graph, saldo_detection(), alert_id="A1", day=DAY, earlier_alerts={"B1": "propuesta"})
    assert first["merged_alerts"] == ["C1"] and ["C1", "unida"] in first["transitions"]
    assert awaiting_decision(graph, "B1")
    assert second["merged_into"] == "B1" and statuses(second) == ["nueva", "en análisis", "unida"]


@pytest.mark.parametrize("named, earlier", [("R1", {"R1": "rechazada"}), ("A1", {}), ("X9", {})], ids=["rejected", "itself", "unknown"])
def test_orq_a_same_cause_that_fails_both_checks_is_dropped_and_logged(named, earlier):
    recorder = Recorder()
    graph, state = started(recorder, earlier=earlier, overrides={("analista", "explicar"): lambda state: {"cause": {"kind": "identified", "sentence": {"text": "x", "figures": []}, "evidence": []}, "same_cause_as": named}})
    assert state["same_cause_as"] is None
    assert state["events"] == [{"kind": "same_cause_dropped", "alert": named}]
    assert awaiting_decision(graph, "A1")


def test_orq_an_estratega_fixed_to_insufficient_cause_runs_analista_twice_then_one_manual_review():
    recorder = Recorder()
    graph, state = started(recorder, overrides={("estratega", "proponer"): lambda state: {"actions": None, "insufficient_cause": "La causa no nombra el SKU"}})
    assert recorder.count("analista", "explicar") == 2
    assert recorder.received[("analista", "explicar")]["insufficient_cause"] == "La causa no nombra el SKU"
    assert recorder.count("estratega", "revision_manual") == 1
    assert state["analyst_returns"] == 1
    assert state["actions"] == [MANUAL_TASK]
    assert awaiting_decision(graph, "A1")


def test_orq_a_resume_with_no_recorded_decision_is_refused():
    recorder = Recorder()
    graph, _ = started(recorder)
    with pytest.raises(ResumeRefused, match="no record in apps/api"):
        resume(graph, "A1", {"kind": "approve", "actionId": "act-email"})
    assert awaiting_decision(graph, "A1")
    assert recorder.count("ejecutor", "ejecutar") == 0


@pytest.mark.parametrize(
    "classify, target",
    [(lambda state: "causa", "causa"), (lambda state: "otro", "ninguno"), (None, "ninguno")],
    ids=["causa", "outside the list", "classifier fails"],
)
def test_orq_a_rejection_reaches_the_classifier_and_its_failure_targets_ninguno(classify, target):
    def failing(state):
        raise RuntimeError("ollama")

    recorder = Recorder()
    graph, _ = started(recorder, classify=classify or failing)
    final = resume(graph, "A1", {"id": "dec-1", "kind": "reject", "reason": "El cliente ya pagó", "simulated_day": DECISION_DAY})
    assert final["fin"] == "fin.rechazada"
    assert final["status"] == "rechazada"
    assert final["rejection_target"] == target


def test_orq_a_model_call_past_its_timeout_takes_the_fallback_and_still_reaches_propuesta():
    def timeout(state):
        raise StepTimeout("ollama")

    recorder = Recorder()
    graph, state = started(recorder, overrides={("analista", "explicar"): timeout})
    assert state["cause"]["kind"] == "no_evidence"
    assert state["cause"]["reason"] == REASONS["timeout"]
    assert state["failures"] == [{"step": "hoja.analista.explicar", "kind": "timeout", "attempts": 0}]
    assert recorder.count("estratega", "revision_manual") == 1
    assert statuses(state)[-1] == "propuesta"



def test_orq_a_tool_or_connection_error_gives_its_own_reason_not_the_schema_one():
    def broken(state):
        raise ConnectionError("pgvector")

    graph, state = started(Recorder(), overrides={("analista", "explicar"): broken})
    assert state["cause"]["reason"] == "El análisis no terminó: no se pudo consultar la información necesaria."
    assert state["failures"] == [{"step": "hoja.analista.explicar", "kind": "error", "attempts": 0}]


def test_orq_a_failed_manual_review_still_proposes_its_task_to_its_owner():
    def timeout(state):
        raise StepTimeout("ollama")

    def broken(state):
        raise RuntimeError("revision")

    owners = manual_owners((SKILLS / "estratega" / "acciones.md").read_text(encoding="utf-8"))
    graph, state = started(Recorder(), overrides={("analista", "explicar"): timeout, ("estratega", "revision_manual"): broken}, owners=owners)
    assert state["actions"] == [{"id": "act-revision-manual", "title": "Revisión manual de la alerta", "type": "task", "impact": None, "parameters": {"owner": "Analista de cartera"}}]
    assert {"step": "hoja.estratega.revision_manual", "kind": "error", "attempts": 0} in state["failures"]
    assert awaiting_decision(graph, "A1")


def test_orq_every_metric_has_the_owner_of_its_manual_review():
    owners = manual_owners((SKILLS / "estratega" / "acciones.md").read_text(encoding="utf-8"))
    assert set(owners) == set(load_metrics(METRICAS).names)
    assert owners["margen_pct"] == "Comercial"

def test_orq_a_failed_execution_leaves_the_alert_aprobada(caplog):
    def broken(state):
        raise RuntimeError("sandbox")

    recorder = Recorder()
    graph, _ = started(recorder, overrides={("ejecutor", "ejecutar"): broken})
    final = resume(graph, "A1", approve())
    assert final["fin"] == "fin.fallo_ejecucion"
    assert final["status"] == "aprobada"
    assert any(record.levelname == "WARNING" and "A1" in record.getMessage() and "sandbox" in record.getMessage() for record in caplog.records)


RETRASO = Kpi(entity=("cliente_id",), columns=frozenset({"cliente_id", "dias_sobre_habito"}), thresholds={"dias_sobre_habito": 0})


def expanded():
    data = base_data()
    data["version"] = 2
    node_of(data, "detectar.cartera")["predicado"]["valor"].append("retraso_habito")
    node_of(data, "detectar.cartera.dias_pago_prom")["no"] = "detectar.cartera.retraso_habito"
    data["nodos"] += [
        {"id": "detectar.cartera.retraso_habito", "fundamento": "iso31000.6.4.2", "predicado": {"lee": "estado.candidato.metrica", "op": "=", "valor": "retraso_habito"}, "si": "detectar.cartera.retraso_habito.dias", "no": "fin.sin_alerta"},
        {"id": "detectar.cartera.retraso_habito.dias", "fundamento": "fin-pol-004.s4", "predicado": {"lee": "kpi.retraso_habito.dias_sobre_habito", "op": ">", "umbral": "retraso_habito"}, "si": "hoja.vigia.titular", "no": "fin.sin_alerta"},
    ]
    return data


def test_orq_walkthrough_a_customer_who_paid_in_30_days_is_6_days_late():
    late = {
        "saldo_vencido": [{"cliente_id": "CLI-007", "max_dias_vencido": 6, "saldo_abierto": 900000, "cupo_credito": 5000000}],
        "dias_pago_prom": [{"cliente_id": "CLI-007", "aumento_pct": 20.0}],
        "retraso_habito": [{"cliente_id": "CLI-007", "dias_sobre_habito": 6}],
    }
    base_ctx = Context.of(base_tree(), load_metrics(METRICAS), KERNEL_CATALOG, reader_from({DAY: late}))
    assert detect(base_ctx, DAY) == []

    catalog = Catalog({**KERNEL_CATALOG.kpis, "retraso_habito": RETRASO})
    data = expanded()
    assert problems(data, grounds(catalog=catalog)) == []
    tree = Tree.model_validate(data)
    (detection,) = detect(Context.of(tree, load_metrics(METRICAS), catalog, reader_from({DAY: late})), DAY)
    assert detection.path[-1] == ("detectar.cartera.retraso_habito.dias", "si")

    recorder = Recorder()
    graph = compiled(recorder, tree=tree, catalog=catalog, rows={DECISION_DAY: {"retraso_habito": [{"cliente_id": "CLI-007", "dias_sobre_habito": 9}]}})
    start_alert(graph, detection, alert_id="A1", day=DAY)
    assert awaiting_decision(graph, "A1")
    final = resume(graph, "A1", approve())
    assert recorder.calls == [("vigia", "titular"), ("analista", "explicar"), ("estratega", "proponer"), ("ejecutor", "ejecutar")]
    assert recorder.received[("ejecutor", "ejecutar")]["action"] == EMAIL
    assert statuses(final) == ["nueva", "en análisis", "propuesta", "ejecutada"]
