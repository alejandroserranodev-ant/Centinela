import datetime as dt
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import ciclo_vida, db
from centinela_api.main import app
from centinela_api.modelos import Action, Alert, CauseNoEvidence, Confidence, Figure, Sentence
from centinela_api.routers import alertas as alertas_router
from centinela_api.routers import simulacion as simulacion_router

DIA = dt.date(2026, 1, 15)


def _alerta() -> Alert:
    return Alert(
        id="alerta_1",
        status="proposed",
        severity="high",
        metric="saldo_vencido",
        title=Sentence(text="La alerta", figures=[]),
        pesos_at_risk=Figure(value=1000, unit="COP", query_id="q1"),
        recoverable_per_month=None,
        confidence=Confidence(level="medium", assumptions=[]),
        simulated_date="2026-01-15",
        cause=CauseNoEvidence(reason="sin evidencia", queries_reviewed=[]),
        actions=[Action(id="accion_1", title="Hacer algo", description=Sentence(text="Hace algo", figures=[]), type="task", impact=None, confidence=Confidence(level="medium"), parameters={})],
    )


@pytest.fixture
def guardadas(monkeypatch):
    guardadas: list[Alert] = []
    for modulo in (simulacion_router, alertas_router):
        monkeypatch.setattr(modulo.alertas_repo, "guardar", lambda conn, alerta: guardadas.append(alerta))
        monkeypatch.setattr(modulo.bitacora, "registrar", MagicMock())
        monkeypatch.setattr(modulo.simulacion, "dia_actual", lambda conn: DIA)
    monkeypatch.setattr(simulacion_router.simulacion, "avanzar", lambda conn, dias: DIA)
    monkeypatch.setattr(alertas_router.alertas_repo, "obtener", lambda conn, id: _alerta())

    def conexion():
        yield MagicMock()

    app.dependency_overrides[db.obtener_conexion] = conexion
    yield guardadas
    app.dependency_overrides.clear()


def _orquestador_que_recorre(monkeypatch, *estados):
    orquestador = MagicMock()

    def start(detection, *, alert_id, day):
        return {"status": estados[-1], "transitions": [[alert_id, e] for e in estados], "actions": []}

    orquestador.start.side_effect = start
    monkeypatch.setattr(simulacion_router, "get_orchestrator", lambda: orquestador)


def test_avanzar_guarda_una_alerta_que_recorre_el_ciclo(monkeypatch, guardadas):
    _orquestador_que_recorre(monkeypatch, "nueva", "en análisis", "propuesta")
    TestClient(app).post("/simulacion/avanzar")
    assert guardadas and all(a.status == "proposed" for a in guardadas)


def test_avanzar_no_guarda_una_alerta_que_salta_un_estado(monkeypatch, guardadas):
    _orquestador_que_recorre(monkeypatch, "nueva", "propuesta")
    respuesta = TestClient(app).post("/simulacion/avanzar")
    assert guardadas == []
    assert '"newAlerts": []' in respuesta.text


def test_el_resume_no_escribe_ejecutada_si_el_ciclo_la_rechaza(monkeypatch, guardadas):
    orquestador = MagicMock()
    orquestador.resume.return_value = {"executed_action": {"actionId": "accion_1", "result": "Tarea creada"}}
    monkeypatch.setattr(alertas_router, "get_orchestrator", lambda: orquestador)
    monkeypatch.setitem(ciclo_vida.TRANSICIONES, "approved", frozenset())
    respuesta = TestClient(app).post(
        "/alertas/alerta_1/decision",
        json={"kind": "approve", "actionId": "accion_1"},
        headers={"X-User-Name": "Ana", "X-User-Role": "gerente"},
    )
    assert respuesta.status_code == 200
    assert [a.status for a in guardadas] == ["approved"]
