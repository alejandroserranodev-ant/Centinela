# The metered provider: one retry on a timeout, a connection error or a refused output, the cost
# of each call under its agent, the token cap of an alert, and a cached answer charged nothing.
import pytest

from centinela_agents.failures import TokenCapReached
from centinela_agents.graph import REASONS, awaiting_decision, start_alert
from centinela_agents.llm_provider import LLMProvider, LLMRequest, LLMResponse, ModelConfig
from centinela_agents.metered import MeteredProvider, add_costs, metering
from support import DAY, IDENTIFIED, Recorder, compiled, saldo_detection

ASK = LLMRequest(system_prompt="s", user_prompt="u")


class Scripted(LLMProvider):
    def __init__(self, *answers):
        super().__init__(ModelConfig(provider="fake", model="fake"))
        self.answers = list(answers)
        self.calls = 0

    def health_check(self) -> bool:
        return True

    def generate_text(self, request):
        self.calls += 1
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    generate_structured = generate_text


def reply(prompt=100, completion=20, cached=False):
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "cached": 1} if cached else {"prompt_tokens": prompt, "completion_tokens": completion}
    return LLMResponse(text="ok", stop_reason="stop", usage=usage, model="fake")


@pytest.mark.parametrize("error", [TimeoutError("lento"), ConnectionError("caído"), ValueError("no es JSON")])
def test_a_call_is_retried_once_then_answers(error):
    inner = Scripted(error, reply())
    with metering("analista", 0, None) as meter:
        MeteredProvider(inner).generate_text(ASK)
    assert inner.calls == 2 and meter.attempts == 2
    assert meter.cost() == {"analista": {"prompt_tokens": 100, "completion_tokens": 20, "calls": 1, "cached": 0}}


def test_a_second_failure_raises():
    inner = Scripted(TimeoutError("uno"), TimeoutError("dos"))
    with metering("analista", 0, None) as meter, pytest.raises(TimeoutError):
        MeteredProvider(inner).generate_text(ASK)
    assert meter.attempts == 2


def test_a_cached_answer_is_charged_nothing_and_never_reaches_the_cap():
    inner = Scripted(reply(cached=True), reply(cached=True))
    with metering("vigia", 499, 500) as meter:
        provider = MeteredProvider(inner)
        provider.generate_text(ASK)
        provider.generate_text(ASK)
    assert meter.cost() == {"vigia": {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "cached": 2}}


def test_a_call_past_the_cap_raises_before_reaching_the_model():
    inner = Scripted(reply(prompt=400, completion=200), reply())
    with metering("vigia", 0, 500) as meter:
        provider = MeteredProvider(inner)
        provider.generate_text(ASK)
        with pytest.raises(TokenCapReached):
            provider.generate_text(ASK)
    assert inner.calls == 1 and meter.attempts == 0


def test_with_no_meter_the_provider_calls_once_and_counts_nothing():
    inner = Scripted(reply())
    assert MeteredProvider(inner).generate_text(ASK).text == "ok"


def test_costs_add_by_agent():
    one = {"vigia": {"prompt_tokens": 1, "completion_tokens": 2, "calls": 1, "cached": 0}}
    assert add_costs(one, one) == {"vigia": {"prompt_tokens": 2, "completion_tokens": 4, "calls": 2, "cached": 0}}
    assert add_costs(None, {}) == {}


def model_leaves(provider, outputs):
    def calling(output):
        def run(state):
            provider.generate_text(ASK)
            return output
        return run

    return {key: calling(output) for key, output in outputs.items()}


def test_an_alert_carries_the_cost_of_each_agent():
    provider = MeteredProvider(Scripted(reply(), reply(), reply()))
    overrides = model_leaves(
        provider,
        {
            ("vigia", "titular"): {"title": {"text": "t", "figures": []}},
            ("analista", "explicar"): {"cause": IDENTIFIED, "same_cause_as": None},
        },
    )
    state = start_alert(compiled(Recorder(), overrides=overrides), saldo_detection(), alert_id="A1", day=DAY)
    assert set(state["cost"]) == {"vigia", "analista"}
    assert state["cost"]["analista"]["calls"] == 1


def test_orq_a_model_call_past_its_timeout_is_retried_once_then_falls_back_and_reaches_propuesta():
    provider = MeteredProvider(Scripted(TimeoutError("uno"), TimeoutError("dos")))
    overrides = model_leaves(provider, {("analista", "explicar"): {"cause": IDENTIFIED, "same_cause_as": None}})
    graph = compiled(Recorder(), overrides=overrides)
    state = start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    assert state["failures"] == [{"step": "hoja.analista.explicar", "kind": "timeout", "attempts": 2}]
    assert state["cause"]["reason"] == REASONS["timeout"]
    assert awaiting_decision(graph, "A1")


def test_orq_a_token_cap_reached_mid_alert_sends_every_later_model_step_to_its_fallback():
    provider = MeteredProvider(Scripted(reply(prompt=400, completion=200), reply(), reply()))
    overrides = model_leaves(
        provider,
        {
            ("vigia", "titular"): {"title": {"text": "t", "figures": []}},
            ("analista", "explicar"): {"cause": IDENTIFIED, "same_cause_as": None},
            ("estratega", "proponer"): {"actions": [], "insufficient_cause": None},
        },
    )
    graph = compiled(Recorder(), overrides=overrides, token_cap=500)
    state = start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    kinds = {failure["step"]: failure["kind"] for failure in state["failures"]}
    assert kinds["hoja.analista.explicar"] == "token_cap"
    assert state["cause"]["reason"] == REASONS["token_cap"]
    assert all(kind == "token_cap" for kind in kinds.values())
    assert awaiting_decision(graph, "A1")
