"""Exercises the endpoints end to end against a real Postgres.

A day advance runs the agents in process only when LLM_MODEL is set; without it, it ends with no alerts.

Needs the Postgres from data/docker-compose.yml with data/sql/01..03 and
apps/api/sql/01_esquema.sql already applied, and DSN_ADMIN set.
"""
import os
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from centinela_api import alertas as alertas_repo
from centinela_api.db import conectar
from centinela_api.main import app
from centinela_api.modelos import Action, Alert, CauseNoEvidence, Confidence, Figure, Sentence

pytestmark = pytest.mark.integracion

DSN_ADMIN = os.environ.get("DSN_ADMIN")
if not DSN_ADMIN:
    pytest.skip("DSN_ADMIN not set", allow_module_level=True)

ID_ALERTA = "alerta_prueba_skeleton"
NOMBRE_GERENTE = "Ana Gómez"
CABECERAS_GERENTE = {"X-User-Name": quote(NOMBRE_GERENTE), "X-User-Role": "gerente"}


def _alerta_de_prueba() -> Alert:
    return Alert(
        id=ID_ALERTA,
        status="proposed",
        severity="high",
        metric="margen_pct",
        title=Sentence(text="Alerta de prueba", figures=[]),
        pesos_at_risk=Figure(value=5_000_000, unit="COP", query_id="q1"),
        recoverable_per_month=None,
        confidence=Confidence(level="medium", assumptions=[]),
        simulated_date="2026-01-01",
        cause=CauseNoEvidence(reason="no tengo evidencia suficiente", queries_reviewed=[]),
        actions=[
            Action(
                id="accion_prueba",
                title="Hacer algo",
                description=Sentence(text="Hace algo", figures=[]),
                type="task",
                impact=None,
                confidence=Confidence(level="medium", assumptions=[]),
                parameters={},
            )
        ],
    )


@pytest.fixture
def cliente():
    with conectar() as conn:
        alertas_repo.guardar(conn, _alerta_de_prueba())
        conn.commit()
    try:
        yield TestClient(app)
    finally:
        with conectar() as conn:
            conn.execute("DELETE FROM api.bitacora WHERE alerta_id = %s", (ID_ALERTA,))
            conn.execute("DELETE FROM api.alertas WHERE id = %s", (ID_ALERTA,))
            conn.commit()


def test_listar_filtra_por_estado(cliente):
    respuesta = cliente.get("/alertas", params={"estado": "propuesta"})
    assert respuesta.status_code == 200
    assert ID_ALERTA in [a["id"] for a in respuesta.json()]


def test_estado_desconocido_es_422(cliente):
    assert cliente.get("/alertas", params={"estado": "inventado"}).status_code == 422


def test_obtener_alerta(cliente):
    respuesta = cliente.get(f"/alertas/{ID_ALERTA}")
    assert respuesta.status_code == 200
    assert respuesta.json()["pesosAtRisk"]["value"] == 5_000_000


def test_obtener_alerta_inexistente(cliente):
    assert cliente.get("/alertas/no_existe").status_code == 404


def test_rol_sin_permiso_no_puede_decidir(cliente):
    respuesta = cliente.post(
        f"/alertas/{ID_ALERTA}/decision",
        json={"kind": "reject", "reason": "no aplica"},
        headers={"X-User-Name": "Ana", "X-User-Role": "lectura"},
    )
    assert respuesta.status_code == 403


def test_rechazar_sin_motivo_es_422(cliente):
    respuesta = cliente.post(
        f"/alertas/{ID_ALERTA}/decision",
        json={"kind": "reject", "reason": "  "},
        headers=CABECERAS_GERENTE,
    )
    assert respuesta.status_code == 422


def test_aprobar_mueve_el_estado_y_queda_en_la_bitacora(cliente):
    respuesta = cliente.post(
        f"/alertas/{ID_ALERTA}/decision",
        json={"kind": "approve", "actionId": "accion_prueba"},
        headers=CABECERAS_GERENTE,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "approved"

    eventos = cliente.get("/bitacora", params={"alertId": ID_ALERTA}).json()
    decision = next(e for e in eventos if e["type"] == "decision")
    assert decision["actor"] == {"kind": "person", "name": NOMBRE_GERENTE, "role": "gerente"}


def test_simulacion_avanzar_devuelve_el_evento_end():
    with TestClient(app) as cliente:
        with cliente.stream("POST", "/simulacion/avanzar", params={"dias": 1}) as respuesta:
            assert respuesta.status_code == 200
            texto = "".join(respuesta.iter_text())
    assert "event: end" in texto
