# The kernel's contract: exactly the four read-only tools, each a valid JSON Schema none of which
# takes SQL from a model, arguments out of contract refused by the lenguaje guard, and a refusal
# returned as data naming its guard instead of an exception the model never sees.
import pytest
from jsonschema import Draft202012Validator

from centinela_tools.kernel import CONTRACT, Kernel, answer, day_of
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of

from support import fixture_entries

SOURCES = load_sources()


def never(role):
    raise AssertionError("no connection")


def kernel():
    return Kernel(SOURCES, catalogue_of(fixture_entries(), SOURCES), Settings(), never)


def test_the_contract_holds_exactly_the_four_tools():
    assert {tool["name"] for tool in CONTRACT} == {"kpi_validar", "kpi_dry_run", "kpi_consultar", "kpi_catalogo"}


def test_every_input_schema_is_a_valid_json_schema():
    for tool in CONTRACT:
        Draft202012Validator.check_schema(tool["input_schema"])


def test_no_tool_takes_sql():
    for tool in CONTRACT:
        assert not {"sql", "consulta", "query"} & set(tool["input_schema"].get("properties", {})), tool["name"]


def test_arguments_out_of_contract_are_refused_by_the_language_guard():
    assert kernel().call("kpi_consultar", {"kpi": "oc_abiertas"})["rechazado"]["guarda"] == "lenguaje"
    assert kernel().call("kpi_validar", {"bloque": [], "dia": "2026-03-02"})["rechazado"]["guarda"] == "lenguaje"


def test_a_tool_outside_the_contract_is_an_error():
    with pytest.raises(ValueError):
        kernel().call("kpi_borrar", {})


def test_the_catalogue_is_answered_without_a_connection():
    assert {kpi["id"] for kpi in kernel().call("kpi_catalogo", {})["kpis"]} == set(catalogue_of(fixture_entries(), SOURCES).kpis)


def test_a_refusal_is_returned_as_data_with_its_guard():
    def refuse():
        raise Refused("hash", "tampered")

    assert answer(refuse) == {"rechazado": {"guarda": "hash", "detalle": "tampered"}}


def test_a_bad_day_is_refused_by_the_language_guard():
    assert answer(lambda: day_of("ayer"))["rechazado"]["guarda"] == "lenguaje"
    assert kernel().call("kpi_consultar", {"kpi": "oc_abiertas", "dia": "ayer"})["rechazado"]["guarda"] == "lenguaje"
