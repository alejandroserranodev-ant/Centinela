# Tracing observes and never decides: a run with no tracer completes, and an injected tracer's
# handler sees the alert's graph under the alert's session, its resume included.
from langchain_core.callbacks import BaseCallbackHandler

from centinela_agents.graph import resume, start_alert
from centinela_agents.tracing import HandlerTracer, langfuse_tracer
from support import DAY, Recorder, approve, compiled, saldo_detection


class Seen(BaseCallbackHandler):
    def __init__(self):
        self.sessions = []

    def on_chain_start(self, serialized, inputs, **kwargs):
        self.sessions.append((kwargs.get("metadata") or {}).get("langfuse_session_id"))


def test_orq_a_run_with_no_trace_handler_completes():
    state = start_alert(compiled(Recorder()), saldo_detection(), alert_id="A1", day=DAY, tracer=None)
    assert state["status"] == "propuesta"


def test_an_injected_handler_sees_the_alert_and_its_resume_under_one_session():
    seen = Seen()
    graph = compiled(Recorder())
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY, tracer=HandlerTracer(seen))
    started = len(seen.sessions)
    resume(graph, "A1", approve(), tracer=HandlerTracer(seen))
    assert started and len(seen.sessions) > started
    assert set(seen.sessions) == {"A1"}


def test_there_is_no_langfuse_tracer_without_its_keys():
    assert langfuse_tracer({}) is None
    assert langfuse_tracer({"LANGFUSE_PUBLIC_KEY": "pk"}) is None
