"""Exercises the endpoints end to end against a real Postgres, signed in through /auth/login
with the demo profiles of the root .env.

A day advance runs the agents in process only when LLM_MODEL is set; without it, it ends with no alerts.

Needs the Postgres from data/docker-compose.yml with data/sql/01..03 and
apps/api/sql/01_esquema.sql already applied; it skips itself when DSN_ADMIN reaches no database.
"""
import json
import os

import psycopg
import pytest
import requests
from fastapi.testclient import TestClient

from centinela_api import alertas as alertas_repo
from centinela_api.db import conectar
from centinela_api.main import app
from centinela_api.modelos import Action, Alert, CauseNoEvidence, Confidence, Figure, Sentence

pytestmark = pytest.mark.integracion

DSN_ADMIN = os.environ.get("DSN_ADMIN")
try:
    psycopg.connect(DSN_ADMIN or "", connect_timeout=2).close()
except psycopg.OperationalError:
    pytest.skip("DSN_ADMIN reaches no database", allow_module_level=True)

ID_ALERTA = "alerta_prueba_skeleton"
CLAVE_DEMO = "Andina2026!"
NOMBRE_GERENTE = "Mariana Restrepo"


def _cabeceras(correo: str) -> dict[str, str]:
    respuesta = TestClient(app).post("/auth/login", json={"email": correo, "password": CLAVE_DEMO})
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['token']}"}


CABECERAS_GERENTE = _cabeceras("gerente@andina.test")


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
        yield TestClient(app, headers=CABECERAS_GERENTE)
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
    assert (respuesta.json()["decidedBy"], respuesta.json()["canDecide"]) == ("Comercial", True)


def test_obtener_alerta_inexistente(cliente):
    assert cliente.get("/alertas/no_existe").status_code == 404


def test_rol_sin_permiso_no_puede_decidir(cliente):
    respuesta = cliente.post(
        f"/alertas/{ID_ALERTA}/decision",
        json={"kind": "reject", "reason": "no aplica"},
        headers=_cabeceras("auditoria@andina.test"),
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "Esta alerta la decide Comercial"


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


def test_simulacion_avanzar_devuelve_el_evento_end(monkeypatch):
    monkeypatch.setenv("CENTINELA_ALERTAS_POR_DIA", "0")
    with TestClient(app, headers=CABECERAS_GERENTE) as cliente:
        with cliente.stream("POST", "/simulacion/avanzar", params={"dias": 1}) as respuesta:
            assert respuesta.status_code == 200
            texto = "".join(respuesta.iter_text())
    assert "event: end" in texto


def _modelo_responde() -> bool:
    if os.environ.get("LLM_PROVIDER", "ollama") == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    try:
        requests.get(f"{os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')}/api/tags", timeout=2).raise_for_status()
    except requests.RequestException:
        return False
    return bool(os.environ.get("LLM_MODEL"))


def _evento_end(texto: str) -> dict:
    bloque = next(b for b in texto.split("\n\n") if b.startswith("event: end"))
    return json.loads(bloque.split("data: ", 1)[1])


def _query_ids(alerta: dict) -> set[str]:
    figuras = [*alerta["title"]["figures"], alerta["pesosAtRisk"]]
    if alerta["cause"]["kind"] == "identified":
        figuras += alerta["cause"]["sentence"]["figures"]
        figuras += [f for e in alerta["cause"]["evidence"] for f in e["claim"]["figures"]]
    figuras += [a["impact"]["figure"] for a in alerta["actions"] if a["impact"]]
    return {f["queryId"] for f in figuras}


@pytest.mark.skipif(not _modelo_responde(), reason="the model provider of the root .env is unusable")
def test_un_dia_real_cita_el_kernel_y_aprobar_ejecuta_y_rechazar_clasifica(monkeypatch):
    monkeypatch.setenv("CENTINELA_ALERTAS_POR_DIA", "2")
    nuevas: list[str] = []
    try:
        with TestClient(app, headers=CABECERAS_GERENTE) as cliente:
            with cliente.stream("POST", "/simulacion/avanzar", params={"dias": 1}) as respuesta:
                nuevas = _evento_end("".join(respuesta.iter_text()))["newAlerts"]
            assert len(nuevas) == 2

            for id_alerta in nuevas:
                alerta = cliente.get(f"/alertas/{id_alerta}").json()
                eventos = cliente.get("/bitacora", params={"alertId": id_alerta}).json()
                consultadas = {e["queryId"] for e in eventos if e["type"] == "evidence"}
                assert _query_ids(alerta) <= consultadas
                assert alerta["pesosAtRisk"]["value"] > 0

            aprobada = cliente.get(f"/alertas/{nuevas[0]}").json()
            assert aprobada["status"] == "proposed" and aprobada["actions"]
            respuesta = cliente.post(
                f"/alertas/{nuevas[0]}/decision",
                json={"kind": "approve", "actionId": aprobada["actions"][0]["id"]},
                headers=CABECERAS_GERENTE,
            )
            assert respuesta.json()["status"] == "executed"
            eventos = cliente.get("/bitacora", params={"alertId": nuevas[0]}).json()
            assert any(e["type"] == "result" and e["actor"] == {"kind": "agent", "agent": "ejecutor"} for e in eventos)

            respuesta = cliente.post(
                f"/alertas/{nuevas[1]}/decision",
                json={"kind": "reject", "reason": "La acción propuesta no aplica a este cliente."},
                headers=CABECERAS_GERENTE,
            )
            assert respuesta.json()["status"] == "rejected"
            assert respuesta.json()["executedAction"] is None
    finally:
        with conectar() as conn:
            for id_alerta in nuevas:
                conn.execute("DELETE FROM api.bitacora WHERE alerta_id = %s", (id_alerta,))
                conn.execute("DELETE FROM api.alertas WHERE id = %s", (id_alerta,))
            conn.commit()


CONSULTA_CHAT = {"queryId": "q_prueba_chat", "kpi": "saldo_vencido", "dia": "2026-03-02", "consulta": "kpi_consultar('saldo_vencido', '2026-03-02')"}


class _OrquestadorDelChat:
    def ask(self, question, day, alert=None):
        figura = {"value": 45, "unit": "days", "queryId": CONSULTA_CHAT["queryId"]}
        return {
            "fin": "fin.chat_respondida",
            "steps": [{"node": "conversar.raiz", "branch": "no", "agent": None}],
            "answer": {"text": "CLI-001 tiene {0} de mora.", "figures": [figura], "enough_evidence": True, "assumptions": []},
            "queries": [CONSULTA_CHAT],
            "costs": [],
        }


def test_una_pregunta_sin_alerta_queda_en_la_bitacora_y_su_consulta_se_abre(monkeypatch):
    from centinela_api.routers import chat as chat_router

    monkeypatch.setattr(chat_router, "get_orchestrator", lambda: _OrquestadorDelChat())
    marca = "¿Cuánta mora tiene CLI-001? prueba de integración"
    try:
        respuesta = TestClient(app).post("/chat", json={"question": marca}, headers=CABECERAS_GERENTE)
        assert respuesta.status_code == 200

        eventos = TestClient(app, headers=CABECERAS_GERENTE).get("/bitacora").json()
        pregunta = next(e for e in eventos if e["type"] == "question" and e["detail"] == marca)
        assert pregunta["alertId"] is None
        assert pregunta["actor"] == {"kind": "person", "name": NOMBRE_GERENTE, "role": "gerente"}
        assert any(e["type"] == "answer" and e["alertId"] is None and e["queryId"] == "q_prueba_chat" for e in eventos)

        consulta = TestClient(app, headers=CABECERAS_GERENTE).get("/consultas/q_prueba_chat")
        assert consulta.status_code == 200
        assert consulta.json() == {"id": "q_prueba_chat", "source": "kernel", "sql": CONSULTA_CHAT["consulta"], "description": "KPI saldo_vencido del 2026-03-02"}
        assert TestClient(app, headers=CABECERAS_GERENTE).get("/consultas/q_no_existe").status_code == 404
    finally:
        with conectar() as conn:
            conn.execute("DELETE FROM api.bitacora WHERE alerta_id IS NULL AND (detalle = %s OR detalle LIKE %s OR query_id = %s)", (marca, "fin.chat_respondida: CLI-001 tiene {0} de mora.", "q_prueba_chat"))
            conn.execute("DELETE FROM api.consultas WHERE query_id = %s", ("q_prueba_chat",))
            conn.commit()
