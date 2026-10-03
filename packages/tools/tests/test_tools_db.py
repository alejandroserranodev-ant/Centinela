# The tools against the scratch database: each fixture KPI agrees with a hand-written as-of query on
# several simulated days, facturas_abiertas agrees with the kit's v_cartera_cliente on fecha_corte(),
# and each guard that needs a database (costo, tiempo, cardinalidad, the read-only transaction) holds.
from datetime import date

import psycopg
import pytest

from centinela_tools.compiler import compile_kpi, digest, freeze
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_consultar, kpi_dry_run, kpi_validar

from support import fixture_block, fixture_entries

pytestmark = pytest.mark.db
SOURCES = load_sources()
CATALOGUE = catalogue_of(fixture_entries(), SOURCES)
DAYS = [date(2025, 12, 15), date(2026, 3, 2), date(2026, 9, 30)]


def rows(superuser, query, params):
    return {row[0]: float(row[1]) for row in superuser.execute(query, params).fetchall()}


def kernel_rows(connect, kpi_id, day, column):
    answer = kpi_consultar(kpi_id, day, CATALOGUE, connect, Settings())
    return {list(row.values())[0]: float(row[column]) for row in answer["filas"]}


@pytest.mark.parametrize("day", DAYS)
def test_open_orders_agree_with_an_as_of_query(connect, superuser, day):
    expected = rows(superuser, "SELECT proveedor_id, count(*) FROM centinela.ordenes_compra WHERE fecha_oc <= %(d)s AND (fecha_recibida IS NULL OR fecha_recibida > %(d)s) GROUP BY 1", {"d": day})
    assert kernel_rows(connect, "oc_abiertas", day, "ordenes_abiertas") == expected


@pytest.mark.parametrize("day", DAYS)
def test_open_invoices_agree_with_an_as_of_query(connect, superuser, day):
    query = (
        "SELECT f.cliente_id, sum(f.valor_total) FROM centinela.facturas f WHERE f.fecha_factura <= %(d)s "
        "AND coalesce((SELECT min(p.fecha_pago) FROM centinela.pagos p WHERE p.factura_id = f.factura_id), 'infinity') > %(d)s GROUP BY 1"
    )
    assert kernel_rows(connect, "facturas_abiertas", day, "saldo_abierto") == pytest.approx(rows(superuser, query, {"d": day}))


def test_open_invoices_agree_with_the_kits_view_on_fecha_corte(connect, superuser):
    cut = superuser.execute("SELECT centinela.fecha_corte()").fetchone()[0]
    view = rows(superuser, "SELECT cliente_id, saldo_abierto FROM centinela.v_cartera_cliente WHERE saldo_abierto > 0", {})
    assert kernel_rows(connect, "facturas_abiertas", cut, "saldo_abierto") == pytest.approx(view)


@pytest.mark.parametrize("day, week", [(date(2026, 2, 28), date(2026, 2, 16)), (date(2026, 3, 1), date(2026, 2, 23)), (date(2026, 3, 4), date(2026, 2, 23))])
def test_a_weekly_baseline_measures_the_last_complete_week(connect, superuser, day, week):
    query = (
        "WITH w AS (SELECT date_trunc('week', p.fecha)::date AS s, pr.linea, sum(d.valor_neto) AS v FROM centinela.pedidos p "
        "JOIN centinela.pedidos_detalle d USING (pedido_id) JOIN centinela.productos pr USING (sku) "
        "WHERE p.estado <> 'Cancelado' AND p.fecha >= %(w)s::date - 56 AND p.fecha < %(w)s::date + 7 GROUP BY 1, 2) "
        "SELECT linea, coalesce(sum(v) FILTER (WHERE s = %(w)s), 0), coalesce(sum(v) FILTER (WHERE s < %(w)s), 0) / 8.0 FROM w GROUP BY linea"
    )
    expected = {row[0]: (float(row[1]), float(row[2])) for row in superuser.execute(query, {"w": week}).fetchall()}
    answer = kpi_consultar("ventas_semana_linea", day, CATALOGUE, connect, Settings())
    got = {row["linea"]: (row["ventas"], row["ventas_base"]) for row in answer["filas"]}
    assert expected and got.keys() == expected.keys()
    assert got == pytest.approx(expected)


def test_a_day_before_the_dataset_returns_no_rows(connect):
    for kpi_id in ("oc_abiertas", "facturas_abiertas", "ventas_semana_linea"):
        assert kpi_consultar(kpi_id, date(2025, 9, 1), CATALOGUE, connect, Settings())["filas"] == []


def test_a_dry_run_returns_a_sample_the_count_and_the_time(connect):
    answer = kpi_dry_run(fixture_block("oc_abiertas"), date(2026, 3, 2), SOURCES, connect, Settings(sample_rows=2))
    assert len(answer["filas"]) <= 2 and answer["total_filas"] >= len(answer["filas"]) and answer["ms"] >= 0
    assert answer["hash"] and "%(dia)s" in answer["sql"]


@pytest.mark.parametrize("kpi_id", ["oc_abiertas", "facturas_abiertas", "ventas_semana_linea"])
def test_every_fixture_kpi_fits_the_default_cost_cap(connect, kpi_id):
    assert kpi_validar(fixture_block(kpi_id), date(2026, 3, 2), SOURCES, connect, Settings())["costo"] <= Settings().max_cost


def test_the_cost_guard_refuses_over_its_cap(connect):
    with pytest.raises(Refused) as refused:
        kpi_validar(fixture_block("ventas_semana_linea"), date(2026, 3, 2), SOURCES, connect, Settings(max_cost=1.0))
    assert refused.value.guard == "costo"


def test_the_time_guard_refuses_past_its_timeout(connect):
    with pytest.raises(Refused) as refused:
        kpi_dry_run(fixture_block("ventas_semana_linea"), date(2026, 3, 2), SOURCES, connect, Settings(timeout_ms=1))
    assert refused.value.guard == "tiempo"


def test_the_cardinality_guard_refuses_too_many_groups(connect):
    with pytest.raises(Refused) as refused:
        kpi_dry_run(fixture_block("oc_abiertas"), date(2026, 3, 2), SOURCES, connect, Settings(max_groups=1))
    assert refused.value.guard == "cardinalidad"


def test_a_literal_with_sql_in_it_stays_a_literal(connect, superuser):
    block = fixture_block("oc_abiertas")
    block["filtro"] = [{"columna": "ordenes_compra.sku", "op": "=", "valor": "x'); DROP TABLE centinela.pagos; --"}]
    assert kpi_dry_run(block, date(2026, 3, 2), SOURCES, connect, Settings())["total_filas"] == 0
    assert superuser.execute("SELECT count(*) FROM centinela.pagos").fetchone()[0] > 0


def test_an_approved_kpi_runs_its_stored_text_as_the_kernel_role(connect):
    frozen = freeze(compile_kpi(fixture_block("oc_abiertas"), SOURCES))
    record = {"id": "aprobado_oc", "sql": frozen.sql, "hash": frozen.hash, "version_compilador": "1", "ficha": {}, "descriptivo": True, "entidad": ["proveedor_id"], "columnas": []}
    answer = kpi_consultar("aprobado_oc", date(2026, 3, 2), catalogue_of({}, SOURCES, [record]), connect, Settings())
    assert answer["consulta"] == frozen.sql and answer["filas"]


def test_an_approved_kpi_that_writes_fails_and_changes_nothing(connect, superuser):
    text = "DELETE FROM centinela.pedidos WHERE fecha <= %(dia)s"
    record = {"id": "malicioso", "sql": text, "hash": digest(text), "version_compilador": "1", "ficha": {}, "descriptivo": True, "entidad": [], "columnas": []}
    before = superuser.execute("SELECT count(*) FROM centinela.pedidos").fetchone()[0]
    with pytest.raises(psycopg.Error):
        kpi_consultar("malicioso", date(2026, 3, 2), catalogue_of({}, SOURCES, [record]), connect, Settings())
    assert superuser.execute("SELECT count(*) FROM centinela.pedidos").fetchone()[0] == before
