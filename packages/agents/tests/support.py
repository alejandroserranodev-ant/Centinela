# The catalogue the tests hand the validator and the walk. Each metric's columns are its
# v_* view's, plus the ones the base reads that no view has and the kernel builds:
# caida_pts, margen_minimo_pct, concentracion_vencida_pct, aumento_pct, dias_habiles_sin_traslado.
# The real catalogue comes from kpi_catalogo; DOUBTS.md files the gap.
import copy
from pathlib import Path

from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Tree
from centinela_agents.validator import Grounds, load_registry
from centinela_agents.yaml_loader import load_yaml

AGENTS = Path(__file__).resolve().parents[1]
ARBOL = AGENTS / "arbol"
METRICAS = AGENTS.parents[1] / "data" / "metricas.yaml"
SKILLS = AGENTS / "skills"


def kpi(entity, *columns):
    return Kpi(entity=tuple(entity), columns=frozenset({*entity, *columns}))


VIEW_CATALOG = Catalog(
    {
        "margen_pct": kpi(["semana", "linea"], "ventas", "costo", "margen_pct", "caida_pts", "margen_minimo_pct"),
        "saldo_vencido": kpi(["cliente_id"], "segmento", "cupo_credito", "plazo_dias", "saldo_abierto", "saldo_vencido", "max_dias_vencido", "dias_pago_prom_120d"),
        "concentracion_vencida_pct": kpi(["cliente_id"], "saldo_vencido", "concentracion_vencida_pct"),
        "dias_pago_prom": kpi(["cliente_id", "mes_factura"], "dias_pago_prom", "facturas_pagadas", "aumento_pct"),
        "cobertura_dias": kpi(["sku", "bodega_id"], "linea", "clase_abc", "existencia", "demanda_prom_30d", "cobertura_dias", "unidades_pendientes"),
        "variacion_costo_pct": kpi(["sku"], "linea", "clase_abc", "proveedor_id", "costo_unitario", "costo_anterior", "variacion_pct", "fecha_vigencia", "dias_habiles_sin_traslado"),
        "dias_retraso": kpi(["oc_id"], "proveedor_id", "sku", "bodega_id", "fecha_esperada", "cantidad", "costo_unitario", "recibida", "dias_retraso"),
        "descuento_en_exceso": kpi(["vendedor_id", "semana"], "descuento_en_exceso"),
        "margen_bruto_negativo": kpi(["pedido_id", "linea_n"], "sku", "margen_bruto"),
        "veces_intervalo_habitual": kpi(["cliente_id"], "pedidos", "ultima_compra", "intervalo_prom_dias", "dias_sin_comprar", "veces_intervalo_habitual"),
    }
)


def base_data() -> dict:
    return copy.deepcopy(load_yaml(ARBOL / "base.yaml"))


def base_tree() -> Tree:
    return Tree.model_validate(base_data())


def node_of(data: dict, node_id: str) -> dict:
    return next(node for node in data["nodos"] if node["id"] == node_id)


def grounds(catalog: Catalog = VIEW_CATALOG, metrics=None) -> Grounds:
    return Grounds(
        base=base_tree(),
        registry=load_registry(ARBOL / "fundamentos.yaml"),
        metrics=metrics or load_metrics(METRICAS),
        catalog=catalog,
        skills=SKILLS,
    )
