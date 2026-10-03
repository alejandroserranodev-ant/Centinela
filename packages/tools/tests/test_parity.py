# Parity of every base KPI of data/metricas.yaml, in two halves. On fecha_corte() the kit's views are
# right by definition, so each KPI returns its view's rows, value for value, on the columns the view
# holds. On earlier simulated days the views leak, so each KPI agrees with a hand-written as-of query
# here, never with the view. Each test is one KER- case of evals/AGENTS.md. margen_pct and
# dias_pago_prom are compared on the entities measured in the current period, because no view or
# as-of query holds a row for a week or a month with no sale or payment. descuento_en_exceso agrees
# with its view within half a peso per line, because the kit rounds each line and the kernel rounds
# the week's sum. dias_pago_prom has no view half: it measures by month of payment, and its view by
# month of invoice, whose last months hold only the invoices already paid.
from datetime import date
from decimal import Decimal

import pytest
from psycopg import sql
from psycopg.rows import dict_row

from centinela_tools.compiler import BUSINESS_DAYS
from centinela_tools.paths import METRICAS
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_consultar, load_entries, plain

pytestmark = pytest.mark.db
ENTRIES = load_entries(METRICAS)
CATALOGUE = catalogue_of(ENTRIES, load_sources())
DAYS = [date(2025, 12, 15), date(2026, 4, 8), date(2026, 9, 15)]
WEEK = "date_trunc('week', %(d)s::date - 6)::date"
MONTH = "(date_trunc('month', %(d)s::date + 1) - interval '1 month')::date"
OPEN = "f.fecha_factura <= %(d)s AND NOT EXISTS (SELECT 1 FROM centinela.pagos pg WHERE pg.factura_id = f.factura_id AND pg.fecha_pago <= %(d)s)"
SOLD = "FROM centinela.pedidos_detalle dd JOIN centinela.pedidos p USING (pedido_id) WHERE p.estado <> 'Cancelado' AND p.fecha <= %(d)s"

VIEWS = {
    "margen_pct": f"SELECT linea, margen_pct, ventas FROM centinela.v_margen_semanal_linea WHERE semana = {WEEK}",
    "saldo_vencido": "SELECT cliente_id, saldo_vencido, saldo_abierto, max_dias_vencido, cupo_credito FROM centinela.v_cartera_cliente WHERE saldo_abierto > 0",
    "concentracion_vencida_pct": (
        "SELECT cliente_id, saldo_vencido, round(100 * saldo_vencido / sum(saldo_vencido) OVER (), 2) AS concentracion_vencida_pct "
        "FROM centinela.v_cartera_cliente WHERE saldo_abierto > 0"
    ),
    "cobertura_dias": "SELECT sku, bodega_id, demanda_prom_30d, existencia, clase_abc, cobertura_dias FROM centinela.v_cobertura_inventario",
    "variacion_costo_pct": "SELECT sku, costo_unitario, costo_anterior, fecha_vigencia, variacion_pct FROM centinela.v_costo_sku WHERE vigente",
    "dias_retraso": "SELECT oc_id, fecha_recibida, fecha_esperada, recibida, dias_retraso FROM centinela.v_ordenes_compra",
    "margen_bruto_negativo": "SELECT pedido_id, linea_n, margen_bruto, sku, fecha FROM centinela.v_ventas WHERE margen_bruto < 0",
    "veces_intervalo_habitual": "SELECT cliente_id, pedidos, ultima_compra, intervalo_prom_dias, dias_sin_comprar, veces_intervalo_habitual FROM centinela.v_actividad_cliente",
}

AS_OF = {
    "margen_pct": (
        "WITH semanas AS (SELECT pr.linea, date_trunc('week', p.fecha)::date AS semana, "
        "100 * sum(dd.valor_neto - dd.cantidad * dd.costo_unitario) / nullif(sum(dd.valor_neto), 0) AS margen, sum(dd.valor_neto) AS ventas "
        f"{SOLD.replace('USING (pedido_id)', 'USING (pedido_id) JOIN centinela.productos pr USING (sku)')} "
        f"AND p.fecha >= {WEEK} - 56 AND p.fecha < {WEEK} + 7 GROUP BY 1, 2), "
        f"actual AS (SELECT linea, margen, ventas FROM semanas WHERE semana = {WEEK}), "
        f"previa AS (SELECT linea, avg(margen) AS base FROM semanas WHERE semana < {WEEK} GROUP BY 1), "
        "trimestre AS (SELECT pr.linea, sum(dd.valor_neto) / 3 AS mes "
        f"{SOLD.replace('USING (pedido_id)', 'USING (pedido_id) JOIN centinela.productos pr USING (sku)')} AND p.fecha > %(d)s::date - 90 GROUP BY 1) "
        "SELECT a.linea, round(a.margen, 2) AS margen_pct, round(b.base, 2) AS margen_pct_base, round(b.base - a.margen, 2) AS caida_pts, "
        "a.ventas, m.margen_minimo_pct, round(t.mes, 0) AS ventas_mes_prom, "
        "round((greatest(b.base, m.margen_minimo_pct) - a.margen) / 100 * a.ventas, 0) AS pesos_en_riesgo "
        "FROM actual a LEFT JOIN previa b USING (linea) JOIN centinela.ref_margen_minimo_linea m USING (linea) LEFT JOIN trimestre t USING (linea)"
    ),
    "saldo_vencido": (
        "SELECT f.cliente_id, coalesce(sum(f.valor_total) FILTER (WHERE f.fecha_vencimiento < %(d)s), 0) AS saldo_vencido, "
        "sum(f.valor_total) AS saldo_abierto, max(%(d)s::date - f.fecha_vencimiento) AS max_dias_vencido, max(c.cupo_credito) AS cupo_credito, "
        "coalesce(sum(f.valor_total) FILTER (WHERE f.fecha_vencimiento < %(d)s), 0) AS pesos_en_riesgo "
        f"FROM centinela.facturas f JOIN centinela.clientes c USING (cliente_id) WHERE {OPEN} GROUP BY 1"
    ),
    "concentracion_vencida_pct": (
        "WITH s AS (SELECT f.cliente_id, coalesce(sum(f.valor_total) FILTER (WHERE f.fecha_vencimiento < %(d)s), 0) AS v "
        f"FROM centinela.facturas f WHERE {OPEN} GROUP BY 1) "
        "SELECT cliente_id, v AS saldo_vencido, round(100 * v / nullif(sum(v) OVER (), 0), 2) AS concentracion_vencida_pct, v AS pesos_en_riesgo FROM s"
    ),
    "dias_pago_prom": (
        "WITH meses AS (SELECT f.cliente_id, date_trunc('month', pg.fecha_pago)::date AS mes, avg(pg.fecha_pago - f.fecha_factura) AS dias "
        "FROM centinela.pagos pg JOIN centinela.facturas f USING (factura_id) "
        f"WHERE f.fecha_factura <= %(d)s AND pg.fecha_pago >= ({MONTH} - interval '12 months')::date AND pg.fecha_pago < ({MONTH} + interval '1 month')::date GROUP BY 1, 2), "
        f"actual AS (SELECT cliente_id, dias FROM meses WHERE mes = {MONTH}), "
        f"previa AS (SELECT cliente_id, avg(dias) AS base FROM meses WHERE mes < {MONTH} GROUP BY 1), "
        f"cartera AS (SELECT f.cliente_id, sum(f.valor_total) AS saldo FROM centinela.facturas f WHERE {OPEN} GROUP BY 1) "
        "SELECT a.cliente_id, round(a.dias, 1) AS dias_pago_prom, round(b.base, 1) AS dias_pago_prom_base, "
        "round(100 * (a.dias / nullif(b.base, 0) - 1), 2) AS aumento_pct, c.saldo AS pesos_en_riesgo "
        "FROM actual a LEFT JOIN previa b USING (cliente_id) LEFT JOIN cartera c USING (cliente_id)"
    ),
    "cobertura_dias": (
        "WITH inv AS (SELECT sku, bodega_id, avg(salidas) AS dem, (array_agg(existencia_final ORDER BY fecha DESC))[1] AS ex "
        "FROM centinela.inventario_diario WHERE fecha > %(d)s::date - 30 AND fecha <= %(d)s GROUP BY 1, 2), "
        "precio AS (SELECT DISTINCT ON (sku) sku, precio_lista FROM centinela.lista_precios WHERE fecha_vigencia <= %(d)s ORDER BY sku, fecha_vigencia DESC), "
        "pend AS (SELECT dd.sku, count(*) AS n FROM centinela.pedidos_detalle dd JOIN centinela.pedidos p USING (pedido_id) "
        "WHERE p.estado <> 'Cancelado' AND p.fecha <= %(d)s AND NOT EXISTS "
        "(SELECT 1 FROM centinela.facturas f WHERE f.pedido_id = p.pedido_id AND f.fecha_factura <= %(d)s) GROUP BY 1) "
        "SELECT inv.sku, inv.bodega_id, round(inv.dem, 1) AS demanda_prom_30d, inv.ex AS existencia, pr.clase_abc, precio.precio_lista, "
        "round(inv.ex / nullif(inv.dem, 0), 1) AS cobertura_dias, coalesce(pend.n, 0) AS pedidos_pendientes, "
        "round(inv.dem * (CASE pr.clase_abc WHEN 'A' THEN %(a)s WHEN 'B' THEN %(b)s END - inv.ex / nullif(inv.dem, 0)) * precio.precio_lista, 0) AS pesos_en_riesgo "
        "FROM inv JOIN centinela.productos pr USING (sku) LEFT JOIN precio USING (sku) LEFT JOIN pend USING (sku)"
    ),
    "variacion_costo_pct": (
        "WITH c AS (SELECT sku, (array_agg(costo_unitario ORDER BY fecha_vigencia DESC))[1] AS cu, "
        "(array_agg(costo_unitario ORDER BY fecha_vigencia DESC))[2] AS ca, max(fecha_vigencia) AS fv "
        "FROM centinela.costos_proveedor WHERE fecha_vigencia <= %(d)s GROUP BY 1), "
        "lp AS (SELECT sku, max(fecha_vigencia) AS cambio, (array_agg(precio_lista ORDER BY fecha_vigencia DESC))[1] AS precio "
        "FROM centinela.lista_precios WHERE fecha_vigencia <= %(d)s GROUP BY 1), "
        "v AS (SELECT dd.sku, coalesce(sum(dd.cantidad) FILTER (WHERE p.fecha >= c.fv), 0) AS desde, "
        "coalesce(sum(dd.cantidad) FILTER (WHERE p.fecha > %(d)s::date - 90), 0) AS n90 "
        f"{SOLD.replace('USING (pedido_id)', 'USING (pedido_id) LEFT JOIN c USING (sku)')} GROUP BY 1), "
        "habiles AS (SELECT c.sku, count(g.dia) FILTER (WHERE extract(isodow FROM g.dia) BETWEEN 1 AND 5) AS n "
        "FROM c LEFT JOIN LATERAL generate_series(c.fv + 1, %(d)s::date, interval '1 day') AS g(dia) ON TRUE GROUP BY 1) "
        "SELECT c.sku, c.cu AS costo_unitario, c.ca AS costo_anterior, c.fv AS fecha_vigencia, lp.precio AS precio_lista, "
        "round(100 * (c.cu / nullif(c.ca, 0) - 1), 2) AS variacion_pct, "
        "CASE WHEN lp.cambio >= c.fv THEN 0 ELSE h.n END AS dias_habiles_sin_traslado, "
        "round((c.cu - c.ca) * v.desde, 0) AS pesos_en_riesgo, round(v.n90 / 3.0, 1) AS unidades_mes_prom "
        "FROM c LEFT JOIN lp USING (sku) LEFT JOIN v USING (sku) JOIN habiles h USING (sku)"
    ),
    "dias_retraso": (
        "SELECT oc_id, CASE WHEN fecha_recibida <= %(d)s THEN fecha_recibida END AS fecha_recibida, fecha_esperada, "
        "coalesce(fecha_recibida <= %(d)s, false) AS recibida, "
        "CASE WHEN fecha_recibida <= %(d)s THEN greatest(fecha_recibida - fecha_esperada, 0) ELSE greatest(%(d)s::date - fecha_esperada, 0) END AS dias_retraso, "
        "cantidad * costo_unitario AS pesos_en_riesgo FROM centinela.ordenes_compra WHERE fecha_oc <= %(d)s"
    ),
    "descuento_en_exceso": (
        "WITH s AS (SELECT p.vendedor_id, date_trunc('week', p.fecha)::date AS semana, "
        "sum(dd.cantidad * dd.precio_unitario * (dd.descuento_pct - t.tope_descuento_pct) / 100) AS e "
        "FROM centinela.pedidos_detalle dd JOIN centinela.pedidos p USING (pedido_id) JOIN centinela.clientes c ON c.cliente_id = p.cliente_id "
        "JOIN centinela.ref_topes_descuento t ON t.segmento = c.segmento "
        "WHERE p.estado <> 'Cancelado' AND p.fecha <= %(d)s AND dd.aprobacion_especial = 'N' AND dd.descuento_pct > t.tope_descuento_pct GROUP BY 1, 2) "
        "SELECT a.vendedor_id, a.semana, round(a.e, 0) AS descuento_en_exceso, round(b.e, 0) AS exceso_semana_anterior, round(a.e, 0) AS pesos_en_riesgo "
        "FROM s a LEFT JOIN s b ON b.vendedor_id = a.vendedor_id AND b.semana = a.semana - 7"
    ),
    "margen_bruto_negativo": (
        "SELECT dd.pedido_id, dd.linea_n, dd.valor_neto - dd.cantidad * dd.costo_unitario AS margen_bruto, dd.sku, p.fecha, "
        f"dd.cantidad * dd.costo_unitario - dd.valor_neto AS pesos_en_riesgo {SOLD} AND dd.valor_neto - dd.cantidad * dd.costo_unitario < 0"
    ),
    "veces_intervalo_habitual": (
        "WITH c AS (SELECT cliente_id, count(*) AS n, max(fecha) AS u, min(fecha) AS f FROM centinela.pedidos "
        "WHERE estado <> 'Cancelado' AND fecha <= %(d)s GROUP BY 1), "
        "s AS (SELECT p.cliente_id, coalesce(sum(dd.valor_neto) FILTER (WHERE p.fecha > (c.u - interval '6 months')::date), 0) / 6 AS mes "
        f"{SOLD.replace('USING (pedido_id)', 'USING (pedido_id) JOIN c ON c.cliente_id = p.cliente_id')} GROUP BY 1) "
        "SELECT c.cliente_id, c.n AS pedidos, c.u AS ultima_compra, round((c.u - c.f)::numeric / nullif(c.n - 1, 0), 1) AS intervalo_prom_dias, "
        "%(d)s::date - c.u AS dias_sin_comprar, round((%(d)s::date - c.u) / nullif((c.u - c.f)::numeric / nullif(c.n - 1, 0), 0), 1) AS veces_intervalo_habitual, "
        "round(s.mes, 0) AS pesos_en_riesgo FROM c LEFT JOIN s USING (cliente_id)"
    ),
}

MEASURED = {"margen_pct": "margen_pct", "dias_pago_prom": "dias_pago_prom"}


def parameters(day):
    classes = ENTRIES["cobertura_dias"]["umbrales"]["cobertura_dias"]["valores"]
    return {"d": day, "a": classes["A"], "b": classes["B"]}


def expected(superuser, query, day, entity):
    with superuser.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, parameters(day))
        rows = [plain(row) for row in cursor.fetchall()]
    return {tuple(row[name] for name in entity): row for row in rows}


def measured(connect, metric, day):
    entity = CATALOGUE.kpis[metric].entity
    rows = kpi_consultar(metric, day, CATALOGUE, connect, Settings())["filas"]
    column = MEASURED.get(metric)
    return {tuple(row[name] for name in entity): row for row in rows if column is None or row[column] is not None}, entity


def close(left, right, tolerance):
    if isinstance(left, (int, float, Decimal)) and isinstance(right, (int, float, Decimal)) and not isinstance(left, bool):
        return abs(float(left) - float(right)) <= tolerance
    return left == right


def agree(kernel, reference, tolerance=1e-9):
    assert set(kernel) == set(reference), sorted(set(kernel) ^ set(reference))[:5]
    for key, row in reference.items():
        for column, value in row.items():
            assert close(kernel[key][column], value, tolerance), (key, column, kernel[key][column], value)


def cut(superuser):
    return superuser.execute("SELECT centinela.fecha_corte()").fetchone()[0]


def test_every_metric_of_metricas_yaml_is_a_base_kpi():
    assert set(CATALOGUE.kpis) == set(ENTRIES)
    assert set(AS_OF) == set(ENTRIES) and set(VIEWS) | {"descuento_en_exceso", "dias_pago_prom"} == set(ENTRIES)


@pytest.mark.parametrize("metric", sorted(VIEWS))
def test_a_kpi_returns_its_views_rows_on_fecha_corte(connect, superuser, metric):
    day = cut(superuser)
    kernel, entity = measured(connect, metric, day)
    agree(kernel, expected(superuser, VIEWS[metric], day, entity))


def test_descuento_en_exceso_agrees_with_its_view_within_half_a_peso_per_line(connect, superuser):
    day = cut(superuser)
    kernel, entity = measured(connect, "descuento_en_exceso", day)
    view = expected(
        superuser,
        "SELECT vendedor_id, date_trunc('week', fecha)::date AS semana, sum(descuento_en_exceso) AS descuento_en_exceso, count(*) AS lineas "
        "FROM centinela.v_descuentos_fuera_politica GROUP BY 1, 2",
        day,
        entity,
    )
    assert set(kernel) == set(view)
    for key, row in view.items():
        assert close(kernel[key]["descuento_en_exceso"], row["descuento_en_exceso"], 0.5 * row["lineas"]), key


@pytest.mark.parametrize("day", DAYS, ids=str)
@pytest.mark.parametrize("metric", sorted(AS_OF))
def test_a_kpi_agrees_with_an_as_of_query_on_an_earlier_day(connect, superuser, metric, day):
    kernel, entity = measured(connect, metric, day)
    agree(kernel, expected(superuser, AS_OF[metric], day, entity))


@pytest.mark.parametrize("metric", sorted(AS_OF))
def test_every_kpi_returns_rows_on_some_as_of_day(connect, metric):
    assert any(measured(connect, metric, day)[0] for day in DAYS), f"{metric} returns no row on {DAYS}, so its as-of check proves nothing"


@pytest.mark.parametrize("metric", sorted(ENTRIES))
def test_every_base_kpi_outputs_pesos_en_riesgo(metric):
    assert "pesos_en_riesgo" in dict(CATALOGUE.kpis[metric].columns)


def test_cobertura_dias_outputs_the_orders_pending_on_the_day():
    assert dict(CATALOGUE.kpis["cobertura_dias"].columns)["pedidos_pendientes"] in ("bigint", "integer")


@pytest.mark.parametrize("metric", sorted(ENTRIES))
def test_a_day_before_the_dataset_returns_no_rows(connect, metric):
    assert kpi_consultar(metric, date(2025, 9, 30), CATALOGUE, connect, Settings())["filas"] == []


def test_a_customer_with_one_order_has_no_interval_and_raises_nothing(connect):
    rows = kpi_consultar("veces_intervalo_habitual", date(2025, 10, 2), CATALOGUE, connect, Settings())["filas"]
    single = [row for row in rows if row["pedidos"] == 1]
    assert single and all(row["intervalo_prom_dias"] is None and row["veces_intervalo_habitual"] is None for row in single)


@pytest.mark.parametrize(
    "start, end, days",
    [(date(2026, 2, 13), date(2026, 2, 27), 10), (date(2026, 2, 13), date(2026, 3, 2), 11), (date(2026, 2, 13), date(2026, 2, 13), 0), (date(2026, 2, 14), date(2026, 2, 15), 0)],
)
def test_business_days_count_monday_to_friday_after_the_start(superuser, start, end, days):
    assert superuser.execute(sql.SQL("SELECT {}").format(BUSINESS_DAYS.format(sql.Literal(start), sql.Literal(end)))).fetchone()[0] == days
