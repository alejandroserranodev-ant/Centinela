"""
Tests for tool implementations.

Validates that tools can be initialized, called, and return expected results.
"""

import pytest

from centinela_agents.action_tools import (
    EmailDraftStub,
    PriceChangeDraftStub,
    PurchaseOrderDraftStub,
    TaskStub,
)
from centinela_agents.buscar_politica import BuscarPoliticaStub
from centinela_agents.calcular_impacto import CalcularImpactoStub
from centinela_agents.sql_vistas import SqlVistasStub
from centinela_agents.tools import ToolRegistry


class TestSqlVistas:
    """Tests for SQL vistas tool."""

    def test_initialization(self):
        """SqlVistasStub can be initialized."""
        tool = SqlVistasStub()
        assert tool.query_counter == 0

    def test_query(self):
        """Query returns SqlQuery with queryId."""
        tool = SqlVistasStub()
        result = tool.query(
            view_name="v_cartera_cliente",
            filters={"cliente_id": "C123"},
            simulated_day="2026-10-03"
        )

        assert result.queryId.startswith("q_sql_")
        assert result.rows == []
        assert result.error is None

    def test_query_named(self):
        """Named query returns SqlQuery."""
        tool = SqlVistasStub()
        result = tool.query_by_name(
            query_name="q_dias_retraso",
            simulated_day="2026-10-03"
        )

        assert result.queryId.startswith("q_q_dias_retraso")
        assert result.rows == []

    def test_query_counter_increments(self):
        """Query counter increments."""
        tool = SqlVistasStub()
        tool.query("v_test1", {}, "2026-10-03")
        tool.query("v_test2", {}, "2026-10-03")

        assert tool.query_counter == 2


class TestBuscarPolitica:
    """Tests for policy search tool."""

    def test_initialization(self):
        """BuscarPoliticaStub can be initialized."""
        tool = BuscarPoliticaStub()
        assert "FIN-POL-004" in tool.policies

    def test_search_ranks_the_passages_that_share_words_with_the_query(self):
        tool = BuscarPoliticaStub()
        results = tool.search("límite de crédito", top_k=3)

        assert 0 < len(results) <= 3
        assert [r.relevance for r in results] == sorted((r.relevance for r in results), reverse=True)
        assert all(r.relevance > 0 for r in results)

    def test_search_by_code(self):
        """Search by policy code."""
        tool = BuscarPoliticaStub()
        results = tool.search_by_code("FIN-POL-004", "§3")

        assert isinstance(results, list)
        assert results == []

    def test_policies_loaded(self):
        """Policies are loaded in stub."""
        tool = BuscarPoliticaStub()
        assert len(tool.policies) >= 3
        assert "OPE-POL-007" in tool.policies


class TestCalcularImpacto:
    """Tests for impact calculator tool."""

    def test_initialization(self):
        """CalcularImpactoStub can be initialized."""
        tool = CalcularImpactoStub()
        assert tool.query_counter == 0
        assert len(tool.formulas) == 7

    def test_calculate_traslado_costo(self):
        """Calculate traslado_costo formula."""
        tool = CalcularImpactoStub()
        result = tool.calculate(
            formula_name="traslado_costo",
            entidad="SKU-123",
            simulated_day="2026-10-03"
        )

        assert result.formula == "traslado_costo"
        assert result.queryId.startswith("q_impacto_")
        assert result.error is None

    def test_calculate_cartera_vencida(self):
        """Calculate cartera_vencida formula."""
        tool = CalcularImpactoStub()
        result = tool.calculate(
            formula_name="cartera_vencida",
            entidad="cliente_456",
            simulated_day="2026-10-03"
        )

        assert result.formula == "cartera_vencida"
        assert result.unit == "COP"

    def test_calculate_unknown_formula(self):
        """Unknown formula returns error."""
        tool = CalcularImpactoStub()
        result = tool.calculate(
            formula_name="unknown_formula",
            entidad="X",
            simulated_day="2026-10-03"
        )

        assert result.error is not None
        assert "not found" in result.error

    def test_all_formulas_exist(self):
        """All 8 formulas (except dias_pago_prom) are defined."""
        tool = CalcularImpactoStub()
        expected = [
            "traslado_costo",
            "precio_a_margen_minimo",
            "cartera_vencida",
            "ventas_protegidas",
            "descuento_recuperado",
            "venta_bajo_costo",
            "compra_recuperada",
        ]

        for formula in expected:
            assert formula in tool.formulas


class TestEmailDraft:
    """Tests for email_draft tool."""

    def test_execute(self):
        """Create email draft."""
        tool = EmailDraftStub()
        result = tool.execute(
            recipient="cliente_123",
            body="Estimado cliente, su factura vence pronto.",
            subject="Recordatorio de pago"
        )

        assert result.draft_id.startswith("email_draft_")
        assert result.to == "cliente_123"
        assert "factura vence" in result.body

    def test_execute_without_subject(self):
        """Create email draft without explicit subject."""
        tool = EmailDraftStub()
        result = tool.execute(
            recipient="cliente_456",
            body="Contenido del email"
        )

        assert result.subject == "Centinela"
        assert result.draft_id is not None

    def test_draft_counter_increments(self):
        """Draft counter increments."""
        tool = EmailDraftStub()
        tool.execute("c1", "body1")
        tool.execute("c2", "body2")

        assert tool.draft_counter == 2


class TestTask:
    """Tests for task tool."""

    def test_execute(self):
        """Create task."""
        tool = TaskStub()
        result = tool.execute(
            owner="Jefe de cartera",
            title="Revisar cliente con retraso",
            description="Evaluar límite de crédito"
        )

        assert result.task_id.startswith("task_")
        assert result.owner == "Jefe de cartera"
        assert result.title == "Revisar cliente con retraso"

    def test_task_without_description(self):
        """Create task without description."""
        tool = TaskStub()
        result = tool.execute(
            owner="Comercial",
            title="Tarea"
        )

        assert result.task_id is not None
        assert result.description is None


class TestPurchaseOrderDraft:
    """Tests for purchase_order_draft tool."""

    def test_execute(self):
        """Create purchase order draft."""
        tool = PurchaseOrderDraftStub()
        result = tool.execute(
            proveedor_id="prov_123",
            sku="SKU-789",
            quantity=50,
            warehouse="bodega_01"
        )

        assert result.order_id.startswith("po_draft_")
        assert result.proveedor_id == "prov_123"
        assert result.sku == "SKU-789"
        assert result.quantity == 50

    def test_order_counter_increments(self):
        """Order counter increments."""
        tool = PurchaseOrderDraftStub()
        tool.execute("p1", "s1", 10, "b1")
        tool.execute("p2", "s2", 20, "b2")

        assert tool.order_counter == 2


class TestPriceChangeDraft:
    """Tests for price_change_draft tool."""

    def test_execute_sku_level(self):
        """Create price change draft for SKU."""
        tool = PriceChangeDraftStub()
        result = tool.execute(
            sku="SKU-123",
            price_increase_pct=2.5
        )

        assert result.change_id.startswith("price_draft_")
        assert result.sku == "SKU-123"
        assert result.price_increase_pct == 2.5

    def test_execute_line_level(self):
        """Create price change draft for line."""
        tool = PriceChangeDraftStub()
        result = tool.execute(
            linea="linea_456",
            price_increase_pct=3.0
        )

        assert result.linea == "linea_456"
        assert result.sku is None

    def test_execute_requires_percentage(self):
        """Price increase percentage is required."""
        tool = PriceChangeDraftStub()

        with pytest.raises(ValueError, match="price_increase_pct"):
            tool.execute(sku="SKU-123", price_increase_pct=None)


class TestToolRegistry:
    """Tests for tool registry."""

    def test_registry_initialization(self):
        """Registry can be initialized."""
        registry = ToolRegistry(
            sql_vistas=SqlVistasStub(),
            buscar_politica=BuscarPoliticaStub(),
            calcular_impacto=CalcularImpactoStub(),
            email_draft=EmailDraftStub(),
            task=TaskStub(),
        )

        assert registry.sql_vistas is not None

    def test_get_tools_for_vigia(self):
        """Vigía gets no tools."""
        registry = ToolRegistry(
            sql_vistas=SqlVistasStub(),
            calcular_impacto=CalcularImpactoStub(),
        )
        tools = registry.get_tools_for_agent("vigia")

        assert tools == {}

    def test_get_tools_for_chat(self):
        """The chat gets no tool: code reads the kernel, and no action is in its reach."""
        registry = ToolRegistry(sql_vistas=SqlVistasStub(), calcular_impacto=CalcularImpactoStub())

        assert registry.get_tools_for_agent("chat") == {}

    def test_get_tools_for_analista(self):
        """Analista gets sql_vistas and buscar_politica."""
        registry = ToolRegistry(
            sql_vistas=SqlVistasStub(),
            buscar_politica=BuscarPoliticaStub(),
        )
        tools = registry.get_tools_for_agent("analista")

        assert "sql_vistas" in tools
        assert "buscar_politica" in tools
        assert len(tools) == 2

    def test_get_tools_for_estratega(self):
        """Estratega gets sql, policy, and impact."""
        registry = ToolRegistry(
            sql_vistas=SqlVistasStub(),
            buscar_politica=BuscarPoliticaStub(),
            calcular_impacto=CalcularImpactoStub(),
        )
        tools = registry.get_tools_for_agent("estratega")

        assert "sql_vistas" in tools
        assert "buscar_politica" in tools
        assert "calcular_impacto" in tools
        assert len(tools) == 3

    def test_get_tools_for_ejecutor(self):
        """Ejecutor gets action tools."""
        registry = ToolRegistry(
            email_draft=EmailDraftStub(),
            task=TaskStub(),
            purchase_order_draft=PurchaseOrderDraftStub(),
            price_change_draft=PriceChangeDraftStub(),
        )
        tools = registry.get_tools_for_agent("ejecutor")

        assert "email_draft" in tools
        assert "task" in tools
        assert "purchase_order_draft" in tools
        assert "price_change_draft" in tools
        assert len(tools) == 4

    def test_unknown_agent_raises_error(self):
        """Unknown agent raises ValueError."""
        registry = ToolRegistry()

        with pytest.raises(ValueError, match="Unknown agent"):
            registry.get_tools_for_agent("unknown")
