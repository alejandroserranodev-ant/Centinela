import json

from fastapi.testclient import TestClient

from centinela_api.main import app


def _eventos(cuerpo: str) -> list[tuple[str, dict]]:
    eventos = []
    for bloque in cuerpo.strip().split("\n\n"):
        lineas = dict(linea.split(": ", 1) for linea in bloque.splitlines())
        eventos.append((lineas["event"], json.loads(lineas["data"])))
    return eventos


def test_chat_acepta_la_pregunta_con_su_alerta():
    respuesta = TestClient(app).post("/chat", json={"question": "¿Por qué?", "alertId": "alerta_1"})
    assert respuesta.status_code == 200
    eventos = _eventos(respuesta.text)
    assert [nombre for nombre, _ in eventos] == ["step", "step", "end"]
    assert eventos[-1][1]["alertId"] == "alerta_1"


def test_chat_acepta_la_pregunta_sin_alerta():
    respuesta = TestClient(app).post("/chat", json={"question": "¿Cómo va la cartera?"})
    assert respuesta.status_code == 200
    eventos = _eventos(respuesta.text)
    assert eventos[-1][0] == "end"
    assert eventos[-1][1]["alertId"] is None
