# The two inputs the kernel hands the tree: the catalogue, from kpi_catalogo's answer as Kernel.call
# returns it, and the reader, from kpi_consultar. The reader raises on a refusal, so a refused reading never passes for a day with no
# rows and no alert.
import pytest

from centinela_agents.catalog import catalog_from_kernel, kernel_reader
from centinela_tools.kernel import Kernel
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, load_entries

from support import KERNEL_CATALOG, METRICAS


def test_the_catalogue_holds_each_kpis_entity_and_columns():
    kpi = KERNEL_CATALOG.kpis["saldo_vencido"]
    assert kpi.entity == ("cliente_id",) and not kpi.descriptive
    assert {"max_dias_vencido", "saldo_abierto", "cupo_credito", "pesos_en_riesgo"} <= kpi.columns



def test_the_catalogue_is_built_from_the_answer_kpi_catalogo_returns():
    sources = load_sources()
    kernel = Kernel(sources, catalogue_of(load_entries(METRICAS), sources), Settings(), connect=None)
    assert catalog_from_kernel(kernel.call("kpi_catalogo", {})) == KERNEL_CATALOG


def test_the_reader_returns_the_rows_kpi_consultar_returns():
    calls = []

    def call(name, arguments):
        calls.append((name, dict(arguments)))
        return {"kpi": "saldo_vencido", "dia": "2026-03-02", "consulta": "SELECT 1", "filas": [{"cliente_id": "CLI-001"}]}

    assert kernel_reader(call)("saldo_vencido", "2026-03-02") == [{"cliente_id": "CLI-001"}]
    assert calls == [("kpi_consultar", {"kpi": "saldo_vencido", "dia": "2026-03-02"})]


def test_a_refusal_of_the_kernel_raises_instead_of_reading_as_no_rows():
    read = kernel_reader(lambda name, arguments: {"rechazado": {"guarda": "catalogo", "detalle": "x is no KPI of this client's catalogue"}})
    with pytest.raises(RuntimeError, match="catalogo"):
        read("x", "2026-03-02")
