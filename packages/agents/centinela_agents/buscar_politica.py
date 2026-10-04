"""
Policy Search Tool: find relevant policy passages.

Stub implementation. Real implementation requires:
- pgvector extension in PostgreSQL
- Policy texts in database with embeddings
- bge-m3 embeddings (Spanish-optimized)
"""

import logging
from typing import Any

from .tools import BuscarPoliticaProvider, PolicyPassage

logger = logging.getLogger(__name__)


class BuscarPoliticaStub(BuscarPoliticaProvider):
    """Stub implementation of policy search (no embeddings)."""

    def __init__(self):
        """Initialize stub."""
        self.policies = {
            "FIN-POL-004": {
                "§3": "Cupo de crédito: el saldo abierto no debe exceder el cupo_credito establecido.",
                "§4": "Seguimiento y escalamiento: máx 15 días sin vencerse, luego tramos 16-30, 31-60, >60 días.",
                "§5": "Señales de alerta temprana: concentración >10%, aumento de días de pago >50%.",
            },
            "OPE-POL-007": {
                "§2": "Cobertura mínima: clase A ≥10 días, clase B ≥7 días.",
                "§3": "Proveedores: orden debe llegar en fecha esperada.",
                "§4": "Revisión de precios: traslado de costo en lista, margen mínimo línea.",
            },
            "COM-POL-002": {
                "§2": "Topes de descuento por segmento: no exceder tope sin aprobación.",
                "§3": "Prohibiciones: dos semanas consecutivas escala según §5.",
                "§4": "Venta bajo costo: prohibida sin aprobación de Gerencia General.",
                "§5": "Recuperación: Control Comercial o Gerencia Comercial.",
            },
        }

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[PolicyPassage]:
        """
        Search for relevant policy passages.

        In real implementation, this would:
        1. Embed query with bge-m3
        2. Search pgvector in policy table
        3. Return top_k passages with relevance scores
        4. Mark as DATA (not orders)

        Args:
            query: Spanish search query (e.g., "límite de crédito")
            top_k: Number of results

        Returns:
            List of PolicyPassage with text and relevance

        Notes:
            - Stub returns empty list
            - Real: would use pgvector similarity search
        """
        logger.info(f"Policy search: '{query}' (top_k={top_k})")

        return []

    def search_by_code(
        self,
        policy_code: str,
        section: str | None = None,
    ) -> list[PolicyPassage]:
        """
        Retrieve policy by code (for citation).

        Args:
            policy_code: e.g., "FIN-POL-004"
            section: e.g., "§4" (optional)

        Returns:
            List of PolicyPassage
        """
        logger.info(f"Policy lookup: {policy_code} {section or ''}")

        return []
