"""
SQL Vistas Tool: read-only access to semantic layer views.

Stub implementation. Real implementation requires:
- Database connection to semantic layer
- View definitions (v_cartera_cliente, v_cobertura_inventario, etc.)
- Data masking for personal data
"""

import logging
from typing import Any

from .tools import SqlQuery, SqlVistasProvider

logger = logging.getLogger(__name__)


class SqlVistasStub(SqlVistasProvider):
    """Stub implementation of SQL vistas tool (no database)."""

    def __init__(self):
        """Initialize stub."""
        self.query_counter = 0

    def query(
        self,
        view_name: str,
        filters: dict[str, Any],
        simulated_day: str,
    ) -> SqlQuery:
        """
        Execute a stub query (returns empty result).

        In real implementation, this would:
        1. Connect to database
        2. Build WHERE clause from filters
        3. Add simulated_day filter
        4. Execute query
        5. Mask personal data (names → IDs)
        6. Return rows with unique queryId

        Args:
            view_name: e.g., "v_cartera_cliente"
            filters: e.g., {"cliente_id": "C123"}
            simulated_day: YYYY-MM-DD

        Returns:
            SqlQuery with rows and queryId
        """
        self.query_counter += 1
        query_id = f"q_sql_{self.query_counter:04d}"

        logger.info(
            f"SQL query: {view_name} with {filters} on {simulated_day}",
            extra={"queryId": query_id}
        )

        # Stub: return empty result
        # Real: would query database
        return SqlQuery(
            queryId=query_id,
            rows=[],
            error=None  # Or error if query failed
        )

    def query_by_name(self, query_name: str, simulated_day: str) -> SqlQuery:
        """
        Execute a named query (pre-defined in skills/).

        Each skill file (analista/saldo_vencido.md) names queries by ID.
        This method looks them up and executes them.

        Args:
            query_name: Name from skill file (e.g., "q_dias_retraso")
            simulated_day: YYYY-MM-DD

        Returns:
            SqlQuery result
        """
        self.query_counter += 1
        query_id = f"q_{query_name}_{self.query_counter:02d}"

        logger.info(
            f"Named query: {query_name} on {simulated_day}",
            extra={"queryId": query_id}
        )

        # Stub: return empty
        # Real: look up query_name in catalog, execute with simulated_day
        return SqlQuery(
            queryId=query_id,
            rows=[],
            error=None
        )
