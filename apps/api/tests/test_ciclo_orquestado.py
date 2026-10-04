import datetime as dt
from unittest.mock import ANY, MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_agents.day import Verdict
from corridas import corrida, deteccion, dia_con

from centinela_api import alertas as alertas_repo_modulo
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
        monkeypatch.setattr(modulo.alertas_repo, "guardar", lambda conn, alerta: guardadas.append(alerta) or alerta)
        monkeypatch.setattr(modulo.bitacora, "registrar", MagicMock())
        monkeypatch.setattr(modulo.simulacion, "dia_actual", lambda conn: DIA)
    monkeypatch.setattr(simulacion_router.simulacion, "avanzar", lambda conn, dias: DIA)
    monkeypatch.setattr(simulacion_router.simulacion, "sin_datos", lambda conn, dias: None)
    monkeypatch.setattr(alertas_router.alertas_repo, "obtener", lambda conn, id, bloquear=False: guardadas[-1] if guardadas else _alerta())

    def conexion():
        yield MagicMock()

    app.dependency_overrides[db.obtener_conexion] = conexion
    app.dependency_overrides[persona_actual] = lambda: Persona(email="gerente@andina.test", name="Ana", role="gerente")
    yield guardadas
    app.dependency_overrides.clear()


def test_avanzar_guarda_una_alerta_que_recorre_el_ciclo(monkeypatch, guardadas):
    veredictos, _ = dia_con(monkeypatch, corrida("alerta_a", deteccion(), "nueva", "en análisis", "propuesta"))
    TestClient(app).post("/simulacion/avanzar")
    assert guardadas and all(a.status == "proposed" for a in guardadas)
    assert veredictos == [Verdict(recorded=True)]
    simulacion_router.alertas_repo.fijar_entidad.assert_any_call(ANY, "alerta_a", ("CLI-001",))


def test_avanzar_no_guarda_una_alerta_que_salta_un_estado(monkeypatch, guardadas):
    veredictos, _ = dia_con(monkeypatch, corrida("alerta_a", deteccion(), "nueva", "propuesta"))
    TestClient(app).post("/simulacion/avanzar")
    assert not guardadas and veredictos == [Verdict(recorded=False)]


def test_la_severidad_y_los_pesos_salen_de_la_deteccion(monkeypatch, guardadas):
    dia_con(monkeypatch, corrida("alerta_a", deteccion(pesos=None, severity="critical"), "nueva", "en análisis", "propuesta"))
    TestClient(app).post("/simulacion/avanzar")
    (alerta,) = guardadas
    assert alerta.severity == "critical"
    assert (alerta.pesos_at_risk.value, alerta.pesos_at_risk.query_id) == (0, "q_saldo_vencido_CLI-001")


def test_el_costo_de_la_alerta_se_guarda(monkeypatch, guardadas):
    costo = {"analista": {"prompt_tokens": 10, "completion_tokens": 2, "calls": 1, "cached": 0}}
    dia_con(monkeypatch, corrida("alerta_a", deteccion(), "nueva", "en análisis", "propuesta", cost=costo))
    TestClient(app).post("/simulacion/avanzar")
    simulacion_router.alertas_repo.fijar_costo.assert_any_call(ANY, "alerta_a", costo)


PROMPT = {"agent": "vigia", "system": "contrato", "user": "detection.entity: CLIENTE_QWERTY"}


def test_la_bitacora_guarda_el_prompt_enmascarado_y_la_alerta_su_entidad_original(monkeypatch, guardadas):
    registrar_prompts = MagicMock()
    monkeypatch.setattr(simulacion_router.bitacora, "registrar_prompts", registrar_prompts)
    dia_con(monkeypatch, corrida("alerta_a", deteccion(), "nueva", "en análisis", "propuesta", prompts=[PROMPT]))
    TestClient(app).post("/simulacion/avanzar")
    registrar_prompts.assert_called_once_with(ANY, "alerta_a", [PROMPT], DIA)
    simulacion_router.alertas_repo.fijar_entidad.assert_any_call(ANY, "alerta_a", ("CLI-001",))


def test_el_resume_guarda_solo_los_prompts_que_agrega(monkeypatch, guardadas):
    registrar_prompts = MagicMock()
    monkeypatch.setattr(alertas_router.bitacora, "registrar_prompts", registrar_prompts)
    nuevo = {"agent": "ejecutor", "system": "contrato", "user": "recipient: CLIENTE_QWERTY"}
    orquestador = MagicMock()
    orquestador.resume.return_value = {"prompts": [PROMPT, nuevo], "resumed_prompts": [nuevo], "executed_action": {"actionId": "accion_1", "result": "Tarea creada"}}
    monkeypatch.setattr(alertas_router, "get_orchestrator", lambda: orquestador)
    TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "approve", "actionId": "accion_1"})
    registrar_prompts.assert_called_once_with(ANY, "alerta_1", [nuevo], DIA)


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


@pytest.mark.parametrize(
    "estado, detalle",
    [
        ({"fin": "fin.ya_no_aplica"}, "La acción aprobada no se ejecutó: el indicador ya no está fuera de su umbral el 2026-01-15."),
        ({"fin": "fin.fallo_ejecucion", "failures": [{"step": "hoja.ejecutor.ejecutar", "kind": "error"}]}, "La acción aprobada no se ejecutó: falló su preparación, así que queda para hacerla a mano."),
    ],
)
def test_una_aprobacion_sin_accion_ejecutada_lo_registra(monkeypatch, guardadas, estado, detalle):
    orquestador = MagicMock()
    orquestador.resume.return_value = estado
    monkeypatch.setattr(alertas_router, "get_orchestrator", lambda: orquestador)
    respuesta = TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "approve", "actionId": "accion_1"})
    assert respuesta.status_code == 200
    assert [a.status for a in guardadas] == ["approved"]
    resultado = [c.args for c in alertas_router.bitacora.registrar.call_args_list if c.args[2] == "result"]
    assert [args[4] for args in resultado] == [detalle]


def test_una_edicion_parcial_llega_al_ejecutor_con_los_demas_parametros(monkeypatch, guardadas):
    accion = Action(id="accion_1", title="Tarea", description=Sentence(text="Hace algo", figures=[]), type="task", impact=None, confidence=Confidence(level="medium"), parameters={"owner": "Compras", "cliente_id": "C1"})
    monkeypatch.setattr(alertas_router.alertas_repo, "obtener", lambda conn, id, bloquear=False: _alerta().model_copy(update={"actions": [accion]}))
    orquestador = MagicMock()
    orquestador.resume.return_value = {"executed_action": {"actionId": "accion_1", "result": "Tarea creada"}}
    monkeypatch.setattr(alertas_router, "get_orchestrator", lambda: orquestador)
    respuesta = TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "edit", "actionId": "accion_1", "parameters": {"owner": "Ventas"}})
    assert respuesta.status_code == 200
    assert orquestador.resume.call_args.args[1]["parameters"] == {"owner": "Ventas", "cliente_id": "C1"}


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
        lambda conn, id, bloquear=False: _alerta().model_copy(update={"changes_requested": True}),
    )
    respuesta = _pedir()
    assert respuesta.status_code == 409
    assert "Ya se pidieron cambios una vez" in respuesta.json()["detail"]
    orquestador.resume.assert_not_called()


def test_pedir_cambios_conserva_las_acciones_y_la_solicitud_si_el_ciclo_falla_en_la_pausa(monkeypatch, guardadas):
    _con_orquestador(monkeypatch, side_effect=RuntimeError("sin modelo"))
    respuesta = _pedir()
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["changesRequested"] is False and [a["id"] for a in cuerpo["actions"]] == ["accion_1"]
    assert [a.changes_requested for a in guardadas] == [True, False]
    registro = alertas_router.bitacora.registrar.call_args_list[-1]
    assert registro.args[2] == "proposal" and "se conservan las acciones anteriores: sin modelo" in registro.args[4]


def test_pedir_cambios_que_deja_el_ciclo_fuera_de_la_pausa_solo_deja_rechazar(monkeypatch, guardadas):
    orquestador = _con_orquestador(monkeypatch, side_effect=RuntimeError("se cayó a mitad"))
    orquestador.is_awaiting_decision.side_effect = [True, False]
    cuerpo = _pedir().json()
    assert cuerpo["changesRequested"] is True
    assert [a.changes_requested for a in guardadas] == [True]
    assert "solo queda rechazarla" in alertas_router.bitacora.registrar.call_args_list[-1].args[4]


def test_una_decision_sobre_un_ciclo_que_no_espera_es_409_y_no_se_registra(monkeypatch, guardadas):
    orquestador = _con_orquestador(monkeypatch)
    orquestador.is_awaiting_decision.return_value = False
    for decision in ({"kind": "approve", "actionId": "accion_1"}, {"kind": "request_changes", "reason": "Otra"}):
        respuesta = TestClient(app).post("/alertas/alerta_1/decision", json=decision)
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == alertas_router.EN_PAUSA
    assert guardadas == []
    alertas_router.bitacora.registrar.assert_not_called()
    orquestador.resume.assert_not_called()


def test_un_rechazo_sobre_un_ciclo_que_no_espera_se_registra_sin_reanudar(monkeypatch, guardadas):
    orquestador = _con_orquestador(monkeypatch)
    orquestador.is_awaiting_decision.return_value = False
    respuesta = TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "reject", "reason": "No aplica"})
    assert respuesta.status_code == 200 and respuesta.json()["status"] == "rejected"
    assert [a.status for a in guardadas] == ["rejected"]
    orquestador.resume.assert_not_called()


def test_una_decision_mientras_otra_reanuda_la_alerta_es_409(monkeypatch, guardadas):
    orquestador = _con_orquestador(monkeypatch)
    monkeypatch.setattr(alertas_router, "reanudando", {"alerta_1"})
    respuesta = TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "approve", "actionId": "accion_1"})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == alertas_router.EN_CURSO
    orquestador.resume.assert_not_called()


def test_la_nueva_propuesta_no_pisa_una_alerta_que_ya_no_esta_propuesta(monkeypatch, guardadas):
    _con_orquestador(monkeypatch, return_value={"actions": [_accion_nueva()], "queries": []})
    leidas = iter([_alerta(), _alerta(), _alerta().model_copy(update={"status": "rejected"})])
    monkeypatch.setattr(alertas_router.alertas_repo, "obtener", lambda conn, id, bloquear=False: next(leidas))
    cuerpo = _pedir().json()
    assert cuerpo["status"] == "rejected"
    assert [a.actions[0].id for a in guardadas] == ["accion_1"]


def test_pedir_cambios_sin_acciones_nuevas_conserva_las_anteriores(monkeypatch, guardadas):
    _con_orquestador(monkeypatch, return_value={"actions": []})
    cuerpo = _pedir().json()
    assert [a["id"] for a in cuerpo["actions"]] == ["accion_1"]


def _fin(respuesta) -> list[str]:
    return [linea for linea in respuesta.text.splitlines() if linea.startswith("data:")][-1]


def test_una_alerta_mayor_absorbe_una_deteccion_del_dia_que_no_corre(monkeypatch, guardadas):
    mayor, menor = deteccion("C1", 900), deteccion("C2", 100)
    id_mayor, id_menor = "alerta_mayor", "alerta_menor"
    estado = corrida(id_mayor, mayor, "nueva", "en análisis", "propuesta", absorbed={id_menor: menor}, merged_alerts=[id_menor])
    estado.state["transitions"].insert(2, [id_menor, "unida"])
    veredictos, _ = dia_con(monkeypatch, estado)
    respuesta = TestClient(app).post("/simulacion/avanzar")
    assert veredictos == [Verdict(recorded=True, absorbed=(id_menor,))]
    unida = next(a for a in guardadas if a.id == id_menor)
    assert unida.status == "merged" and unida.merged_into == id_mayor
    assert unida.cause.reason == "La explica la causa de la alerta que queda."
    assert unida.pesos_at_risk.query_id == menor.query["queryId"] and unida.cause.queries_reviewed == [menor.query["queryId"]]
    simulacion_router.consultas.registrar.assert_any_call(ANY, [dict(menor.query)])
    restante = [a for a in guardadas if a.id == id_mayor][-1]
    detalles = [llamada.args[4] for llamada in simulacion_router.bitacora.registrar.call_args_list]
    assert restante.labels and f"Unida a la alerta {' · '.join(restante.labels)}: la misma causa." in next(d for d in detalles if d.startswith("Unida"))
    assert restante.status == "proposed" and [m.id for m in restante.merged_alerts] == [id_menor]
    assert restante.pesos_at_risk.value == 900
    assert f'"newAlerts": ["{id_mayor}"]' in _fin(respuesta)


def _unida_a(alert_id, destino):
    return corrida(alert_id, deteccion("C1", 500), "nueva", "en análisis", "unida", merged_into=destino)


def test_una_alerta_se_une_a_una_analizada_antes_que_sigue_abierta(monkeypatch, guardadas):
    veredictos, llamadas = dia_con(monkeypatch, _unida_a("alerta_b", "alerta_1"), anteriores=[(_alerta(), ["C9"])])
    monkeypatch.setattr(simulacion_router.alertas_repo, "obtener", lambda conn, id, bloquear=False: _alerta() if id == "alerta_1" else None)
    respuesta = TestClient(app).post("/simulacion/avanzar")
    (anterior,) = llamadas[0]["earlier"]
    assert (anterior.alert_id, anterior.status, anterior.entity) == ("alerta_1", "propuesta", ("C9",))
    unida, destino = guardadas
    assert unida.status == "merged" and unida.merged_into == "alerta_1"
    assert destino.id == "alerta_1" and [m.id for m in destino.merged_alerts] == [unida.id]
    assert veredictos == [Verdict(recorded=True)]
    assert '"newAlerts": []' in _fin(respuesta)


def test_una_union_rechazada_pide_correr_la_alerta_otra_vez_sin_ese_destino(monkeypatch, guardadas):
    rechazada = _alerta().model_copy(update={"status": "rejected"})
    otra_vez = corrida("alerta_b", deteccion("C1", 500), "nueva", "en análisis", "propuesta", actions=[_accion_nueva()])
    veredictos, _ = dia_con(monkeypatch, _unida_a("alerta_b", "alerta_1"), otra_vez, anteriores=[(_alerta(), ["C9"])])
    monkeypatch.setattr(simulacion_router.alertas_repo, "obtener", lambda conn, id, bloquear=False: rechazada if id == "alerta_1" else None)
    respuesta = TestClient(app).post("/simulacion/avanzar")
    assert veredictos == [Verdict(recorded=False, refused_merge="alerta_1"), Verdict(recorded=True)]
    (propia,) = guardadas
    assert propia.status == "proposed" and propia.merged_into is None and propia.actions
    assert f'"newAlerts": ["{propia.id}"]' in _fin(respuesta)
    assert "No se unió a la alerta alerta_1, que está rechazada." in simulacion_router.bitacora.registrar.call_args_list[0].args[4]


def test_guardar_conserva_las_alertas_unidas_que_otra_escritura_agrego():
    unida = {"id": "alerta_9", "metric": "saldo_vencido", "simulatedDate": "2026-01-15", "title": {"text": "Otra", "figures": []}, "pesosAtRisk": {"value": 10, "unit": "COP", "queryId": "q9"}, "cause": {"kind": "no_evidence", "reason": "Unida", "queriesReviewed": []}}
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ([unida],)
    guardada = alertas_repo_modulo.guardar(conn, _alerta())
    assert [m.id for m in guardada.merged_alerts] == ["alerta_9"]
    lectura, escritura = [llamada.args for llamada in conn.execute.call_args_list]
    assert "FOR UPDATE" in lectura[0]
    assert escritura[1][2].obj["mergedAlerts"][0]["id"] == "alerta_9"


def test_listar_sin_estado_excluye_las_unidas_y_unida_las_lista(monkeypatch, guardadas):
    conn = MagicMock()
    alertas_repo_modulo.listar(conn, None)
    assert "status <> 'merged'" in conn.execute.call_args.args[0]
    pedidos = []
    monkeypatch.setattr(alertas_router.alertas_repo, "listar", lambda conn, status: pedidos.append(status) or [])
    monkeypatch.setattr(alertas_router.permisos, "vistas", lambda conn, persona, alertas: alertas)
    assert TestClient(app).get("/alertas", params={"estado": "unida"}).status_code == 200
    assert pedidos == ["merged"]


def test_un_rechazo_guarda_su_destino_y_las_acciones_que_rechazo(monkeypatch, guardadas):
    _con_orquestador(monkeypatch, return_value={"rejection_target": "propuesta"})
    registrar = MagicMock()
    monkeypatch.setattr(alertas_router.rechazos, "registrar", registrar)
    TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "reject", "reason": " No aplica "})
    registrar.assert_called_once_with(ANY, "alerta_1", "saldo_vencido", "propuesta", ["accion_1"], "No aplica", DIA)


@pytest.mark.parametrize("en_pausa, estado", [(True, {}), (False, {"rejection_target": "propuesta"})], ids=["no target", "no paused graph"])
def test_un_rechazo_que_el_clasificador_no_dirigio_no_guarda_evidencia(monkeypatch, guardadas, en_pausa, estado):
    orquestador = _con_orquestador(monkeypatch, return_value=estado)
    orquestador.is_awaiting_decision.return_value = en_pausa
    registrar = MagicMock()
    monkeypatch.setattr(alertas_router.rechazos, "registrar", registrar)
    TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "reject", "reason": "No aplica"})
    registrar.assert_not_called()


def test_una_escritura_de_evidencia_que_falla_se_registra_con_su_propio_mensaje(monkeypatch, guardadas, caplog):
    _con_orquestador(monkeypatch, return_value={"rejection_target": "propuesta"})
    monkeypatch.setattr(alertas_router.rechazos, "registrar", MagicMock(side_effect=RuntimeError("store down")))
    respuesta = TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "reject", "reason": "No aplica"})
    assert respuesta.status_code == 200
    mensajes = [registro.getMessage() for registro in caplog.records]
    assert any("Rejection evidence write failed" in mensaje for mensaje in mensajes)
    assert not any("Orchestrator reject failed" in mensaje for mensaje in mensajes)
