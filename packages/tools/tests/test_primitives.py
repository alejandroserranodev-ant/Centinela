# The primitives the current metrics need, with no database: one planted violation per new bound of
# the language and per new refusal of the compiler, each with its guard, and the SQL each primitive
# compiles to. The blocks come from data/metricas.yaml, because they are the KPIs these primitives
# exist for.
import copy

import pytest

from centinela_tools.compiler import compile_kpi
from centinela_tools.language import check_block
from centinela_tools.paths import METRICAS
from centinela_tools.refusal import Refused
from centinela_tools.sources import load_sources
from centinela_tools.tools import load_entries

SOURCES = load_sources()
ENTRIES = load_entries(METRICAS)
SUM = {"agregado": "sum", "de": "facturas.valor_total"}


def block(metric, change=lambda b: None):
    copied = copy.deepcopy(ENTRIES[metric]["kernel"])
    change(copied)
    return copied


def text(metric, change=lambda b: None):
    return compile_kpi(block(metric, change), SOURCES, thresholds=ENTRIES[metric].get("umbrales")).query.as_string()


def refused(metric, change, thresholds=None):
    with pytest.raises(Refused) as caught:
        compile_kpi(block(metric, change), SOURCES, thresholds=ENTRIES[metric].get("umbrales") if thresholds is None else thresholds)
    return caught.value


def nested(depth):
    inner = {"fuente": "facturas", "agrupar": ["facturas.cliente_id"], "medida": SUM, "salida": {"valor": "v"}}
    for _ in range(depth):
        inner = {**inner, "tomar": {"t": {"kpi": copy.deepcopy(inner), "por": {"cliente_id": "facturas.cliente_id"}}}}
    return inner


def deep(levels):
    node = "saldo_vencido"
    for _ in range(levels):
        node = {"op": "+", "izq": node, "der": 1}
    return node


@pytest.mark.parametrize(
    "change, path",
    [
        pytest.param(lambda b: b.update(columnas={f"c{i}": SUM for i in range(9)}), "columnas", id="nine-columns"),
        pytest.param(lambda b: b.update(derivadas={f"d{i}": "saldo_vencido" for i in range(7)}), "derivadas", id="seven-derived"),
        pytest.param(lambda b: b.update(decimales={"saldo_vencido": 5}), "decimales/saldo_vencido", id="five-decimals"),
        pytest.param(lambda b: b.update(tener=[{"columna": "saldo_vencido", "op": ">", "valor": i} for i in range(4)]), "tener", id="four-having"),
        pytest.param(lambda b: b.update(tomar={f"t{i}": {"kpi": nested(0), "por": {"cliente_id": "facturas.cliente_id"}} for i in range(3)}), "tomar", id="three-taken"),
        pytest.param(lambda b: b["medida"].update(si=[{"columna": "facturas.fecha_vencimiento", "op": "<", "contra": "dia"}] * 4), "medida/si", id="four-conditions"),
        pytest.param(lambda b: b["medida"]["si"][0].update(menos_dias=1, menos_meses=1), "medida/si/0", id="days-and-months"),
        pytest.param(lambda b: b["medida"]["si"][0].update(menos_dias=366), "medida/si/0/menos_dias", id="days-past-365"),
        pytest.param(lambda b: b["medida"]["si"][0].update(menos_meses=13), "medida/si/0/menos_meses", id="months-past-12"),
        pytest.param(lambda b: b["medida"]["si"][0].update(op="en"), "medida/si/0/op", id="en-against-a-column"),
        pytest.param(lambda b: b.update(medida={"agregado": "ultimo", "de": "facturas.valor_total"}), "medida", id="last-without-order"),
        pytest.param(lambda b: b.update(medida={**SUM, "por": "facturas.fecha_factura"}), "medida", id="order-on-a-sum"),
        pytest.param(lambda b: b.update(derivadas={"d": {"raiz": "saldo_vencido"}}), "derivadas/d", id="unknown-operation"),
        pytest.param(lambda b: b.update(derivadas={"d": {"mayor": ["saldo_vencido"]}}), "derivadas/d", id="greatest-of-one"),
    ],
)
def test_a_new_bound_of_the_language_is_refused(change, path):
    with pytest.raises(Refused) as caught:
        check_block(block("saldo_vencido", change))
    assert caught.value.guard == "lenguaje"
    assert caught.value.detail.startswith(path), caught.value.detail


@pytest.mark.parametrize(
    "metric, change, guard, words",
    [
        pytest.param("saldo_vencido", lambda b: b.update(tomar={"t": {"kpi": nested(2), "por": {"cliente_id": "facturas.cliente_id"}}}), "lenguaje", "at most 2 levels", id="taken-three-deep"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": deep(5)}), "lenguaje", "at most 4 operations", id="derived-five-deep"),
        pytest.param("variacion_costo_pct", lambda b: b["tomar"]["precio"].update(por={"sku": "costos_proveedor.sku", "otro": "costos_proveedor.proveedor_id"}), "fuente", "whole entity", id="taken-by-part-of-a-key"),
        pytest.param("saldo_vencido", lambda b: b.update(tomar={"clientes": {"kpi": nested(0), "por": {"cliente_id": "facturas.cliente_id"}}}), "fuente", "already the name", id="taken-named-as-a-join"),
        pytest.param("variacion_costo_pct", lambda b: b["tomar"]["precio"].update(por={"sku": "costos_proveedor.fecha_vigencia"}), "lenguaje", "joins", id="taken-by-another-type"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": "saldo_cero"}), "lenguaje", "no column", id="derived-from-nothing"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": {"umbral": "saldo_vencido"}}), "lenguaje", "umbral", id="threshold-not-in-umbrales"),
        pytest.param("variacion_costo_pct", lambda b: b.update(decimales={"fecha_vigencia": 1}), "lenguaje", "decimales", id="decimals-of-a-date"),
        pytest.param("variacion_costo_pct", lambda b: b.update(tener=[{"columna": "fecha_vigencia", "op": ">", "valor": 0}]), "lenguaje", "tener", id="having-on-a-date"),
        pytest.param("saldo_vencido", lambda b: b["medida"]["si"][0].update(contra="facturas.valor_total"), "lenguaje", "cannot be compared", id="date-against-a-number"),
        pytest.param("saldo_vencido", lambda b: b["medida"]["si"][0].update(columna="facturas.valor_total", contra="clientes.cupo_credito", menos_dias=3), "lenguaje", "no date", id="days-back-from-a-number"),
        pytest.param("margen_bruto_negativo", lambda b: b["medida"].update(si=[{"columna": "pedidos.estado", "op": "=", "contra": "pedidos.canal"}]), "fuente", "end of the dataset", id="fuga-against-a-column"),
        pytest.param("variacion_costo_pct", lambda b: b.update(medida={"agregado": "ultimo", "de": "costos_proveedor.costo_unitario", "por": "costos_proveedor.sku"}), "reloj", "not a date of an event", id="last-by-a-non-event"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": {"dias_habiles": {"desde": "saldo_abierto", "hasta": "dia"}}}), "lenguaje", "two dates", id="business-days-of-a-number"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": {"si": {"cuando": "saldo_abierto", "entonces": 1, "sino": 0}}}), "lenguaje", "cuando", id="if-on-a-number"),
        pytest.param("dias_retraso", lambda b: b.update(derivadas={"d": {"participacion": "fecha_esperada"}}), "lenguaje", "participacion", id="share-of-a-date"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": {"periodo_anterior": "saldo_vencido"}}), "lenguaje", "exactly one", id="previous-period-without-a-period"),
        pytest.param("cobertura_dias", lambda b: b["tomar"]["precio"].update(por={"sku": "precio.sku"}), "fuente", "neither the source", id="taken-by-its-own-column"),
        pytest.param("cobertura_dias", lambda b: b["tomar"]["precio"].update(por={"sku": "pendientes.sku"}), "fuente", "neither the source", id="taken-by-a-later-taken-kpi"),
        pytest.param("descuento_en_exceso", lambda b: b["derivadas"].update(d={"participacion": "exceso_semana_anterior"}), "lenguaje", "every row", id="share-of-a-previous-period"),
        pytest.param("descuento_en_exceso", lambda b: b["derivadas"].update(s={"participacion": "descuento_en_exceso"}, d={"periodo_anterior": "s"}), "lenguaje", "every row", id="previous-period-of-a-share"),
        pytest.param("descuento_en_exceso", lambda b: b["derivadas"].update(s={"op": "+", "izq": "exceso_semana_anterior", "der": 1}, d={"participacion": "s"}), "lenguaje", "every row", id="share-of-a-column-over-a-window"),
        pytest.param("dias_pago_prom", lambda b: b["columnas"].update(valor={"agregado": "count"}), "lenguaje", "unique name", id="a-column-named-valor"),
    ],
)
def test_a_new_primitive_the_kernel_cannot_bound_is_refused(metric, change, guard, words):
    refusal = refused(metric, change)
    assert refusal.guard == guard and words in refusal.detail, refusal


def test_a_condition_on_a_measure_is_a_filter_and_an_empty_sum_is_zero():
    assert 'coalesce(sum("facturas"."valor_total") FILTER (WHERE "facturas"."fecha_vencimiento" < CAST(%(dia)s AS date)), 0)::numeric' in text("saldo_vencido")


def test_dia_is_an_operand_of_an_expression():
    assert '(CAST(%(dia)s AS date) - "facturas"."fecha_vencimiento")' in text("saldo_vencido")


def test_a_filter_compares_two_columns():
    assert '"pedidos_detalle"."descuento_pct" > "topes"."tope_descuento_pct"' in text("descuento_en_exceso")


def test_a_condition_reaches_back_from_a_date_by_months():
    assert "(\"ultima\".\"ultima_compra\" - interval '1 month' * 6)::date" in text("veces_intervalo_habitual")


def test_the_last_and_the_previous_value_follow_an_event_date():
    query = text("variacion_costo_pct")
    assert '(array_agg("costos_proveedor"."costo_unitario" ORDER BY "costos_proveedor"."fecha_vigencia" DESC NULLS LAST))[1]' in query
    assert '(array_agg("costos_proveedor"."costo_unitario" ORDER BY "costos_proveedor"."fecha_vigencia" DESC NULLS LAST))[2]' in query


def test_a_taken_kpi_joins_on_its_whole_entity_and_reads_the_same_day():
    query = text("cobertura_dias")
    assert ') AS "precio" ON "precio"."sku" = "inventario_diario"."sku"' in query
    assert '"lista_precios"."fecha_vigencia" <= CAST(%(dia)s AS date)' in query
    assert query.count("LEFT JOIN (SELECT") == 2


def test_a_taken_kpi_is_many_to_one_by_construction():
    taken = compile_kpi(block("cobertura_dias")["tomar"]["precio"]["kpi"], SOURCES)
    assert taken.entity == ("sku",)


def test_a_derived_column_reads_the_unrounded_value_and_only_the_output_is_rounded():
    query = text("cobertura_dias")
    assert 'round(("nucleo"."existencia"::numeric / NULLIF("nucleo"."demanda_prom_30d"::numeric, 0))::numeric, 1)::numeric AS "cobertura_dias"' in query
    assert 'round("nucleo"."demanda_prom_30d"::numeric, 1)::numeric AS "demanda_prom_30d"' in query


def test_a_threshold_by_a_dimension_is_read_from_umbrales():
    assert "(CASE \"nucleo\".\"clase_abc\" WHEN 'A' THEN 10 WHEN 'B' THEN 7 END)" in text("cobertura_dias")


def test_business_days_compile_to_a_count_of_monday_to_friday():
    assert "generate_series(\"nucleo\".\"fecha_vigencia\" + 1, CAST(%(dia)s AS date), interval '1 day') AS habil(d) WHERE extract(isodow FROM habil.d) < 6" in text("variacion_costo_pct")


def test_a_share_divides_by_the_total_of_every_row():
    assert '(100 * "nucleo"."saldo_vencido"::numeric / NULLIF(sum("nucleo"."saldo_vencido") OVER (), 0))' in text("concentracion_vencida_pct")


def test_having_keeps_only_the_rows_it_names():
    assert text("margen_bruto_negativo").endswith('AS kpi WHERE "kpi"."margen_bruto" < 0')


def test_a_drop_is_the_base_minus_the_value():
    current = "date_trunc('week', CAST(%(dia)s AS date) - 6)::date"
    assert f"(avg(marco.valor) FILTER (WHERE marco.periodo < {current})::numeric - max(marco.valor) FILTER (WHERE marco.periodo = {current})::numeric)::numeric AS \"caida_pts\"" in text("margen_pct")


def test_a_column_of_a_baseline_kpi_is_measured_on_the_current_period():
    current = "date_trunc('week', CAST(%(dia)s AS date) - 6)::date"
    query = text("margen_pct")
    assert f'max("marco"."ventas") FILTER (WHERE marco.periodo = {current})::numeric AS "ventas"' in query
    assert 'coalesce("periodos"."ventas", 0) AS "ventas"' in query


def test_a_kpi_with_no_threshold_cannot_read_one():
    refusal = refused("cobertura_dias", lambda b: None, thresholds={})
    assert refusal.guard == "lenguaje" and "umbral cobertura_dias" in refusal.detail


def test_the_previous_period_is_the_same_entity_one_period_before():
    expected = (
        'max("nucleo"."descuento_en_exceso") OVER (PARTITION BY "nucleo"."vendedor_id" ORDER BY "nucleo"."semana" '
        "RANGE BETWEEN interval '1 week' PRECEDING AND interval '1 week' PRECEDING)"
    )
    assert expected in text("descuento_en_exceso")
