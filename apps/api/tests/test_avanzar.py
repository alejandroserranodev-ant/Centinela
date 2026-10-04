import datetime as dt
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import db
from centinela_api.main import app
from centinela_api.modelos import AgentStep
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
    orquestador.start.side_effect = lambda detection, *, alert_id, day: {
        "status": "propuesta",
        "transitions": [[alert_id, "nueva"], [alert_id, "en análisis"], [alert_id, "propuesta"]],
        "actions": [],
    }
    monkeypatch.setattr(simulacion_router, "get_orchestrator", lambda: orquestador)
    monkeypatch.setattr(simulacion_router.alertas_repo, "guardar", MagicMock())
    monkeypatch.setattr(simulacion_router.bitacora, "registrar", MagicMock())

    def conexion():
        yield conn

    app.dependency_overrides[db.obtener_conexion] = conexion
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_el_dia_transmite_pasos_y_un_fin(cliente):
    respuesta = cliente.post("/simulacion/avanzar?dias=1")
    assert respuesta.status_code == 200
    eventos = _eventos(respuesta.text)
    nombres = [nombre for nombre, _ in eventos]
    assert nombres[-1] == "end"
    assert set(nombres[:-1]) == {"step"}
    for _, dato in eventos[:-1]:
        AgentStep.model_validate(dato)
    assert eventos[-1][1]["newAlerts"]
