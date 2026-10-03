import pytest
from langgraph.checkpoint.memory import InMemorySaver

from centinela_agents.graph import BOUND_NODES, Compiler, MissingLeaf, ResumeRefused, awaiting_decision, compile_tree, resume, start_alert
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import ENDS, Tree, branches, index
from support import DAY, DECISION_DAY, EMAIL, METRICAS, SALDO_ROW, VIEW_CATALOG, Recorder, approve, base_data, base_tree, compiled, leaves, node_of, reader_from, saldo_detection, statuses


def test_an_alert_pauses_at_the_gate_and_executes_on_approval():
    recorder = Recorder()
    graph = compiled(recorder)
    state = start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    assert awaiting_decision(graph, "A1")
    assert statuses(state) == ["nueva", "en análisis", "propuesta"]
    assert recorder.count("ejecutor", "ejecutar") == 0
    final = resume(graph, "A1", approve())
    assert final["fin"] == "fin.ejecutada"
    assert final["status"] == "ejecutada"
    assert statuses(final) == ["nueva", "en análisis", "propuesta", "ejecutada"]
    assert ["aprobar.decision", "si"] in final["camino"]
    assert ["ejecutar.vigente", "si"] in final["camino"]


def test_ejecutor_receives_the_approved_action_and_the_decision_only():
    recorder = Recorder()
    graph = compiled(recorder)
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    resume(graph, "A1", approve())
    received = recorder.received[("ejecutor", "ejecutar")]
    assert set(received) == {"alert_id", "action", "decision"}
    assert received["action"] == EMAIL


def test_an_edit_replaces_the_parameters_ejecutor_receives():
    recorder = Recorder()
    graph = compiled(recorder)
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    edit = {"id": "dec-1", "kind": "edit", "actionId": "act-email", "parameters": {"recipient": "CLI-001", "vendedor_id": "VEN-02"}, "simulated_day": DECISION_DAY}
    resume(graph, "A1", edit)
    assert recorder.received[("ejecutor", "ejecutar")]["action"]["parameters"] == {"recipient": "CLI-001", "vendedor_id": "VEN-02"}


def test_a_leaf_with_no_function_is_refused_at_compile():
    recorder = Recorder()
    functions = leaves(recorder)
    functions.pop(("ejecutor", "nota_manual"))
    with pytest.raises(MissingLeaf, match="hoja.ejecutor.nota_manual"):
        compile_tree(base_tree(), leaves=functions, metrics=load_metrics(METRICAS), catalog=VIEW_CATALOG, reader=reader_from({}), classify=lambda state: "ninguno", checkpointer=InMemorySaver())


def test_a_resume_when_nothing_awaits_is_refused():
    graph = compiled(Recorder())
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    resume(graph, "A1", approve())
    with pytest.raises(ResumeRefused, match="awaits no decision"):
        resume(graph, "A1", approve(decision_id="dec-2"))


def test_the_compiler_caches_a_graph_by_version():
    recorder = Recorder()
    compiler = Compiler(leaves=leaves(recorder), metrics=load_metrics(METRICAS), catalog=VIEW_CATALOG, reader=reader_from({}), classify=lambda state: "ninguno", checkpointer=InMemorySaver())
    tree = base_tree()
    assert compiler.graph(tree) is compiler.graph(tree)
    assert compiler.graph(tree.model_copy(update={"version": 2})) is not compiler.graph(tree)



def test_the_compiler_keeps_apart_two_trees_of_one_version_with_different_content():
    compiler = Compiler(leaves=leaves(Recorder()), metrics=load_metrics(METRICAS), catalog=VIEW_CATALOG, reader=reader_from({}), classify=lambda state: "ninguno", checkpointer=InMemorySaver())
    data = base_data()
    data["nodos"].append({"id": "hoja.vigia.otra", "hoja": {"agente": "vigia", "decision": "titular", "skill": "vigia/contrato.md"}, "sigue": "hoja.analista.explicar"})
    node_of(data, "detectar.cartera.saldo_vencido.cupo")["no"] = "hoja.vigia.otra"
    other = Tree.model_validate(data)
    assert other.version == base_tree().version
    assert compiler.graph(other) is not compiler.graph(base_tree())
    assert compiler.graph(Tree.model_validate(base_data())) is compiler.graph(base_tree())

def test_every_node_the_interpreter_binds_a_write_to_is_in_the_base():
    nodes = index(base_tree())
    assert BOUND_NODES <= set(nodes)
    ends = {target for node in nodes.values() for _, target in branches(node) if target.startswith("fin.")}
    assert ends <= ENDS


def test_a_decision_with_no_simulated_day_is_refused():
    graph = compiled(Recorder(), rows={DECISION_DAY: {"saldo_vencido": [{**SALDO_ROW, "max_dias_vencido": 0}]}, DAY: {"saldo_vencido": [SALDO_ROW]}})
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    with pytest.raises(ResumeRefused, match="no simulated day"):
        resume(graph, "A1", {"id": "dec-1", "kind": "approve", "actionId": "act-email"})
    assert awaiting_decision(graph, "A1")


@pytest.mark.parametrize(
    "decision, message",
    [
        ({"id": "dec-1", "kind": "approve", "actionId": "act-otra", "simulated_day": DECISION_DAY}, "names no proposed action"),
        ({"id": "dec-1", "kind": "edit", "actionId": "act-email", "simulated_day": DECISION_DAY}, "carries no parameters"),
    ],
    ids=["unknown action", "edit without parameters"],
)
def test_an_approval_the_walk_cannot_carry_out_is_refused(decision, message):
    recorder = Recorder()
    graph = compiled(recorder)
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    with pytest.raises(ResumeRefused, match=message):
        resume(graph, "A1", decision)
    assert awaiting_decision(graph, "A1")
    assert recorder.count("ejecutor", "nota_manual") == 0


def test_a_leaf_that_runs_again_clears_the_outputs_it_does_not_return():
    answers = iter([{"insufficient_cause": "Falta el SKU", "actions": None}, {"actions": [EMAIL]}])
    recorder = Recorder()
    graph = compiled(recorder, overrides={("estratega", "proponer"): lambda state: next(answers)})
    state = start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    assert recorder.count("estratega", "proponer") == 2
    assert recorder.count("estratega", "revision_manual") == 0
    assert state["actions"] == [EMAIL]
    assert awaiting_decision(graph, "A1")


def test_a_vigia_leaf_the_root_does_not_reach_is_no_entry_of_the_graph():
    data = base_data()
    data["nodos"].append({"id": "hoja.vigia.huerfana", "hoja": {"agente": "vigia", "decision": "titular", "skill": "vigia/contrato.md"}, "sigue": "hoja.ejecutor.ejecutar"})
    graph = compiled(Recorder(), tree=Tree.model_validate(data))
    assert "hoja.vigia.huerfana" not in graph.get_graph().nodes
