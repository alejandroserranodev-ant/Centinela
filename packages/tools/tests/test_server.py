# The kernel's MCP server: exactly the four read-only tools, none of which takes SQL from a model,
# and a refusal returned as data naming its guard instead of an exception the model never sees.
import asyncio

from centinela_tools.server import answer, build_server, day_of
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of

from support import fixture_entries

SOURCES = load_sources()


def never(role):
    raise AssertionError("no connection")


def server():
    return build_server(SOURCES, catalogue_of(fixture_entries(), SOURCES), Settings(), never)


def test_the_server_exposes_exactly_the_four_tools():
    tools = asyncio.run(server().list_tools())
    assert {tool.name for tool in tools} == {"kpi_validar", "kpi_dry_run", "kpi_consultar", "kpi_catalogo"}


def test_no_tool_takes_sql():
    for tool in asyncio.run(server().list_tools()):
        assert not {"sql", "consulta", "query"} & set(tool.input_schema.get("properties", {})), tool.name


def test_a_refusal_is_returned_as_data_with_its_guard():
    def refuse():
        raise Refused("hash", "tampered")

    assert answer(refuse) == {"rechazado": {"guarda": "hash", "detalle": "tampered"}}


def test_a_bad_day_is_refused_by_the_language_guard():
    assert answer(lambda: day_of("ayer"))["rechazado"]["guarda"] == "lenguaje"
