# The prompt-capture test of Ley 1581: a day run, the approval that resumes one of its alerts and
# two chat questions go through the orchestrator with a provider that records every request. No
# recorded prompt holds a client id, a seller id or a name a row carried, one entity reads one
# placeholder across the day, and every answer comes back with the original in place of the
# placeholder the model wrote.
import re

from langgraph.checkpoint.memory import InMemorySaver

from centinela_agents.day import AlertRun, Verdict
from centinela_agents.llm_provider import LLMProvider, LLMResponse, LLMStructuredResponse, ModelConfig
from centinela_agents.metrics import load_metrics
from centinela_agents.orchestrator import CentinelaOrchestrator
from centinela_agents.tools import ToolRegistry
from centinela_agents.walk import Context
from support import DAY, DECISION_DAY, KERNEL_CATALOG, METRICAS, approve, base_tree, reader_from

PLACEHOLDER = re.compile(r"\b(?:CLIENTE|VENDEDOR|NOMBRE)_[A-Z]{6,}\b")
CLEAR = ("CLI-001", "CLI-002", "VEN-01", "Ferretería López")


def saldo(cliente, nombre=None):
    row = {"cliente_id": cliente, "vendedor_id": "VEN-01", "cupo_credito": 5000000, "saldo_abierto": 1200000, "saldo_vencido": 900, "max_dias_vencido": 20, "pesos_en_riesgo": 900}
    return {**row, "nombre": nombre} if nombre else row


DAY_ROWS = {"saldo_vencido": [saldo("CLI-001", "Ferretería López"), saldo("CLI-002")]}
ROWS = {DAY: DAY_ROWS, DECISION_DAY: DAY_ROWS}


class Recording(LLMProvider):
    def __init__(self, chat_entity=None):
        super().__init__(ModelConfig(provider="fake", model="fake"))
        self.requests = []
        self.chat_entity = chat_entity

    def health_check(self) -> bool:
        return True

    def first(self, request) -> str:
        found = PLACEHOLDER.search(request.user_prompt)
        return found.group(0) if found else "nadie"

    def generate_text(self, request):
        self.requests.append(request)
        if "figures:" not in request.user_prompt:
            return LLMResponse(text=f"Le escribimos sobre la cuenta {self.first(request)}.", stop_reason="stop", usage={}, model="fake")
        return LLMResponse(text=f"Cartera vencida de {self.first(request)} por {{0}}", stop_reason="stop", usage={}, model="fake")

    def generate_structured(self, request):
        self.requests.append(request)
        fields = set(request.schema.get("properties", {}))
        if "intent" in fields:
            parsed = {"intent": "dato", "kpi": "saldo_vencido", "entity": self.chat_entity or self.first(request), "periodo": ""}
        elif "sentences" in fields:
            parsed = {"sentences": [{"text": f"{self.first(request)} debe {{0}}.", "figures": ["f1"]}], "assumptions": []}
        elif "sentence" in fields:
            parsed = {"kind": "identified", "sentence": f"{self.first(request)} dejó de pagar {{0}}", "sentence_figures": ["f1"], "evidence": [], "reason": "", "confidence": "high", "assumptions": []}
        elif "actions" in fields:
            row = re.search(r"^(\S+): \[email_draft\]", request.user_prompt, re.MULTILINE)
            parsed = {"actions": [{"row": row.group(1), "title": "Recordar el pago", "description": "Escribir al cliente."}], "insufficient_cause": False}
        else:
            parsed = {"destino": "ninguno"}
        return LLMStructuredResponse(text="{}", parsed=parsed, stop_reason="stop", usage={}, model="fake")


def orchestrator(provider):
    return CentinelaOrchestrator(
        provider=provider,
        tools=ToolRegistry(),
        tree=base_tree(),
        metrics=load_metrics(METRICAS),
        catalog=KERNEL_CATALOG,
        reader=reader_from(ROWS),
        checkpointer=InMemorySaver(),
        owners={},
    )


def day_runs(orq):
    run, sent, runs = orq.run_day(Context.of(base_tree(), load_metrics(METRICAS), KERNEL_CATALOG, reader_from(ROWS)), DAY), None, []
    while True:
        try:
            event = run.send(sent)
        except StopIteration:
            return runs
        sent = Verdict(recorded=True) if isinstance(event, AlertRun) else None
        if isinstance(event, AlertRun):
            runs.append(event)


def texts(requests):
    return [text for request in requests for text in (request.system_prompt, request.user_prompt)]


def in_clear(strings):
    return [value for value in CLEAR for text in strings if value.lower() in text.lower()]


def test_a_day_run_sends_no_personal_value_and_one_placeholder_per_entity():
    provider = Recording()
    runs = day_runs(orchestrator(provider))
    assert len(runs) == 2
    assert in_clear(texts(provider.requests)) == []
    placeholders = {token for text in texts(provider.requests) for token in PLACEHOLDER.findall(text) if token.startswith("CLIENTE_")}
    assert len(placeholders) == 2


def test_the_name_a_row_carries_reaches_the_model_masked():
    provider = Recording()
    day_runs(orchestrator(provider))
    estratega = [request.user_prompt for request in provider.requests if "fila del KPI" in request.user_prompt]
    assert estratega and all("NOMBRE_" in prompt for prompt in estratega if "cupo_credito" in prompt and "nombre" in prompt)


def test_the_model_writes_a_placeholder_and_the_alert_stores_the_original():
    runs = day_runs(orchestrator(Recording()))
    titles = {run.detection.entity[0]: run.state["title"]["text"] for run in runs}
    assert titles == {"CLI-001": "Cartera vencida de CLI-001 por {0}", "CLI-002": "Cartera vencida de CLI-002 por {0}"}
    causes = [run.state["cause"]["sentence"]["text"] for run in runs]
    assert not any(PLACEHOLDER.search(text) for text in causes)


def test_the_state_keeps_the_masked_prompts_of_its_model_steps():
    for run in day_runs(orchestrator(Recording())):
        recorded = run.state["prompts"]
        assert {prompt["agent"] for prompt in recorded} >= {"vigia", "analista", "estratega"}
        assert in_clear([prompt["user"] for prompt in recorded] + [prompt["system"] for prompt in recorded]) == []


def test_an_approval_resumed_with_no_day_run_masks_the_ejecutor_prompt():
    provider = Recording()
    orq = orchestrator(provider)
    run = day_runs(orq)[0]
    action = run.state["actions"][0]
    assert action["parameters"]["recipient"] in ("CLI-001", "CLI-002")
    before = len(provider.requests)
    state = orq.resume(run.alert_id, approve(action["id"]))
    ejecutor = provider.requests[before:]
    assert ejecutor and in_clear(texts(ejecutor)) == []
    assert any(prompt["agent"] == "ejecutor" for prompt in state["prompts"])
    assert state["executed_action"]["result"].endswith(f"Le escribimos sobre la cuenta {action['parameters']['recipient']}.")


def test_a_typed_id_is_masked_before_the_model_and_chosen_back_from_the_rows():
    provider = Recording()
    reply = orchestrator(provider).ask("¿Cuánto debe cli-001?", DAY)
    assert in_clear(texts(provider.requests)) == []
    assert reply["chat"]["entity"] == "CLI-001"
    assert reply["prompts"] and in_clear([prompt["user"] for prompt in reply["prompts"]]) == []


def test_a_placeholder_no_row_holds_chooses_no_entity():
    reply = orchestrator(Recording(chat_entity="CLIENTE_QQQQQQ")).ask("¿Cuánto debe cli-001?", DAY)
    assert reply["chat"]["entity"] is None
