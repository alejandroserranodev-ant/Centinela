# The endpoints of the tree's expansions: the list, newest first, and the retirement with each of
# its refusals and the Spanish each one shows, and the session both ask for, over a mocked store
# and connection.
import datetime as dt
from unittest.mock import ANY, MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import db
from centinela_api.auth import persona_actual
from centinela_api.main import app
from centinela_api.modelos import Persona, TreeExpansion
from centinela_api.routers import arbol as arbol_router

GERENTE = Persona(email="gerente@andina.test", name="Ana", role="gerente")
AUDITOR = Persona(email="auditoria@andina.test", name="Jorge", role="auditor")
EXPANSION = TreeExpansion(id="2", agent="estratega", simulated_date="2026-01-15", created_at="2026-10-04T12:00:00+00:00", description="Deja de proponer", evidence=[], status="active")


@pytest.fixture
def con(monkeypatch):
    monkeypatch.setattr(arbol_router.arboles, "versiones", lambda conn: [])
    monkeypatch.setattr(arbol_router.arboles, "expansiones", lambda filas, titulos: [EXPANSION])
    monkeypatch.setattr(arbol_router.alertas_repo, "listar", lambda conn, status: [])
    monkeypatch.setattr(arbol_router.simulacion, "dia_actual", lambda conn: dt.date(2026, 1, 15))

    def conexion():
        yield MagicMock()

    def como(persona):
        app.dependency_overrides[persona_actual] = lambda: persona
        return TestClient(app)

    app.dependency_overrides[db.obtener_conexion] = conexion
    yield como
    app.dependency_overrides.clear()


def test_sin_sesion_las_rutas_del_arbol_responden_401(con):
    cliente = TestClient(app)
    assert cliente.get("/arbol/expansiones").status_code == 401
    assert cliente.post("/arbol/expansiones/2/retiro", json={"reason": "No ayudó"}).status_code == 401


def test_la_lista_sirve_las_expansiones(con):
    assert con(AUDITOR).get("/arbol/expansiones").json()[0]["id"] == "2"


def test_retirar_devuelve_la_expansion_retirada(con, monkeypatch):
    retirar = MagicMock(return_value=EXPANSION.model_copy(update={"status": "retired", "retired_by": "Ana", "retire_reason": "No ayudó"}))
    monkeypatch.setattr(arbol_router.arboles, "retirar", retirar)
    respuesta = con(GERENTE).post("/arbol/expansiones/2/retiro", json={"reason": "No ayudó"})
    assert respuesta.status_code == 200 and respuesta.json()["status"] == "retired"
    retirar.assert_called_once_with(ANY, 2, "No ayudó", GERENTE, dt.date(2026, 1, 15), {})


@pytest.mark.parametrize(
    "persona, cuerpo, error, estado",
    [
        (AUDITOR, {"reason": "No ayudó"}, None, 403),
        (GERENTE, {"reason": "  "}, None, 422),
        (GERENTE, {"reason": "No ayudó"}, arbol_router.arboles.ExpansionDesconocida(2), 404),
        (GERENTE, {"reason": "No ayudó"}, arbol_router.arboles.YaRetirada(2), 409),
        (GERENTE, {"reason": "No ayudó"}, arbol_router.arboles.RetiroRechazado(["metric x has no L3 branch in detectar"]), 422),
        (GERENTE, {"reason": "No ayudó"}, arbol_router.arboles.YaNoAplica(2), 422),
    ],
    ids=["auditor", "no reason", "unknown", "already retired", "refused", "inactive"],
)
def test_retirar_rechaza(con, monkeypatch, persona, cuerpo, error, estado):
    monkeypatch.setattr(arbol_router.arboles, "retirar", MagicMock(side_effect=error))
    assert con(persona).post("/arbol/expansiones/2/retiro", json=cuerpo).status_code == estado


@pytest.mark.parametrize(
    "error, detalle",
    [
        (arbol_router.arboles.YaNoAplica(2), arbol_router.YA_NO_APLICA),
        (arbol_router.arboles.RetiroRechazado(["metric x has no L3 branch in detectar"]), arbol_router.NO_ADMITE),
    ],
    ids=["inactive", "refused"],
)
def test_un_retiro_rechazado_se_explica_en_castellano(con, monkeypatch, error, detalle):
    monkeypatch.setattr(arbol_router.arboles, "retirar", MagicMock(side_effect=error))
    assert con(GERENTE).post("/arbol/expansiones/2/retiro", json={"reason": "No ayudó"}).json()["detail"] == detalle
