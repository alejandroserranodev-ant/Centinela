import datetime as dt
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import ciclo_vida, db
from centinela_api.auth import persona_actual
from centinela_api.main import app
from centinela_api.modelos import Action, Alert, CauseNoEvidence, Confidence, Figure, Persona, Sentence
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
    app.dependency_overrides[persona_actual] = lambda: Persona(email="gerente@andina.test", name="Ana", role="gerente")
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
    )
    assert respuesta.status_code == 200
    assert [a.status for a in guardadas] == ["approved"]


def _accion_nueva() -> dict:
    return {"id": "accion_2", "title": "Llamar al cliente", "description": "Llama", "type": "task", "parameters": {}}


def _con_orquestador(monkeypatch, **configuracion):
    orquestador = MagicMock()
    orquestador.get_state.return_value = {"queries": [{"queryId": "q_vieja"}]}
    orquestador.resume.configure_mock(**configuracion)
    monkeypatch.setattr(alertas_router, "get_orchestrator", lambda: orquestador)
    return orquestador


def _pedir(motivo="Prefiero una llamada"):
    return TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "request_changes", "reason": motivo})


def test_pedir_cambios_reanuda_el_ciclo_y_guarda_las_acciones_nuevas(monkeypatch, guardadas):
    consulta = {"queryId": "q_nueva", "kpi": "saldo_vencido", "dia": "2026-01-15", "consulta": "SELECT 1"}
    orquestador = _con_orquestador(
        monkeypatch,
        return_value={"actions": [_accion_nueva()], "queries": [{"queryId": "q_vieja"}, consulta]},
    )
    registradas = MagicMock()
    monkeypatch.setattr(alertas_router.consultas, "registrar", registradas)
    respuesta = _pedir()
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "proposed" and cuerpo["changesRequested"] is True
    assert [a["id"] for a in cuerpo["actions"]] == ["accion_2"]
    asignado = orquestador.resume.call_args.args
    assert asignado[0] == "alerta_1"
    assert asignado[1]["kind"] == "request_changes" and asignado[1]["reason"] == "Prefiero una llamada"
    assert [a.actions[0].id for a in guardadas] == ["accion_1", "accion_2"]
    registradas.assert_called_once()
    assert [q["queryId"] for q in registradas.call_args.args[1]] == ["q_nueva"]


def test_pedir_cambios_una_segunda_vez_responde_409_sin_reanudar(monkeypatch, guardadas):
    orquestador = _con_orquestador(monkeypatch)
    monkeypatch.setattr(
        alertas_router.alertas_repo, "obtener",
        lambda conn, id: _alerta().model_copy(update={"changes_requested": True}),
    )
    respuesta = _pedir()
    assert respuesta.status_code == 409
    assert "Ya se pidieron cambios una vez" in respuesta.json()["detail"]
    orquestador.resume.assert_not_called()


def test_pedir_cambios_conserva_las_acciones_si_el_ciclo_falla(monkeypatch, guardadas):
    _con_orquestador(monkeypatch, side_effect=RuntimeError("sin modelo"))
    respuesta = _pedir()
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["changesRequested"] is True and [a["id"] for a in cuerpo["actions"]] == ["accion_1"]
    assert [a.changes_requested for a in guardadas] == [True]
    registro = alertas_router.bitacora.registrar.call_args_list[-1]
    assert registro.args[2] == "proposal" and "sin modelo" in registro.args[4]


def test_pedir_cambios_sin_acciones_nuevas_conserva_las_anteriores(monkeypatch, guardadas):
    _con_orquestador(monkeypatch, return_value={"actions": []})
    cuerpo = _pedir().json()
    assert [a["id"] for a in cuerpo["actions"]] == ["accion_1"]
