import asyncio
import datetime as dt
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import db
from centinela_api.auth import persona_actual
from centinela_api.main import app
from centinela_api.modelos import Alert, AgentStep, Persona
from centinela_api.routers import simulacion as simulacion_router


def _eventos(cuerpo: str) -> list[tuple[str, dict]]:
    eventos = []
    for bloque in cuerpo.strip().split("\n\n"):
        lineas = dict(linea.split(": ", 1) for linea in bloque.splitlines())
        eventos.append((lineas["event"], json.loads(lineas["data"])))
    return eventos


@pytest.fixture
def conn():
    conn = MagicMock()

    def execute(query, *args, **kwargs):
        resultado = MagicMock()
        resultado.fetchone.return_value = (dt.date(2026, 1, 15),) if "dia_actual" in query or "fecha_corte" in query else None
        resultado.fetchall.return_value = []
        return resultado

    conn.execute.side_effect = execute
    return conn


@pytest.fixture
def cliente(conn, monkeypatch):
    orquestador = MagicMock()
    orquestador.start.side_effect = lambda detection, *, alert_id, day, **_: {
        "status": "propuesta",
        "transitions": [[alert_id, "nueva"], [alert_id, "en análisis"], [alert_id, "propuesta"]],
        "actions": [],
    }
    monkeypatch.setattr(simulacion_router, "get_orchestrator", lambda: orquestador)
    monkeypatch.setattr(simulacion_router.alertas_repo, "guardar", MagicMock(side_effect=lambda conn, alerta: alerta))
    monkeypatch.setattr(simulacion_router.bitacora, "registrar", MagicMock())

    def conexion():
        yield conn

    app.dependency_overrides[db.obtener_conexion] = conexion
    app.dependency_overrides[persona_actual] = lambda: Persona(email="analista@andina.test", name="Camila", role="analista")
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_el_dia_transmite_pasos_y_un_fin(cliente):
    respuesta = cliente.post("/simulacion/avanzar?dias=1")
    assert respuesta.status_code == 200
    eventos = _eventos(respuesta.text)
    nombres = [nombre for nombre, _ in eventos]
    assert nombres[-1] == "end"
    assert set(nombres[:-1]) == {"step", "alert"}
    for nombre, dato in eventos[:-1]:
        (AgentStep if nombre == "step" else Alert).model_validate(dato)
    assert eventos[-1][1]["newAlerts"]


def test_un_segundo_dia_en_curso_se_rechaza_con_409(cliente):
    asyncio.run(simulacion_router.day_run.acquire())
    try:
        respuesta = cliente.post("/simulacion/avanzar?dias=1")
    finally:
        simulacion_router.day_run.release()
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya hay un día en curso"
    assert not simulacion_router.day_run.locked()


def test_el_candado_se_libera_tras_un_dia(cliente):
    assert cliente.post("/simulacion/avanzar?dias=1").status_code == 200
    assert not simulacion_router.day_run.locked()
    assert cliente.post("/simulacion/avanzar?dias=1").status_code == 200


def test_el_candado_se_libera_tras_un_dia_que_falla(cliente, monkeypatch):
    monkeypatch.setattr(simulacion_router.simulacion, "avanzar", MagicMock(side_effect=RuntimeError("falla")))
    with pytest.raises(RuntimeError):
        cliente.post("/simulacion/avanzar?dias=1")
    assert not simulacion_router.day_run.locked()


def test_el_evento_alert_lleva_la_alerta_guardada(cliente):
    guardar = simulacion_router.alertas_repo.guardar
    eventos = _eventos(cliente.post("/simulacion/avanzar?dias=1").text)
    nombres = [nombre for nombre, _ in eventos]
    assert "alert" in nombres
    primera = nombres.index("alert")
    assert nombres[primera - 1] == "step" and nombres[primera + 1] == "step"
    guardada = guardar.call_args_list[0].args[1]
    dato = eventos[primera][1]
    Alert.model_validate(dato)
    assert dato["id"] == guardada.id
    assert dato == guardada.model_dump(by_alias=True, mode="json")
