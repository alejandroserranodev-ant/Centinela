# The generator of data/sql/05_kpis.generated.sql: the committed file is exactly what it writes from
# the tree, so a hand edit fails here; the roles, the column grants and a function are written as
# the kernel's page says; and a KPI over the planner's cap is refused by the guard costo.
import pytest

from centinela_tools.generate import render, view_names
from centinela_tools.paths import GENERATED, METRICAS, SQL_DIR
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import load_entries

from support import fixture_entries

SOURCES = load_sources()


def no_database(query):
    raise AssertionError("no entry of data/metricas.yaml carries kernel:, so no cost is estimated")


def test_the_committed_file_is_what_the_generator_writes():
    assert GENERATED.read_text() == render(SOURCES, load_entries(METRICAS), view_names(SQL_DIR), no_database, Settings())


def test_the_view_names_come_from_both_view_files():
    names = view_names(SQL_DIR)
    assert "v_ventas" in names and "v_costo_sku" in names and len(names) == len(set(names))


def test_the_file_opens_with_its_banner_and_grants_column_by_column():
    text = render(SOURCES, {}, view_names(SQL_DIR), no_database, Settings())
    assert text.startswith("-- Written by `uv run python -m centinela_tools.generate`")
    assert 'GRANT SELECT ("vendedor_id", "region") ON "centinela"."vendedores" TO centinela_kernel;' in text
    assert 'GRANT SELECT ON "centinela"."v_ventas" TO centinela_lector;' in text
    assert "ALTER FUNCTION centinela.fecha_corte() SECURITY DEFINER" in text
    assert "CREATE OR REPLACE FUNCTION" not in text


def test_a_fixture_kpi_becomes_a_function():
    text = render(SOURCES, fixture_entries(), view_names(SQL_DIR), lambda query: 1.0, Settings())
    assert text.count("CREATE OR REPLACE FUNCTION") == 3


def test_a_kpi_over_the_cost_cap_is_refused():
    with pytest.raises(Refused) as refused:
        render(SOURCES, fixture_entries(), view_names(SQL_DIR), lambda query: 2.0, Settings(max_cost=1.0))
    assert refused.value.guard == "costo"


def test_the_settings_read_the_environment():
    settings = Settings.from_env({"CENTINELA_KERNEL_COSTO_MAX": "10", "CENTINELA_KERNEL_TIMEOUT_MS": "20", "CENTINELA_KERNEL_GRUPOS_MAX": "30", "CENTINELA_KERNEL_MUESTRA": "4"})
    assert settings == Settings(10.0, 20, 30, 4)
