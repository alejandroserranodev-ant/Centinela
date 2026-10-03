"""
Impact Calculator Tool: calculate impact of proposed actions.

Implements 8 formulas from packages/tools/AGENTS.md.

Stub implementation. Real implementation requires:
- Database views for each metric (v_cartera_cliente, v_precio_sku, etc.)
- Formula logic with SQL queries
"""

import logging
from typing import Any

from .tools import CalcularImpactoProvider, ImpactResult

logger = logging.getLogger(__name__)


class CalcularImpactoStub(CalcularImpactoProvider):
    """Stub implementation of impact calculator."""

    def __init__(self):
        """Initialize stub."""
        self.query_counter = 0
        self.formulas = {
            "traslado_costo": {
                "description": "Cost increase passed to list price",
                "output": "price_increase_pct",
                "queries": [
                    "SELECT costo_actual FROM v_costo_sku WHERE sku = :sku AND fecha <= :day",
                    "SELECT precio_lista FROM v_precio_sku WHERE sku = :sku AND vigente_desde <= :day",
                    "SELECT SUM(cantidad) FROM v_ventas WHERE sku = :sku AND fecha >= :day - 90d",
                ]
            },
            "precio_a_margen_minimo": {
                "description": "Price to achieve minimum margin",
                "output": "price_increase_pct",
                "queries": [
                    "SELECT margen_pct, margen_minimo_pct FROM v_margen_linea WHERE linea = :linea",
                    "SELECT SUM(valor_neto) FROM v_ventas WHERE linea = :linea AND fecha >= :day - 30d",
                ]
            },
            "cartera_vencida": {
                "description": "Past-due customer balance",
                "output": "impact_once",
                "queries": [
                    "SELECT saldo_vencido FROM v_cartera_cliente WHERE cliente_id = :cliente_id",
                ]
            },
            "ventas_protegidas": {
                "description": "Units to protect sales coverage",
                "output": "units + impact_once",
                "queries": [
                    "SELECT demanda_prom_30d, existencia, clase_abc FROM v_cobertura_inventario WHERE sku = :sku",
                    "SELECT precio_lista FROM v_precio_sku WHERE sku = :sku AND vigente_desde <= :day",
                ]
            },
            "descuento_recuperado": {
                "description": "Discount exceeded recovery",
                "output": "impact_per_month",
                "queries": [
                    "SELECT SUM(descuento_en_exceso) FROM v_descuentos_fuera_politica WHERE vendedor_id = :vendedor_id AND fecha >= :day - 28d",
                ]
            },
            "venta_bajo_costo": {
                "description": "Below-cost sales loss",
                "output": "impact_per_month",
                "queries": [
                    "SELECT SUM(ABS(margen_bruto)) FROM v_ventas WHERE sku = :sku AND margen_bruto < 0 AND fecha >= :day - 28d",
                ]
            },
            "compra_recuperada": {
                "description": "Lost customer recovery value",
                "output": "impact_per_month",
                "queries": [
                    "SELECT AVG(valor_neto) FROM v_ventas WHERE cliente_id = :cliente_id AND fecha >= :ultima_compra - 180d AND fecha < :ultima_compra",
                ]
            },
        }

    def calculate(
        self,
        formula_name: str,
        entidad: str,
        simulated_day: str,
    ) -> ImpactResult:
        """
        Calculate impact using a specific formula.

        Args:
            formula_name: One of the 8 formulas
            entidad: Entity ID (cliente_id, sku, vendedor_id, etc.)
            simulated_day: YYYY-MM-DD

        Returns:
            ImpactResult with calculated value and queryId

        Formulas implemented:
            1. traslado_costo → price_increase_pct, impact/month
            2. precio_a_margen_minimo → price_increase_pct, impact/month
            3. cartera_vencida → impact once
            4. ventas_protegidas → units, impact once
            5. descuento_recuperado → impact/month
            6. venta_bajo_costo → impact/month
            7. compra_recuperada → impact/month
            8. (dias_pago_prom has NO formula)
        """
        if formula_name not in self.formulas:
            return ImpactResult(
                value=0,
                unit="",
                queryId="",
                formula=formula_name,
                error=f"Formula '{formula_name}' not found. Use one of: {list(self.formulas.keys())}"
            )

        self.query_counter += 1
        query_id = f"q_impacto_{formula_name}_{self.query_counter:02d}"

        logger.info(
            f"Impact calculation: {formula_name} for {entidad} on {simulated_day}",
            extra={"queryId": query_id, "formula": formula_name}
        )

        formula = self.formulas[formula_name]

        # Stub: return zero impact
        # Real: execute queries in formula.queries, calculate impact
        return ImpactResult(
            value=0,
            unit="COP" if "impacto" in formula["output"] else "%",
            queryId=query_id,
            formula=formula_name,
            assumptions=["Stub implementation returns 0; use real SQL for actual impact"],
            error=None
        )
