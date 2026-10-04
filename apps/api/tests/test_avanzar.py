import asyncio
import datetime as dt
import json
from unittest.mock import ANY, MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_agents.day import Step
from corridas import ARBOL, corrida, deteccion, dia_con

from centinela_api import db
from centinela_api.auth import persona_actual
from centinela_api.main import app
from centinela_api.modelos import Alert, AgentStep, Persona
from centinela_api.routers import simulacion as simulacion_router


CORTE = dt.date(2026, 9, 30)


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
        resultado.fetchone.return_value = (CORTE,) if "fecha_corte" in query else (dt.date(2026, 1, 15),) if "dia_actual" in query else None
        resultado.fetchall.return_value = []
        return resultado

    conn.execute.side_effect = execute
    return conn


@pytest.fixture
def cliente(conn, monkeypatch):
    detection = deteccion()
    detectada = Step("alerta_a", "vigia", "detectar", "done", "Detectada anomalía", False, detection.metric, detection.entity)
    dia_con(monkeypatch, detectada, corrida("alerta_a", detection, "nueva", "en análisis", "propuesta"))
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


def test_el_fin_del_dia_no_es_un_error(cliente, caplog):
    cliente.post("/simulacion/avanzar?dias=1")
    assert not [r for r in caplog.records if r.levelname == "ERROR"]


def test_un_segundo_dia_en_curso_se_rechaza_con_409(cliente):
    asyncio.run(simulacion_router.day_run.acquire())
    try:
        respuesta = cliente.post("/simulacion/avanzar?dias=1")
    finally:
        simulacion_router.day_run.release()
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya hay un día en curso"
    assert not simulacion_router.day_run.locked()


def test_avanzar_mas_alla_del_ultimo_dia_de_datos_responde_409(cliente, monkeypatch):
    avanzar = MagicMock()
    monkeypatch.setattr(simulacion_router.simulacion, "avanzar", avanzar)
    respuesta = cliente.post("/simulacion/avanzar?dias=300")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Los datos llegan hasta el 2026-09-30: no hay un día siguiente que revisar"
    avanzar.assert_not_called()
    assert not simulacion_router.day_run.locked()


def test_el_dia_actual_dice_hasta_donde_llegan_los_datos(cliente):
    assert cliente.get("/simulacion/dia-actual").json() == {"dia": "2026-01-15", "ultimoDia": "2026-09-30"}


def test_el_dia_transmite_cada_paso_con_la_etiqueta_de_la_metrica(cliente, monkeypatch):
    detection = deteccion()

    def paso(agente, nodo, estado, descripcion):
        return Step("alerta_a", agente, nodo, estado, descripcion, False, detection.metric, detection.entity)

    dia_con(
        monkeypatch,
        paso("vigia", "detectar", "done", "Detectada anomalía"),
        paso("analista", "hoja.analista.explicar", "running", "Buscando la causa"),
        paso("analista", "hoja.analista.explicar", "done", "Buscando la causa"),
        corrida("alerta_a", detection, "nueva", "en análisis", "propuesta"),
    )
    pasos = [dato for nombre, dato in _eventos(cliente.post("/simulacion/avanzar?dias=1").text) if nombre == "step"]
    assert [(p["agent"], p["status"]) for p in pasos[:3]] == [("vigia", "done"), ("analista", "running"), ("analista", "done")]
    assert pasos[1]["description"] == "Buscando la causa de Cartera vencida · CLI-001"
    assert pasos[2]["end"] and pasos[2]["start"] == pasos[1]["start"]


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
    assert (dato["decidedBy"], dato["canDecide"]) == ("Analista de cartera", False)
    assert dato == {**guardada.model_dump(by_alias=True, mode="json"), "decidedBy": "Analista de cartera", "canDecide": False}


@pytest.mark.parametrize("dias, esperado", [(None, dt.date(2026, 8, 31)), ("5", dt.date(2026, 9, 25))])
def test_el_reloj_se_siembra_antes_del_ultimo_dia_de_datos(monkeypatch, dias, esperado):
    from centinela_api import simulacion

    if dias is None:
        monkeypatch.delenv(simulacion.DIAS_DE_DEMO, raising=False)
    else:
        monkeypatch.setenv(simulacion.DIAS_DE_DEMO, dias)
    sembrados = []

    def execute(query, *args):
        resultado = MagicMock()
        resultado.fetchone.return_value = (CORTE,) if "fecha_corte" in query else None
        if query.startswith("INSERT"):
            sembrados.append(args[0][0])
        return resultado

    conn = MagicMock()
    conn.execute.side_effect = execute
    assert simulacion.dia_actual(conn) == esperado
    assert sembrados == [esperado]


def test_el_dia_corre_sobre_la_version_que_crecio_y_guarda_la_de_cada_alerta(cliente, monkeypatch):
    arbol = ARBOL.model_copy(update={"version": 9})
    dia_con(monkeypatch, corrida("alerta_a", deteccion(), "nueva", "en análisis", "propuesta", arbol_version=9))
    monkeypatch.setattr(simulacion_router.arboles, "del_dia", lambda conn, dia: arbol)
    cliente.post("/simulacion/avanzar?dias=1")
    simulacion_router.get_orchestrator().use_tree.assert_called_once_with(arbol)
    simulacion_router.alertas_repo.fijar_version.assert_called_once_with(ANY, "alerta_a", 9)
