"""Tests para validar que los endpoints de agentes existen y responden correctamente.

Para tests de integración completos, usar pytest -m integracion con BD real.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api.main import app
from centinela_api.modelos import (
    AgentAlertInput,
    Confidence,
    Figure,
    Sentence,
)

AGENT_KEY = "insecure-dev-key"


@pytest.fixture
def mock_conn():
    """Mock de conexión Postgres para tests unitarios."""
    import datetime as dt

    conn = MagicMock()

    def mock_execute(query, *args, **kwargs):
        mock_result = MagicMock()
        if "SELECT dia_actual" in query:
            mock_result.fetchone.return_value = (dt.date(2026, 1, 15),)
        elif "SELECT centinela.fecha_corte()" in query:
            mock_result.fetchone.return_value = (dt.date(2026, 1, 15),)
        else:
            mock_result.fetchone.return_value = None
        mock_result.fetchall.return_value = []
        return mock_result

    conn.execute.side_effect = mock_execute
    conn.transaction.return_value.__enter__ = MagicMock(return_value=None)
    conn.transaction.return_value.__exit__ = MagicMock(return_value=None)
    return conn


@pytest.fixture
def app_with_mock_db(mock_conn):
    """Inyecta mock de BD en FastAPI."""
    from centinela_api import db

    def override_get_db():
        yield mock_conn

    app.dependency_overrides[db.obtener_conexion] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_mock_db):
    """TestClient con BD mockeada."""
    return TestClient(app_with_mock_db)


@pytest.fixture
def alerta_input() -> AgentAlertInput:
    """Alerta de prueba."""
    return AgentAlertInput(
        severity="high",
        metric="margen_pct",
        title=Sentence(text="Margen bajo", figures=[]),
        pesos_at_risk=Figure(value=42000000, unit="COP", query_id="q1"),
        confidence=Confidence(level="high"),
        simulated_date="2026-01-15",
    )


class TestEndpointsExisten:
    """Valida que los endpoints internos para agentes existan."""

    def test_post_interno_alertas_requiere_autenticacion(self, client, alerta_input):
        """POST /interno/alertas sin clave debe fallar."""
        response = client.post(
            "/interno/alertas",
            json=alerta_input.model_dump(by_alias=True),
            headers={"X-Agent": "vigia"},
        )
        assert response.status_code == 422  # Header requerido

    def test_post_interno_alertas_rechaza_clave_invalida(self, client, alerta_input):
        """POST /interno/alertas con clave inválida debe fallar."""
        response = client.post(
            "/interno/alertas",
            json=alerta_input.model_dump(by_alias=True),
            headers={"X-Agent": "vigia", "X-Agent-Key": "wrong"},
        )
        assert response.status_code == 401

    def test_put_interno_alertas_id_causa_existe(self, client):
        """PUT /interno/alertas/{id}/causa debe aceptar requests válidas."""
        # Este test valida que el endpoint existe y valida autenticación
        response = client.put(
            "/interno/alertas/alerta_test/causa",
            json={"cause": {"kind": "no_evidence", "reason": "test"}},
            headers={"X-Agent": "analista"},
        )
        # Sin header X-Agent-Key: 422 o 401
        assert response.status_code in (422, 401)

    def test_put_interno_alertas_id_propuesta_existe(self, client):
        """PUT /interno/alertas/{id}/propuesta debe aceptar requests."""
        response = client.put(
            "/interno/alertas/alerta_test/propuesta",
            json={"actions": []},
            headers={"X-Agent": "estratega"},
        )
        # Sin auth: 422 o 401
        assert response.status_code in (422, 401)

    def test_post_interno_alertas_id_ejecutar_existe(self, client):
        """POST /interno/alertas/{id}/ejecutar debe aceptar requests."""
        response = client.post(
            "/interno/alertas/alerta_test/ejecutar",
            json={
                "action_id": "action_1",
                "status": "success",
                "result": "OK",
            },
            headers={"X-Agent": "ejecutor"},
        )
        # Sin auth: 422 o 401
        assert response.status_code in (422, 401)


class TestEnmascaramiento:
    """Valida que el enmascaramiento está disponible."""

    def test_masking_importa_sin_errores(self):
        """El módulo masking debe importar correctamente."""
        from centinela_api import masking

        # Valida funciones clave existen
        assert hasattr(masking, "mask_cliente_id")
        assert hasattr(masking, "mask_cliente_nombre")
        assert hasattr(masking, "mask_dict_for_model")

    def test_mask_cliente_id_es_determinista(self):
        """El enmascaramiento debe ser determinista."""
        from centinela_api.masking import mask_cliente_id

        id1 = mask_cliente_id("C0042")
        id2 = mask_cliente_id("C0042")
        assert id1 == id2

    def test_mask_dict_anonimiza_nombres(self):
        """mask_dict_for_model debe enmascarar nombres."""
        from centinela_api.masking import mask_dict_for_model

        data = {"cliente": "Juan Pérez", "cliente_id": "C0042", "city": "Bogotá"}
        masked = mask_dict_for_model(data)

        # Nombres enmascarados
        assert masked["cliente"] != "Juan Pérez"
        assert masked["cliente_id"] != "C0042"

        # Datos públicos preservados
        assert masked["city"] == "Bogotá"

    def test_mask_sql_result_procesa_multiples_filas(self):
        """mask_sql_result debe procesar listas de diccionarios."""
        from centinela_api.masking import mask_sql_result

        rows = [
            {"cliente": "Juan", "cliente_id": "C0001", "valor": 1000},
            {"cliente": "María", "cliente_id": "C0002", "valor": 2000},
        ]
        masked = mask_sql_result(rows)

        assert len(masked) == 2
        assert masked[0]["cliente"] != "Juan"
        assert masked[1]["cliente"] != "María"
        assert masked[0]["valor"] == 1000  # Números preservados
