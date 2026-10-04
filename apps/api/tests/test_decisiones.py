import pytest

from centinela_api.decisiones import SOLO_INFORMA, ConflictoEstado, DecisionInvalida, aplicar
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


PROPONE = {"email_draft": "propose", "task": "propose", "purchase_order_draft": "propose", "price_change_draft": "propose"}
INFORMA_TAREAS = {**PROPONE, "task": "inform"}


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
    alerta, eventos = aplicar(_alerta(), DecisionApprove(action_id="accion_1"), PROPONE)
    assert alerta.status == "approved"
    assert eventos == [("decision", "Aprobada: Hacer algo")]


def test_editar_aplica_parametros_a_la_accion_elegida():
    alerta, _ = aplicar(_alerta(), DecisionEdit(action_id="accion_1", parameters={"precio": 1}), PROPONE)
    assert alerta.actions[0].parameters["precio"] == 1


def test_rechazar_requiere_motivo():
    with pytest.raises(DecisionInvalida):
        aplicar(_alerta(), DecisionReject(reason="   "), PROPONE)


def test_rechazar_mueve_a_rejected():
    alerta, eventos = aplicar(_alerta(), DecisionReject(reason="no aplica"), PROPONE)
    assert alerta.status == "rejected"
    assert eventos == [("decision", "Rechazada. Motivo: no aplica")]


def test_decision_sobre_alerta_que_no_espera_una():
    with pytest.raises(ConflictoEstado):
        aplicar(_alerta(status="new"), DecisionReject(reason="motivo"), PROPONE)


def test_accion_desconocida_es_rechazada():
    with pytest.raises(DecisionInvalida):
        aplicar(_alerta(), DecisionApprove(action_id="no_existe"), PROPONE)


@pytest.mark.parametrize("decision", [DecisionApprove(action_id="accion_1"), DecisionEdit(action_id="accion_1", parameters={"precio": 1})])
def test_una_accion_que_solo_informa_no_se_aprueba(decision):
    with pytest.raises(DecisionInvalida, match=SOLO_INFORMA):
        aplicar(_alerta(), decision, INFORMA_TAREAS)


def test_una_accion_que_solo_informa_se_puede_rechazar():
    alerta, _ = aplicar(_alerta(), DecisionReject(reason="no aplica"), INFORMA_TAREAS)
    assert alerta.status == "rejected"
