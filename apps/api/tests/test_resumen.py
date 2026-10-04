# The inbox totals: their shape, deterministic queryIds, the recorded query with source alertas, and,
# against a real Postgres when DSN_ADMIN reaches one, the totals over two seeded proposed alerts.
import datetime as dt
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import consultas, db, resumen
from centinela_api.auth import persona_actual
from centinela_api.main import app
from centinela_api.modelos import Persona

GERENTE = Persona(email="gerente@andina.test", name="Mariana", role="gerente")
DIA = dt.date(2026, 10, 5)


def conexion(valores: list) -> MagicMock:
    conn = MagicMock()
    pendientes = iter(valores)

    def execute(query, *args, **kwargs):
        resultado = MagicMock()
        if "dia_actual" in query:
            resultado.fetchone.return_value = (DIA,)
        elif query.lstrip().startswith("SELECT"):
            resultado.fetchone.return_value = (next(pendientes),)
        return resultado

    conn.execute.side_effect = execute
    return conn


def test_calcula_tres_cifras_con_su_consulta():
    conn = conexion([7_000_000, 1_500_000, 2])
    resumen_bandeja = resumen.calcular(conn)
    assert (resumen_bandeja.money_at_risk.value, resumen_bandeja.money_at_risk.unit) == (7_000_000, "COP")
    assert resumen_bandeja.recoverable_per_month.unit == "COP"
    assert (resumen_bandeja.pending_decisions.value, resumen_bandeja.pending_decisions.unit) == (2, "units")
    inserciones = [c.args for c in conn.execute.call_args_list if "INSERT INTO api.consultas" in c.args[0]]
    assert [i[1][1] for i in inserciones] == [
        "bandeja_pesos_en_riesgo", "bandeja_recuperable_mes", "bandeja_decisiones_pendientes",
    ]
    assert {i[1][4] for i in inserciones} == {"alertas"}


def test_los_ids_son_deterministas_y_cambian_con_el_valor():
    uno = resumen.calcular(conexion([1, 2, 3]))
    otra_vez = resumen.calcular(conexion([1, 2, 3]))
    distinto = resumen.calcular(conexion([9, 2, 3]))
    assert uno == otra_vez
    assert uno.money_at_risk.query_id != distinto.money_at_risk.query_id
    assert uno.recoverable_per_month.query_id == distinto.recoverable_per_month.query_id
    assert len({uno.money_at_risk.query_id, uno.recoverable_per_month.query_id, uno.pending_decisions.query_id}) == 3


def test_la_ruta_exige_sesion_y_responde_la_forma_del_contrato():
    cliente = TestClient(app)
    assert cliente.get("/bandeja/resumen").status_code == 401
    app.dependency_overrides[persona_actual] = lambda: GERENTE
    app.dependency_overrides[db.obtener_conexion] = lambda: conexion([5, 0, 1])
    try:
        cuerpo = cliente.get("/bandeja/resumen").json()
    finally:
        app.dependency_overrides.clear()
    assert set(cuerpo) == {"moneyAtRisk", "recoverablePerMonth", "pendingDecisions"}
    assert cuerpo["pendingDecisions"]["value"] == 1


def test_la_descripcion_de_alertas_dice_la_suma_y_el_dia():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("q_x", "bandeja_pesos_en_riesgo", DIA, "SELECT 1", "alertas")
    consulta = consultas.obtener(conn, "q_x")
    assert consulta.source == "alertas"
    assert consulta.description == "Suma de pesos en riesgo de las alertas propuestas, día 2026-10-05"


@pytest.mark.integracion
def test_las_cifras_de_dos_alertas_propuestas_abren_su_consulta():
    from centinela_api import alertas as alertas_repo
    from centinela_api.db import conectar
    from tests.test_api_integracion import _alerta_de_prueba, CABECERAS_GERENTE

    ids = ["alerta_prueba_resumen_a", "alerta_prueba_resumen_b"]
    with conectar() as conn:
        antes = resumen.calcular(conn)
        for id in ids:
            alertas_repo.guardar(conn, _alerta_de_prueba().model_copy(update={"id": id}))
        conn.commit()
    try:
        cliente = TestClient(app, headers=CABECERAS_GERENTE)
        cuerpo = cliente.get("/bandeja/resumen").json()
        assert cuerpo["pendingDecisions"]["value"] == antes.pending_decisions.value + 2
        assert cuerpo["moneyAtRisk"]["value"] == antes.money_at_risk.value + 10_000_000
        assert cuerpo["recoverablePerMonth"]["value"] == antes.recoverable_per_month.value
        assert cliente.get("/bandeja/resumen").json() == cuerpo
        for cifra in cuerpo.values():
            consulta = cliente.get(f"/consultas/{cifra['queryId']}").json()
            assert consulta["source"] == "alertas"
            assert "api.alertas" in consulta["sql"]
            assert "día" in consulta["description"]
    finally:
        with conectar() as conn:
            conn.execute("DELETE FROM api.alertas WHERE id = ANY(%s)", (ids,))
            conn.commit()
