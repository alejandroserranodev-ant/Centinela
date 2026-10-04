"""
Tests for agent output schemas (Cause, Action, ExecutedAction, Decision).

Validates that schemas can be serialized to JSON, parsed from JSON,
and work correctly with LLM provider structured output.
"""

import json

import pytest
from pydantic import ValidationError

from centinela_agents.schema import (
    Action,
    Cause,
    CauseIdentified,
    CauseNoEvidence,
    Confidence,
    Decision,
    Evidence,
    ExecutedAction,
    Figure,
    InsufficientCause,
    RejectionClassifierOutput,
)


class TestFigure:
    """Tests for Figure schema."""

    def test_figure_with_all_fields(self):
        """Figure can be created with value, unit, and queryId."""
        fig = Figure(value=45.5, unit="COP", queryId="query_001")
        assert fig.value == 45.5
        assert fig.unit == "COP"
        assert fig.queryId == "query_001"

    def test_figure_without_unit(self):
        """Figure can be created without unit (dimensionless)."""
        fig = Figure(value=3, unit=None, queryId="q_002")
        assert fig.value == 3
        assert fig.unit is None

    def test_figure_string_value(self):
        """Figure can have string value."""
        fig = Figure(value="SKU-12345", unit=None, queryId="q_003")
        assert fig.value == "SKU-12345"

    def test_figure_serializes_to_json(self):
        """Figure can be serialized to JSON."""
        fig = Figure(value=100, unit="days", queryId="q_time")
        json_str = fig.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["value"] == 100
        assert parsed["unit"] == "days"
        assert parsed["queryId"] == "q_time"

    def test_figure_deserializes_from_json(self):
        """Figure can be deserialized from JSON."""
        json_str = '{"value": 50, "unit": "%", "queryId": "q_pct"}'
        fig = Figure.model_validate_json(json_str)
        assert fig.value == 50
        assert fig.unit == "%"

    def test_figure_rejects_missing_queryId(self):
        """Figure requires queryId."""
        with pytest.raises(ValidationError):
            Figure(value=100, unit="COP")


class TestEvidence:
    """Tests for Evidence schema."""

    def test_evidence_with_claim_and_figures(self):
        """Evidence contains a claim and supporting figures."""
        fig = Figure(value=30, unit="days", queryId="q_dias")
        evidence = Evidence(claim="El cliente tiene {0} de retraso", figures=[fig])
        assert evidence.claim == "El cliente tiene {0} de retraso"
        assert len(evidence.figures) == 1
        assert evidence.figures[0].value == 30

    def test_evidence_without_figures(self):
        """Evidence can be created without figures (for text-only claims)."""
        evidence = Evidence(claim="Solo texto sin figura")
        assert evidence.figures == []

    def test_evidence_serializes(self):
        """Evidence serializes to JSON correctly."""
        fig = Figure(value=100000, unit="COP", queryId="q_saldo")
        evidence = Evidence(
            claim="Saldo vencido de {0}",
            figures=[fig]
        )
        json_str = evidence.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["claim"] == "Saldo vencido de {0}"
        assert len(parsed["figures"]) == 1


class TestCauseIdentified:
    """Tests for identified Cause."""

    def test_cause_identified_basic(self):
        """Create a Cause with kind=identified."""
        fig = Figure(value=45, unit="days", queryId="q_dias")
        evidence = Evidence(claim="Retraso de {0}", figures=[fig])
        confidence = Confidence(level="high", assumptions=[])

        cause = CauseIdentified(
            kind="identified",
            sentence="El cliente acumula retraso en pagos.",
            evidence=[evidence]
        )

        assert cause.kind == "identified"
        assert cause.sentence == "El cliente acumula retraso en pagos."
        assert len(cause.evidence) == 1
        assert cause.same_cause_as is None

    def test_cause_identified_with_merged_alert(self):
        """Cause can reference another alert with same cause."""
        fig = Figure(value=20, unit="COP", queryId="q_cost")
        evidence = Evidence(claim="Costo subió {0}", figures=[fig])
        confidence = Confidence(level="medium", assumptions=["sin data histórica"])

        cause = CauseIdentified(
            kind="identified",
            sentence="Aumento en costo de materiales.",
            evidence=[evidence],
            same_cause_as="alert_id_123"
        )

        assert cause.same_cause_as == "alert_id_123"

    def test_cause_identified_serializes(self):
        """Cause identified serializes to valid JSON for LLM output."""
        fig = Figure(value=15, unit="%", queryId="q_pct")
        evidence = Evidence(claim="Margen cayó {0}", figures=[fig])
        confidence = Confidence(level="low", assumptions=["dato parcial"])

        cause = CauseIdentified(
            kind="identified",
            sentence="Margen bajo por descuento.",
            evidence=[evidence]
        )

        json_str = cause.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["kind"] == "identified"
        assert parsed["sentence"] == "Margen bajo por descuento."
        assert len(parsed["evidence"]) == 1


class TestCauseNoEvidence:
    """Tests for no_evidence Cause."""

    def test_cause_no_evidence(self):
        """Create a Cause with kind=no_evidence."""
        cause = CauseNoEvidence(
            kind="no_evidence",
            reason="No se encontraron cambios en los datos que expliquen el síntoma.",
            queriesReviewed=["q_ventas", "q_clientes", "q_comportamiento"]
        )

        assert cause.kind == "no_evidence"
        assert "No se encontraron cambios" in cause.reason
        assert len(cause.queriesReviewed) == 3

    def test_cause_no_evidence_serializes(self):
        """No evidence cause serializes correctly."""
        cause = CauseNoEvidence(
            kind="no_evidence",
            reason="Datos insuficientes.",
            queriesReviewed=["q1"]
        )

        json_str = cause.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["kind"] == "no_evidence"


class TestConfidence:
    """Tests for Confidence schema."""

    def test_confidence_high(self):
        """High confidence with two views."""
        conf = Confidence(
            level="high",
            assumptions=["Datos de último mes completo"]
        )
        assert conf.level == "high"
        assert len(conf.assumptions) == 1

    def test_confidence_low_without_assumptions(self):
        """Confidence can be created without assumptions."""
        conf = Confidence(level="low")
        assert conf.level == "low"
        assert conf.assumptions == []


class TestAction:
    """Tests for Action schema."""

    def test_action_email_draft(self):
        """Action for email_draft type."""
        impact = Figure(value=100000, unit="COP", queryId="q_cartera")
        confidence = Confidence(level="high")

        action = Action(
            id="action_001",
            title="Enviar cobro al cliente",
            description="Recordatorio de pago según FIN-POL-004 §4",
            type="email_draft",
            parameters={"recipient": "cliente_123", "vendedor_id": "vendedor_45"},
            impact=impact,
            confidence=confidence
        )

        assert action.type == "email_draft"
        assert action.parameters["recipient"] == "cliente_123"
        assert action.impact.value == 100000

    def test_action_task(self):
        """Action for task type (manual review)."""
        confidence = Confidence(level="medium", assumptions=["Requiere revisión manual"])

        action = Action(
            id="action_002",
            title="Revisar límite de crédito",
            description="Evaluar aumento según FIN-POL-004 §3",
            type="task",
            parameters={"owner": "Jefe de cartera", "cliente_id": "cliente_456"},
            impact=None,
            confidence=confidence
        )

        assert action.type == "task"
        assert action.impact is None

    def test_action_price_change_draft(self):
        """Action for price change."""
        impact = Figure(value=2.5, unit="%", queryId="q_precio")
        confidence = Confidence(level="high")

        action = Action(
            id="action_003",
            title="Ajustar precio del SKU",
            description="Traslado de costo según OPE-POL-007 §4",
            type="price_change_draft",
            parameters={"sku": "SKU-789", "price_increase_pct": 2.5},
            impact=impact,
            confidence=confidence
        )

        assert action.type == "price_change_draft"
        assert action.parameters["sku"] == "SKU-789"

    def test_action_serializes(self):
        """Action serializes to valid JSON for LLM output."""
        impact = Figure(value=500000, unit="COP", queryId="q_impact")
        confidence = Confidence(level="high")

        action = Action(
            id="a_001",
            title="Acción de prueba",
            description="Descripción de acción",
            type="email_draft",
            parameters={"client": "test"},
            impact=impact,
            confidence=confidence
        )

        json_str = action.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "email_draft"
        assert parsed["impact"]["value"] == 500000


class TestExecutedAction:
    """Tests for ExecutedAction schema."""

    def test_executed_action_email_draft(self):
        """Executed email draft action."""
        action = ExecutedAction(
            actionId="action_001",
            type="email_draft",
            result="Estimado cliente,\n\nSu factura tiene 30 días de vencida...",
            parameters={"recipient": "cliente_123"}
        )

        assert action.type == "email_draft"
        assert "30 días de vencida" in action.result

    def test_executed_action_task(self):
        """Executed task action."""
        action = ExecutedAction(
            actionId="action_002",
            type="task",
            result={"task_id": "TASK-999", "owner": "Jefe de cartera"},
            parameters={"owner": "Jefe de cartera"}
        )

        assert action.type == "task"
        assert isinstance(action.result, dict)
        assert action.result["task_id"] == "TASK-999"

    def test_executed_action_nota_manual(self):
        """Manual note action."""
        action = ExecutedAction(
            actionId="manual_001",
            type="nota_manual",
            result="Nota: Requiere seguimiento personal.",
            parameters={"owner": "supervisor"}
        )

        assert action.type == "nota_manual"


class TestDecision:
    """Tests for Decision schema."""

    def test_decision_approve(self):
        """Decision to approve an action."""
        decision = Decision(
            kind="approve",
            actionId="action_001"
        )

        assert decision.kind == "approve"
        assert decision.actionId == "action_001"
        assert decision.parameters is None
        assert decision.reason is None

    def test_decision_edit(self):
        """Decision to edit an action's parameters."""
        decision = Decision(
            kind="edit",
            actionId="action_002",
            parameters={"price_increase_pct": 3.0}
        )

        assert decision.kind == "edit"
        assert decision.parameters["price_increase_pct"] == 3.0

    def test_decision_reject(self):
        """Decision to reject an alert."""
        decision = Decision(
            kind="reject",
            reason="Los datos no son confiables. Requiere revisión del origen."
        )

        assert decision.kind == "reject"
        assert "no son confiables" in decision.reason

    def test_decision_request_changes(self):
        """Decision to request changes to proposal."""
        decision = Decision(
            kind="request_changes",
            reason="Por favor, proponer descuento en lugar de precio fijo."
        )

        assert decision.kind == "request_changes"
        assert "descuento" in decision.reason


class TestRejectionClassifier:
    """Tests for rejection classifier output."""

    def test_classifier_causa(self):
        """Route rejection to Analista (cause)."""
        output = RejectionClassifierOutput(destino="causa")
        assert output.destino == "causa"

    def test_classifier_propuesta(self):
        """Route rejection to Estratega (proposal)."""
        output = RejectionClassifierOutput(destino="propuesta")
        assert output.destino == "propuesta"

    def test_classifier_ambos(self):
        """Route rejection to both agents."""
        output = RejectionClassifierOutput(destino="ambos")
        assert output.destino == "ambos"

    def test_classifier_ninguno(self):
        """Keep rejection reason in log, no agent action."""
        output = RejectionClassifierOutput(destino="ninguno")
        assert output.destino == "ninguno"

    def test_classifier_serializes(self):
        """Classifier output serializes correctly."""
        output = RejectionClassifierOutput(destino="propuesta")
        json_str = output.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["destino"] == "propuesta"


class TestInsufficientCause:
    """Tests for insufficient cause fallback."""

    def test_insufficient_cause(self):
        """Estratega falls back to insufficient_cause."""
        fallback = InsufficientCause()
        assert fallback.insufficient_cause is True


class TestSchemaIntegration:
    """Integration tests: full workflows with multiple schemas."""

    def test_cause_to_action_flow(self):
        """Analista produces Cause, Estratega produces Action."""
        fig_cause = Figure(value=30, unit="days", queryId="q_dias_retraso")
        evidence = Evidence(
            claim="El cliente acumula {0} sin pagar",
            figures=[fig_cause]
        )
        confidence = Confidence(level="high", assumptions=[])
        cause = CauseIdentified(
            kind="identified",
            sentence="Retraso en pagos del cliente.",
            evidence=[evidence]
        )

        fig_action = Figure(value=100000, unit="COP", queryId="q_saldo_vencido")
        action_conf = Confidence(level="high")
        action = Action(
            id="action_pay_reminder",
            title="Recordatorio de pago",
            description="Email según FIN-POL-004 §4",
            type="email_draft",
            parameters={"recipient": "cliente_123", "vendedor_id": "vendedor_001"},
            impact=fig_action,
            confidence=action_conf
        )

        cause_json = cause.model_dump_json()
        action_json = action.model_dump_json()

        cause_parsed = CauseIdentified.model_validate_json(cause_json)
        action_parsed = Action.model_validate_json(action_json)

        assert cause_parsed.sentence == cause.sentence
        assert action_parsed.type == action.type

    def test_action_to_execution_flow(self):
        """Estratega produces Action, Ejecutor produces ExecutedAction."""
        conf = Confidence(level="medium")
        action = Action(
            id="draft_001",
            title="Borrador de email",
            description="Envío a cliente",
            type="email_draft",
            parameters={"recipient": "cliente_X"},
            impact=None,
            confidence=conf
        )

        decision = Decision(
            kind="approve",
            actionId="draft_001"
        )

        executed = ExecutedAction(
            actionId="draft_001",
            type="email_draft",
            result="Estimado cliente,\n\nSu cuenta tiene pendientes...",
            parameters={"recipient": "cliente_X"}
        )

        action_json = action.model_dump_json()
        decision_json = decision.model_dump_json()
        executed_json = executed.model_dump_json()

        assert json.loads(action_json)["id"] == "draft_001"
        assert json.loads(decision_json)["actionId"] == "draft_001"
        assert json.loads(executed_json)["actionId"] == "draft_001"
