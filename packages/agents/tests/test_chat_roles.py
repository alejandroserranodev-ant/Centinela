# The role of the signed-in person changes how the chat writes and what it shows, never a fact.
import pytest

from centinela_agents.agents.chat import READ_ONLY, ROLES, SENTENCES, Facts, closing, written
from centinela_agents.skills import skill

FIGURE = {"value": 1, "unit": "COP", "queryId": "q1"}


@pytest.mark.parametrize("role", ROLES)
def test_each_role_has_a_skill_that_loads_after_the_contract(role):
    text = skill("chat", "contrato", f"rol_{role}")
    assert text.startswith("# Chat: the contract")
    assert f"# Role: {role}" in text


def test_the_manager_reads_at_most_two_sentences():
    facts = Facts()
    ref = facts.figure(FIGURE, "pesos en riesgo")
    parsed = {"sentences": [{"text": f"Riesgo {{0}} {n}", "figures": [ref]} for n in "abc"]}
    texts, _ = written(parsed, facts, ("a", "b", "c"), SENTENCES["gerente"])
    assert len(texts) == 2


def test_the_auditor_who_asks_to_act_is_told_it_only_consults():
    state = {"fin": "fin.chat_fuera_de_alcance", "role": "auditor", "chat": {"intent": "accion"}}
    assert closing(state)["text"] == READ_ONLY
    assert closing({**state, "role": "gerente"})["text"] != READ_ONLY
