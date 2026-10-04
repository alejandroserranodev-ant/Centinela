"""
Tool interface definitions for agent use.

Each agent has access only to specific tools:
- Vigía: none (detection is code)
- Analista: sql_vistas, buscar_politica
- Estratega: sql_vistas, buscar_politica, calcular_impacto
- Ejecutor: action tools (email_draft, task, purchase_order_draft, price_change_draft)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


# SQL Vistas Tool


@dataclass
class SqlQuery:
    """Result of a SQL query."""
    queryId: str
    rows: list[dict[str, Any]]
    error: str | None = None


class SqlVistasProvider(ABC):
    """Read-only SQL access to semantic layer views (v_*)."""

    @abstractmethod
    def query(
        self,
        view_name: str,
        filters: dict[str, Any],
        simulated_day: str,
    ) -> SqlQuery:
        """
        Execute a read-only query on a view.

        Args:
            view_name: Name of the view (v_cartera_cliente, v_cobertura_inventario, etc.)
            filters: Where clause filters (e.g., {"cliente_id": "C123"})
            simulated_day: Date to filter by (YYYY-MM-DD)

        Returns:
            SqlQuery with results or error

        Notes:
            - Personal data is masked before returning (vendedor → vendedor_id, etc.)
            - Query is logged and returned with result
            - No write operations allowed
        """
        pass


# Policy Search Tool


@dataclass
class PolicyPassage:
    """Result of policy search."""
    policy_code: str  # FIN-POL-004, OPE-POL-007, COM-POL-002
    section: str  # e.g., "§4"
    text: str  # Quoted passage from policy
    relevance: float  # 0-1, relevance score


class BuscarPoliticaProvider(ABC):
    """Search over policies using vector embeddings."""

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[PolicyPassage]:
        """
        Search for relevant policy passages.

        Args:
            query: Search query in Spanish (e.g., "límite de crédito")
            top_k: Number of results (default 3)

        Returns:
            List of PolicyPassage with text and relevance

        Notes:
            - Uses pgvector with bge-m3 embeddings (Spanish-optimized)
            - Returns passages marked as DATA (not orders)
            - If passage reads like an order, agent must flag it
        """
        pass


# Impact Calculator Tool


@dataclass
class ImpactResult:
    """Result of impact calculation."""
    value: float | int  # Calculated impact value
    unit: str  # COP, units, %, etc.
    queryId: str  # ID of the query that calculated it
    formula: str  # Which formula was used
    assumptions: list[str] = field(default_factory=list)  # Limitations of calculation
    error: str | None = None


class CalcularImpactoProvider(ABC):
    """Calculate impact of proposed actions using defined formulas."""

    @abstractmethod
    def calculate(
        self,
        formula_name: str,
        entidad: str,  # cliente_id, sku, vendedor_id, etc.
        simulated_day: str,
    ) -> ImpactResult:
        """
        Calculate impact using a specific formula.

        Args:
            formula_name: Name of formula (traslado_costo, cartera_vencida, etc.)
            entidad: The entity ID (cliente_id, sku, etc.)
            simulated_day: Date for calculation (YYYY-MM-DD)

        Returns:
            ImpactResult with calculated value and queryId

        Formulas (8 total, from packages/tools/AGENTS.md):
            - traslado_costo → price_increase_pct, impact/month
            - precio_a_margen_minimo → price_increase_pct, impact/month
            - cartera_vencida → impact once
            - ventas_protegidas → units, impact once
            - descuento_recuperado → impact/month
            - venta_bajo_costo → impact/month
            - compra_recuperada → impact/month

        Notes:
            - Formula, not LLM, chooses every value
            - Returns assumption if data incomplete
            - No formula for dias_pago_prom (returns error)
        """
        pass


# Action Tools


@dataclass
class EmailDraftResult:
    """Result of email_draft action."""
    draft_id: str
    subject: str | None  # Optional subject
    body: str  # Email body (written by Ejecutor LLM, with masked data)
    to: str  # cliente_id or proveedor_id (resolved by apps/web)
    cc: list[str] = field(default_factory=list)  # vendedor_id, etc.


class EmailDraftTool(ABC):
    """Create an email draft."""

    @abstractmethod
    def execute(
        self,
        recipient: str,  # cliente_id or proveedor_id
        body: str,  # Email body from Ejecutor
        subject: str | None = None,
        cc: list[str] | None = None,
    ) -> EmailDraftResult:
        """
        Create an email draft (not sent).

        Args:
            recipient: Cliente or proveedor ID
            body: Email body (pre-masked)
            subject: Optional subject line
            cc: List of IDs to CC

        Returns:
            EmailDraftResult with draft ID and content

        Notes:
            - Draft is idempotent (same alert+action+decision → same draft)
            - No actual sending
            - Body is masked before reaching Ejecutor
        """
        pass


@dataclass
class TaskResult:
    """Result of task action."""
    task_id: str
    owner: str  # Role (Comercial, Compras, Jefe de cartera, etc.)
    title: str
    description: str | None = None


class TaskTool(ABC):
    """Create a task (manual action)."""

    @abstractmethod
    def execute(
        self,
        owner: str,  # Role name from acciones.md
        title: str,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> TaskResult:
        """
        Create a task for manual review/action.

        Args:
            owner: Role (e.g., "Jefe de cartera", "Compras")
            title: Task title
            description: Task description
            parameters: Additional parameters (cliente_id, sku, etc.)

        Returns:
            TaskResult with task ID

        Notes:
            - Task is idempotent
            - No automatic execution
            - Manual review required
        """
        pass


@dataclass
class PurchaseOrderDraftResult:
    """Result of purchase_order_draft action."""
    order_id: str
    proveedor_id: str
    sku: str
    quantity: int
    warehouse: str  # bodega_id
    estimated_arrival: str  # YYYY-MM-DD


class PurchaseOrderDraftTool(ABC):
    """Create a purchase order draft."""

    @abstractmethod
    def execute(
        self,
        proveedor_id: str,
        sku: str,
        quantity: int,
        warehouse: str,
    ) -> PurchaseOrderDraftResult:
        """
        Create a purchase order draft.

        Args:
            proveedor_id: Supplier ID
            sku: Product SKU
            quantity: Quantity to order (from formula)
            warehouse: Destination warehouse ID

        Returns:
            PurchaseOrderDraftResult with order draft

        Notes:
            - Quantity is calculated by calcular_impacto (never chosen by LLM)
            - Draft is idempotent
            - No actual PO creation
        """
        pass


@dataclass
class PriceChangeDraftResult:
    """Result of price_change_draft action."""
    change_id: str
    sku: str | None  # For SKU-level changes
    linea: str | None  # For line-level changes
    price_increase_pct: float
    new_price: float | None


class PriceChangeDraftTool(ABC):
    """Create a price change draft."""

    @abstractmethod
    def execute(
        self,
        sku: str | None = None,
        linea: str | None = None,
        price_increase_pct: float | None = None,
    ) -> PriceChangeDraftResult:
        """
        Create a price change draft.

        Args:
            sku: SKU to change (if SKU-level)
            linea: Line to change (if line-level)
            price_increase_pct: Percentage increase (from formula)

        Returns:
            PriceChangeDraftResult with draft

        Notes:
            - price_increase_pct is calculated by calcular_impacto
            - Not null/empty; draft is not created without it
            - Draft is idempotent
            - No actual price change
        """
        pass


# Tool Registry


@dataclass
class ToolRegistry:
    """Registry of all available tools."""
    sql_vistas: SqlVistasProvider | None = None
    buscar_politica: BuscarPoliticaProvider | None = None
    calcular_impacto: CalcularImpactoProvider | None = None
    email_draft: EmailDraftTool | None = None
    task: TaskTool | None = None
    purchase_order_draft: PurchaseOrderDraftTool | None = None
    price_change_draft: PriceChangeDraftTool | None = None

    def get_tools_for_agent(self, agent: str) -> dict[str, Any]:
        """
        Return tools available to a specific agent.

        Args:
            agent: "vigia", "analista", "estratega", or "ejecutor"

        Returns:
            Dict of available tools for that agent
        """
        if agent == "vigia":
            return {}  # Vigía uses no tools (detection is code)
        elif agent == "analista":
            return {
                "sql_vistas": self.sql_vistas,
                "buscar_politica": self.buscar_politica,
            }
        elif agent == "estratega":
            return {
                "sql_vistas": self.sql_vistas,
                "buscar_politica": self.buscar_politica,
                "calcular_impacto": self.calcular_impacto,
            }
        elif agent == "ejecutor":
            return {
                "email_draft": self.email_draft,
                "task": self.task,
                "purchase_order_draft": self.purchase_order_draft,
                "price_change_draft": self.price_change_draft,
            }
        else:
            raise ValueError(f"Unknown agent: {agent}")
