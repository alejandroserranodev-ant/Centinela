# The two inputs the kernel hands the tree: the catalogue, from kpi_catalogo, and the reader, from
# kpi_consultar. The reader raises on a refusal, so a refused reading never passes for a day with no
# rows and no alert.
import pytest

from centinela_agents.catalog import kernel_reader

from support import KERNEL_CATALOG


def test_the_catalogue_holds_each_kpis_entity_and_columns():
    kpi = KERNEL_CATALOG.kpis["saldo_vencido"]
    assert kpi.entity == ("cliente_id",) and not kpi.descriptive
    assert {"max_dias_vencido", "saldo_abierto", "cupo_credito", "pesos_en_riesgo"} <= kpi.columns


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
