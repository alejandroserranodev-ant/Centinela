from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.metrics import load_metrics
from centinela_agents.walk import Context, detect, still_breaks
import pytest

from support import METRICAS, VIEW_CATALOG, base_tree

DAY = "2026-03-02"
LATER = "2026-03-05"


def run(metric, row, catalog=VIEW_CATALOG):
    ctx = Context.of(base_tree(), load_metrics(METRICAS), catalog, lambda m, day: [row] if m == metric and day == DAY else [])
    return detect(ctx, DAY)


FIRING = [
    ("saldo_vencido", {"cliente_id": "CLI-001", "max_dias_vencido": 20, "saldo_abierto": 100, "cupo_credito": 5000}, "detectar.cartera.saldo_vencido.dias"),
    ("saldo_vencido", {"cliente_id": "CLI-001", "max_dias_vencido": 6, "saldo_abierto": 6000, "cupo_credito": 5000}, "detectar.cartera.saldo_vencido.cupo"),
    ("concentracion_vencida_pct", {"cliente_id": "CLI-002", "concentracion_vencida_pct": 12.5}, "detectar.cartera.concentracion_vencida_pct.participacion"),
    ("dias_pago_prom", {"cliente_id": "CLI-003", "mes_factura": "2026-02-01", "aumento_pct": 60.0}, "detectar.cartera.dias_pago_prom.aumento"),
    ("margen_pct", {"semana": "2026-02-23", "linea": "Hogar", "caida_pts": 3.5, "margen_pct": 20.0, "margen_minimo_pct": 18.0}, "detectar.margen.margen_pct.caida"),
    ("margen_pct", {"semana": "2026-02-23", "linea": "Hogar", "caida_pts": 1.0, "margen_pct": 15.0, "margen_minimo_pct": 18.0}, "detectar.margen.margen_pct.minimo"),
    ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "A", "cobertura_dias": 9.0}, "detectar.inventario.cobertura_dias.minima"),
    ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "B", "cobertura_dias": 6.0}, "detectar.inventario.cobertura_dias.minima"),
    ("descuento_en_exceso", {"vendedor_id": "VEN-01", "semana": "2026-02-23", "descuento_en_exceso": 120000}, "detectar.comercial.descuento_en_exceso.tope"),
    ("margen_bruto_negativo", {"pedido_id": "P-1", "linea_n": 1, "margen_bruto": -5000}, "detectar.comercial.margen_bruto_negativo.bajo_costo"),
    ("variacion_costo_pct", {"sku": "SKU-3", "variacion_pct": 7.5, "dias_habiles_sin_traslado": 12}, "detectar.abastecimiento.variacion_costo_pct.sin_traslado"),
    ("dias_retraso", {"oc_id": "OC-1", "dias_retraso": 4, "recibida": False}, "detectar.abastecimiento.dias_retraso.pendiente"),
    ("veces_intervalo_habitual", {"cliente_id": "CLI-004", "pedidos": 14, "veces_intervalo_habitual": 3.6}, "detectar.clientes.veces_intervalo_habitual.inactividad"),
]

QUIET = [
    ("saldo_vencido", {"cliente_id": "CLI-001", "max_dias_vencido": 15, "saldo_abierto": 100, "cupo_credito": 5000}),
    ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "B", "cobertura_dias": 8.0}),
    ("variacion_costo_pct", {"sku": "SKU-3", "variacion_pct": 7.5, "dias_habiles_sin_traslado": 3}),
    ("dias_retraso", {"oc_id": "OC-1", "dias_retraso": 4, "recibida": True}),
    ("veces_intervalo_habitual", {"cliente_id": "CLI-004", "pedidos": 9, "veces_intervalo_habitual": 5.0}),
    ("descuento_en_exceso", {"vendedor_id": "VEN-01", "semana": "2026-02-23", "descuento_en_exceso": 0}),
]


@pytest.mark.parametrize("metric, row, last", FIRING, ids=[last for _, _, last in FIRING])
def test_each_threshold_node_fires_on_a_breaking_row(metric, row, last):
    (detection,) = run(metric, row)
    assert detection.metric == metric
    assert detection.entry == "hoja.vigia.titular"
    assert detection.path[-1] == (last, "si")
    assert detection.entity == tuple(row.get(column) for column in VIEW_CATALOG.kpis[metric].entity)


@pytest.mark.parametrize("metric, row", QUIET)
def test_a_row_inside_its_threshold_fires_nothing(metric, row):
    assert run(metric, row) == []


@pytest.mark.parametrize(
    "metric, row",
    [
        ("saldo_vencido", {"cliente_id": "CLI-009", "max_dias_vencido": None, "saldo_abierto": 0, "cupo_credito": 5000}),
        ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "C", "cobertura_dias": 1.0}),
        ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "A", "cobertura_dias": None}),
    ],
)
def test_a_null_value_or_a_class_without_threshold_fires_nothing(metric, row):
    assert run(metric, row) == []


def test_a_descriptive_kpi_fires_nothing():
    real = VIEW_CATALOG.kpis["saldo_vencido"]
    catalog = Catalog({**VIEW_CATALOG.kpis, "saldo_vencido": Kpi(real.entity, real.columns, descriptive=True)})
    assert run("saldo_vencido", {"cliente_id": "CLI-001", "max_dias_vencido": 20}, catalog) == []


def test_a_customer_six_days_late_on_a_thirty_day_habit_fires_nothing_on_the_base():
    rows = {
        "saldo_vencido": [{"cliente_id": "CLI-007", "max_dias_vencido": 6, "saldo_abierto": 900000, "cupo_credito": 5000000}],
        "dias_pago_prom": [{"cliente_id": "CLI-007", "mes_factura": "2026-02-01", "aumento_pct": 20.0}],
    }
    ctx = Context.of(base_tree(), load_metrics(METRICAS), VIEW_CATALOG, lambda metric, day: rows.get(metric, []))
    assert detect(ctx, DAY) == []


def state_of(path, rows_later):
    ctx = Context.of(base_tree(), load_metrics(METRICAS), VIEW_CATALOG, lambda metric, day: rows_later if day == LATER else [])
    state = {
        "simulated_day": DAY,
        "detection": {"metric": "saldo_vencido", "entity": ["CLI-001"], "path": path},
        "decision": {"kind": "approve", "simulated_day": LATER},
    }
    return state, ctx


BY_DAYS = [["detectar.raiz", "si"], ["detectar.cartera", "si"], ["detectar.cartera.saldo_vencido", "si"], ["detectar.cartera.saldo_vencido.dias", "si"]]
BY_CUPO = [*BY_DAYS[:3], ["detectar.cartera.saldo_vencido.dias", "no"], ["detectar.cartera.saldo_vencido.cupo", "si"]]


@pytest.mark.parametrize(
    "path, rows, expected",
    [
        (BY_DAYS, [{"cliente_id": "CLI-001", "max_dias_vencido": 25, "saldo_abierto": 1, "cupo_credito": 5}], True),
        (BY_DAYS, [{"cliente_id": "CLI-001", "max_dias_vencido": 0, "saldo_abierto": 1, "cupo_credito": 5}], False),
        (BY_DAYS, [{"cliente_id": "CLI-002", "max_dias_vencido": 25, "saldo_abierto": 1, "cupo_credito": 5}], False),
        (BY_DAYS, [], False),
        (BY_CUPO, [{"cliente_id": "CLI-001", "max_dias_vencido": 20, "saldo_abierto": 6000, "cupo_credito": 5000}], True),
    ],
    ids=["still late", "paid", "another customer only", "no row", "cupo still exceeded"],
)
def test_still_breaks_reapplies_each_node_the_detection_passed_on_si(path, rows, expected):
    state, ctx = state_of(path, rows)
    assert still_breaks(state, ctx) is expected


def test_still_breaks_is_false_when_no_kpi_node_of_the_path_is_left_in_the_tree():
    gone = [["detectar.cartera.saldo_vencido.retirado", "si"]]
    state, ctx = state_of(gone, [{"cliente_id": "CLI-001", "max_dias_vencido": 25, "saldo_abierto": 1, "cupo_credito": 5}])
    assert still_breaks(state, ctx) is False


def test_still_breaks_refuses_two_rows_of_one_entity():
    late = {"cliente_id": "CLI-001", "max_dias_vencido": 25, "saldo_abierto": 1, "cupo_credito": 5}
    state, ctx = state_of(BY_DAYS, [late, {**late, "max_dias_vencido": 0}])
    with pytest.raises(ValueError, match="CLI-001"):
        still_breaks(state, ctx)
