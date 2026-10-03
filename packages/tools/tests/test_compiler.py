# The compiler with no database: every refusal of the guards fuente, reloj and lenguaje that needs
# fuentes.yaml, the clock written into the SQL by construction, and two checks over the package's
# source: every SQL fragment is a constant, and no query is built from a formatted string.
import ast
from pathlib import Path

import pytest
from psycopg import sql

import centinela_tools
from centinela_tools.compiler import compile_kpi, digest, freeze, function_definition
from centinela_tools.refusal import Refused
from centinela_tools.sources import load_sources

from support import fixture_block

SOURCES = load_sources()
PACKAGE = Path(centinela_tools.__file__).parent


def text(block):
    return compile_kpi(block, SOURCES).query.as_string()


def refused(block):
    with pytest.raises(Refused) as caught:
        compile_kpi(block, SOURCES)
    return caught.value


def changed(metric, change):
    block = fixture_block(metric)
    change(block)
    return block


@pytest.mark.parametrize("metric", ["oc_abiertas", "facturas_abiertas", "ventas_semana_linea"])
def test_every_fixture_compiles_to_a_composition(metric):
    compiled = compile_kpi(fixture_block(metric), SOURCES)
    assert isinstance(compiled.query, sql.Composable)
    assert compiled.entity == tuple(name for name, _ in compiled.columns[: len(compiled.entity)])


def test_the_entity_is_agrupar_and_the_columns_carry_types():
    compiled = compile_kpi(fixture_block("ventas_semana_linea"), SOURCES)
    assert compiled.entity == ("linea",)
    assert compiled.columns == (("linea", "text"), ("ventas", "numeric"), ("ventas_base", "numeric"), ("ventas_delta_pct", "numeric"))


def test_an_open_row_reads_a_closing_date_only_up_to_dia():
    assert '("ordenes_compra"."fecha_recibida" IS NULL OR "ordenes_compra"."fecha_recibida" > CAST(%(dia)s AS date))' in text(fixture_block("oc_abiertas"))


def test_a_payment_closes_an_invoice_only_up_to_dia():
    expected = 'NOT EXISTS (SELECT 1 FROM "centinela"."pagos" AS "pagada" WHERE "pagada"."factura_id" = "facturas"."factura_id" AND "pagada"."fecha_pago" <= CAST(%(dia)s AS date))'
    assert expected in text(fixture_block("facturas_abiertas"))


def test_every_event_date_reached_is_bounded_by_dia():
    query = text(fixture_block("ventas_semana_linea"))
    assert '"pedidos"."fecha" <= CAST(%(dia)s AS date)' in query
    assert '"facturas"."fecha_factura" <= CAST(%(dia)s AS date)' in text(fixture_block("facturas_abiertas"))


def test_a_weekly_baseline_uses_only_complete_weeks():
    query = text(fixture_block("ventas_semana_linea"))
    assert "date_trunc('week', CAST(%(dia)s AS date) - 6)::date" in query
    assert '"pedidos"."fecha" < (' in query


def test_a_monthly_baseline_uses_only_complete_months():
    query = text(changed("ventas_semana_linea", lambda b: b["linea_base"].update(periodo="mes")))
    assert "(date_trunc('month', CAST(%(dia)s AS date) + 1) - interval '1 month')::date" in query


def test_a_baseline_reads_every_period_of_its_window_for_every_entity():
    query = text(fixture_block("ventas_semana_linea"))
    assert "SELECT DISTINCT \"linea\" FROM periodos" in query
    assert "generate_series((date_trunc('week', CAST(%(dia)s AS date) - 6)::date - 7 * 8), date_trunc('week', CAST(%(dia)s AS date) - 6)::date, interval '1 week')" in query
    assert "interval '1 week')::date AS periodo) AS serie" in query
    assert 'FROM entidades CROSS JOIN (SELECT generate_series(' in query
    assert 'LEFT JOIN periodos ON "periodos"."linea" IS NOT DISTINCT FROM "entidades"."linea" AND periodos.periodo = serie.periodo' in query
    assert "(SELECT periodos.valor" not in query


def test_an_empty_period_of_a_sum_counts_as_zero():
    query = text(fixture_block("ventas_semana_linea"))
    assert "coalesce(periodos.valor, 0) AS valor" in query


def test_an_empty_period_of_a_count_counts_as_zero():
    block = changed("ventas_semana_linea", lambda b: b.update(medida={"agregado": "count"}))
    assert "coalesce(periodos.valor, 0) AS valor" in text(block)


def test_an_empty_period_of_an_average_stays_empty():
    block = changed("ventas_semana_linea", lambda b: b.update(medida={"agregado": "avg", "de": "pedidos_detalle.valor_neto"}))
    query = text(block)
    assert "coalesce(" not in query and ", periodos.valor AS valor FROM entidades" in query


def test_the_base_averages_the_n_previous_periods_and_the_value_is_the_current_one():
    query = text(fixture_block("ventas_semana_linea"))
    current = "date_trunc('week', CAST(%(dia)s AS date) - 6)::date"
    assert f"max(marco.valor) FILTER (WHERE marco.periodo = {current})::numeric AS \"ventas\"" in query
    assert f"avg(marco.valor) FILTER (WHERE marco.periodo < {current})::numeric AS \"ventas_base\"" in query


def without_baseline(block):
    del block["linea_base"], block["salida"]["base"], block["salida"]["delta"]


@pytest.mark.parametrize("change", [lambda block: None, without_baseline])
def test_every_join_is_a_left_join(change):
    block = changed("ventas_semana_linea", change)
    query = text(block)
    for name in block["unir"]:
        assert f'LEFT JOIN "centinela"."{name}" AS "{name}" ON' in query
    assert query.count('JOIN "centinela".') == query.count('LEFT JOIN "centinela".') == len(block["unir"])


def test_a_closing_date_in_a_measure_is_read_as_empty_after_dia():
    block = changed("oc_abiertas", lambda b: b.update(medida={"agregado": "max", "de": "ordenes_compra.fecha_recibida"}))
    assert 'CASE WHEN "ordenes_compra"."fecha_recibida" <= CAST(%(dia)s AS date) THEN "ordenes_compra"."fecha_recibida" END' in text(block)


@pytest.mark.parametrize(
    "block, guard, words",
    [
        pytest.param(changed("oc_abiertas", lambda b: b.update(fuente="clientes")), "fuente", "not a source", id="unknown-source"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(unir=["bodegas"])), "fuente", "not a join", id="undeclared-join"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(unir=["clientes", "pedidos"])), "fuente", "before it", id="join-out-of-order"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(unir=["pedidos", "vendedores"], agrupar=["vendedores.nombre"])), "fuente", "not readable", id="a-persons-name"),
        pytest.param(changed("ventas_semana_linea", lambda b: b["filtro"][0].update(op="=", valor="Pendiente de despacho")), "fuente", "end of the dataset", id="fuga-unknown-value"),
        pytest.param(changed("ventas_semana_linea", lambda b: b["filtro"][0].update(op="<")), "fuente", "end of the dataset", id="fuga-ordering"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(medida={"agregado": "max", "de": "pedidos.estado"})), "fuente", "end of the dataset", id="fuga-in-a-measure"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(agrupar=["pedidos_detalle.cantidad"])), "fuente", "not a dimension", id="undeclared-dimension"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(unir=["productos"])), "reloj", "dates it", id="undated-source"),
        pytest.param(changed("facturas_abiertas", lambda b: (b.pop("abierto_al_dia"), b.update(ventana={"columna": "facturas.fecha_vencimiento", "dias": 30}))), "reloj", "not a date of an event", id="window-on-a-term"),
        pytest.param(changed("facturas_abiertas", lambda b: b["abierto_al_dia"].update(hasta="facturas.fecha_vencimiento")), "reloj", "closes a row", id="open-until-a-term"),
        pytest.param(changed("facturas_abiertas", lambda b: b["abierto_al_dia"].update(hasta="cobrada")), "reloj", "closing", id="open-until-nothing"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(agrupar=[{"columna": "ordenes_compra.fecha_recibida", "por": "mes"}])), "reloj", "event or a term", id="period-of-a-closing"),
        pytest.param(changed("ventas_semana_linea", lambda b: b["linea_base"].update(columna="pedidos_detalle.valor_neto")), "reloj", "not a date of an event", id="baseline-on-a-number"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(filtro=[{"columna": "ordenes_compra.cantidad", "op": "=", "valor": "mucho"}])), "lenguaje", "not a integer", id="literal-of-another-type"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(medida={"agregado": "sum", "de": "ordenes_compra.sku"})), "lenguaje", "needs a number", id="sum-of-text"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(medida={"agregado": "max", "de": {"op": "+", "izq": "ordenes_compra.fecha_oc", "der": "ordenes_compra.fecha_esperada"}})), "lenguaje", "does not apply", id="date-plus-date"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(agrupar=["productos.linea", {"columna": "pedidos.fecha", "por": "mes"}])), "lenguaje", "own period", id="baseline-with-a-period"),
        pytest.param(changed("oc_abiertas", lambda b: b["salida"].update(valor="proveedor_id")), "lenguaje", "unique name", id="duplicate-name"),
        pytest.param(changed("oc_abiertas", lambda b: b["salida"].update(valor="dia")), "lenguaje", "unique name", id="reserved-name"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(filtro=[{"columna": "ordenes_compra.fecha_oc", "op": ">=", "valor": "2026W011"}])), "lenguaje", "YYYY-MM-DD", id="date-in-week-form"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(filtro=[{"columna": "ordenes_compra.sku", "op": "=", "valor": "a\x00b"}])), "lenguaje", "filtro/0/valor", id="text-with-nul"),
    ],
)
def test_a_block_the_kernel_cannot_bound_is_refused_with_its_guard(block, guard, words):
    refusal = refused(block)
    assert refusal.guard == guard and words in refusal.detail, refusal


def test_a_function_reads_its_argument_and_belongs_to_the_owner_role():
    definition = function_definition("oc_abiertas", fixture_block("oc_abiertas"), SOURCES).as_string()
    assert definition.startswith('DROP FUNCTION IF EXISTS "centinela"."k_oc_abiertas"(date);\nCREATE FUNCTION "centinela"."k_oc_abiertas"(dia date) RETURNS TABLE ("proveedor_id" text, "ordenes_abiertas" bigint)')
    assert "SECURITY DEFINER SET search_path = pg_catalog, pg_temp" in definition
    assert "CAST(dia AS date)" in definition and "%(dia)s" not in definition
    assert 'ALTER FUNCTION "centinela"."k_oc_abiertas"(date) OWNER TO centinela_propietario;' in definition
    assert 'REVOKE ALL ON FUNCTION "centinela"."k_oc_abiertas"(date) FROM PUBLIC;' in definition
    assert 'GRANT EXECUTE ON FUNCTION "centinela"."k_oc_abiertas"(date) TO centinela_lector;' in definition


def test_a_metric_name_outside_the_pattern_is_refused():
    with pytest.raises(Refused) as caught:
        function_definition("Oc-Abiertas", fixture_block("oc_abiertas"), SOURCES)
    assert caught.value.guard == "lenguaje"


def test_freezing_keeps_the_text_its_hash_and_the_compiler_version():
    frozen = freeze(compile_kpi(fixture_block("oc_abiertas"), SOURCES))
    assert "%(dia)s" in frozen.sql and frozen.hash == digest(frozen.sql) and frozen.compiler_version == "3"


def calls(tree, attribute):
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == attribute]


def test_every_sql_fragment_of_the_package_is_a_constant():
    for path in PACKAGE.glob("*.py"):
        for call in calls(ast.parse(path.read_text()), "SQL"):
            argument = call.args[0] if len(call.args) == 1 else None
            assert isinstance(argument, ast.Constant) and isinstance(argument.value, str), f"{path.name}:{call.lineno}"


def test_no_query_of_the_package_is_built_from_a_formatted_string():
    for path in PACKAGE.glob("*.py"):
        for call in calls(ast.parse(path.read_text()), "execute"):
            first = call.args[0]
            formatted = isinstance(first, (ast.JoinedStr, ast.BinOp)) or (
                isinstance(first, ast.Call) and isinstance(first.func, ast.Attribute) and first.func.attr == "format" and isinstance(first.func.value, ast.Constant)
            )
            assert not formatted, f"{path.name}:{call.lineno}"
