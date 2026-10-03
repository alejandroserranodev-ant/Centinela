import pytest

from centinela_api.decisiones import ConflictoEstado, DecisionInvalida, aplicar
from centinela_api.modelos import (
    Action,
    Alert,
    AlertStatus,
    CauseNoEvidence,
    Confidence,
    DecisionApprove,
    DecisionEdit,
    DecisionReject,
    Figure,
    Sentence,
)


def _alerta(status: AlertStatus = "proposed") -> Alert:
    return Alert(
        id="alerta_1",
        status=status,
        severity="high",
        metric="margen_pct",
        title=Sentence(text="La alerta", figures=[]),
        pesos_at_risk=Figure(value=1000, unit="COP", query_id="q1"),
        recoverable_per_month=None,
        confidence=Confidence(level="medium", assumptions=[]),
        simulated_date="2026-01-01",
        cause=CauseNoEvidence(reason="no tengo evidencia suficiente", queries_reviewed=[]),
        actions=[
            Action(
                id="accion_1",
                title="Hacer algo",
                description=Sentence(text="Hace algo", figures=[]),
                type="task",
                impact=None,
                confidence=Confidence(level="medium", assumptions=[]),
                parameters={},
            )
        ],
    )


def test_aprobar_mueve_a_approved():
    alerta, eventos = aplicar(_alerta(), DecisionApprove(action_id="accion_1"))
    assert alerta.status == "approved"
    assert eventos == [("decision", "Aprobada: Hacer algo")]


def test_editar_aplica_parametros_a_la_accion_elegida():
    alerta, _ = aplicar(_alerta(), DecisionEdit(action_id="accion_1", parameters={"precio": 1}))
    assert alerta.actions[0].parameters["precio"] == 1


def test_rechazar_requiere_motivo():
    with pytest.raises(DecisionInvalida):
        aplicar(_alerta(), DecisionReject(reason="   "))


def test_rechazar_mueve_a_rejected():
    alerta, eventos = aplicar(_alerta(), DecisionReject(reason="no aplica"))
    assert alerta.status == "rejected"
    assert eventos == [("decision", "Rechazada. Motivo: no aplica")]


def test_decision_sobre_alerta_que_no_espera_una():
    with pytest.raises(ConflictoEstado):
        aplicar(_alerta(status="new"), DecisionReject(reason="motivo"))


def test_accion_desconocida_es_rechazada():
    with pytest.raises(DecisionInvalida):
        aplicar(_alerta(), DecisionApprove(action_id="no_existe"))
