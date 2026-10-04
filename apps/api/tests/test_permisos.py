# Who decides an alert: the gerente any alert, a lider_proceso the alerts whose metric its area
# owns in packages/agents/skills/estratega/acciones.md, and no one else; checked pure and through
# POST /alertas/{id}/decision with a mocked connection.
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import db, permisos
from centinela_api.auth import persona_actual
from centinela_api.main import app
from centinela_api.modelos import Alert, CauseNoEvidence, Confidence, Figure, Persona, Sentence
from centinela_api.routers import alertas as alertas_router

GERENTE = Persona(email="gerente@andina.test", name="Mariana", role="gerente")
CARTERA = Persona(email="cartera@andina.test", name="Lucía", role="lider_proceso", area="Analista de cartera")
COMERCIAL = Persona(email="comercial@andina.test", name="Andrés", role="lider_proceso", area="Comercial")
ANALISTA = Persona(email="analista@andina.test", name="Camila", role="analista")
AUDITOR = Persona(email="auditoria@andina.test", name="Jorge", role="auditor")


def alerta(metric: str) -> Alert:
    return Alert(
        id=f"alerta_{metric}",
        status="proposed",
        severity="high",
        metric=metric,
        title=Sentence(text="La alerta", figures=[]),
        pesos_at_risk=Figure(value=1000, unit="COP", query_id="q1"),
        confidence=Confidence(level="medium"),
        simulated_date="2026-01-15",
        cause=CauseNoEvidence(reason="sin evidencia"),
        actions=[],
    )


def test_el_responsable_sale_de_la_tabla_de_estratega():
    assert permisos.responsable("saldo_vencido") == "Analista de cartera"
    assert permisos.responsable("margen_pct") == "Comercial"
    assert permisos.responsable("no_existe") is None


@pytest.mark.parametrize("metric", ["margen_pct", "saldo_vencido", "cobertura_dias", "descuento_en_exceso"])
def test_la_gerente_decide_cualquier_alerta(metric):
    assert permisos.puede_decidir(GERENTE, alerta(metric))


def test_un_lider_decide_solo_las_alertas_de_su_area():
    assert permisos.puede_decidir(CARTERA, alerta("saldo_vencido"))
    assert permisos.puede_decidir(CARTERA, alerta("dias_pago_prom"))
    assert not permisos.puede_decidir(CARTERA, alerta("margen_pct"))
    assert permisos.puede_decidir(COMERCIAL, alerta("margen_pct"))


@pytest.mark.parametrize("persona", [ANALISTA, AUDITOR])
def test_analista_y_auditor_no_deciden(persona):
    assert not permisos.puede_decidir(persona, alerta("saldo_vencido"))


def test_configuran_la_analista_y_la_gerente():
    assert permisos.puede_configurar(ANALISTA) and permisos.puede_configurar(GERENTE)
    assert not permisos.puede_configurar(CARTERA) and not permisos.puede_configurar(AUDITOR)


def test_la_vista_dice_quien_decide_y_si_esta_persona_puede():
    vista = permisos.vista(CARTERA, alerta("margen_pct"))
    assert (vista.decided_by, vista.can_decide) == ("Comercial", False)
    assert permisos.vista(CARTERA, alerta("saldo_vencido")).can_decide


@pytest.fixture
def decidir(monkeypatch):
    monkeypatch.setattr(alertas_router.alertas_repo, "obtener", lambda conn, id: alerta(id.removeprefix("alerta_")))
    monkeypatch.setattr(alertas_router.alertas_repo, "guardar", MagicMock())
    monkeypatch.setattr(alertas_router.bitacora, "registrar", MagicMock())
    monkeypatch.setattr(alertas_router.simulacion, "dia_actual", MagicMock())
    monkeypatch.setattr(alertas_router, "get_orchestrator", MagicMock)

    def conexion():
        yield MagicMock()

    app.dependency_overrides[db.obtener_conexion] = conexion

    def como(persona: Persona, metric: str):
        app.dependency_overrides[persona_actual] = lambda: persona
        return TestClient(app).post(f"/alertas/alerta_{metric}/decision", json={"kind": "reject", "reason": "no aplica"})

    yield como
    app.dependency_overrides.clear()


def test_cartera_decide_saldo_vencido_y_recibe_403_en_margen(decidir):
    assert decidir(CARTERA, "saldo_vencido").status_code == 200
    negada = decidir(CARTERA, "margen_pct")
    assert negada.status_code == 403
    assert negada.json() == {"detail": "Esta alerta la decide Comercial"}


@pytest.mark.parametrize("persona", [ANALISTA, AUDITOR])
def test_analista_y_auditor_reciben_403(decidir, persona):
    assert decidir(persona, "saldo_vencido").status_code == 403


def test_la_gerente_decide_y_la_respuesta_lo_dice(decidir):
    respuesta = decidir(GERENTE, "margen_pct")
    assert respuesta.status_code == 200
    assert (respuesta.json()["decidedBy"], respuesta.json()["canDecide"]) == ("Comercial", True)


def test_una_metrica_sin_area_la_decide_la_gerencia(monkeypatch):
    monkeypatch.setattr(permisos, "responsable", lambda metric: None)
    assert permisos.negada(alerta("margen_pct")) == "Esta alerta la decide la gerencia"
    assert permisos.vista(CARTERA, alerta("margen_pct")).decided_by == "Gerencia"
    assert not permisos.puede_decidir(CARTERA, alerta("margen_pct"))
