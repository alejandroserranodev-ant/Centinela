# The settings of Configuración: the seed read from data/metricas.yaml, how a stored row merges with
# it, each refusal of PUT /configuracion, the bitácora row a save writes, and what the day run takes
# from them; checked over a mocked connection.
import datetime as dt
import math
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import agentes, configuracion, db
from centinela_api.auth import persona_actual
from centinela_api.main import app
from centinela_api.modelos import Persona, Settings
from centinela_agents.metrics import Metrics
from centinela_agents.walk import Context, Detection

ANALISTA = Persona(email="analista@andina.test", name="Camila", role="analista")
AUDITOR = Persona(email="auditoria@andina.test", name="Jorge", role="auditor")


def conexion(cuerpo: dict | None = None) -> MagicMock:
    conn = MagicMock()

    def execute(query, *args, **kwargs):
        resultado = MagicMock()
        if "api.configuracion" in query and query.lstrip().startswith("SELECT"):
            resultado.fetchone.return_value = None if cuerpo is None else (cuerpo,)
        else:
            resultado.fetchone.return_value = (dt.date(2026, 1, 15),)
        return resultado

    conn.execute.side_effect = execute
    return conn


def metrica(ajustes: Settings, nombre: str):
    return next(m for m in ajustes.metrics if m.metric == nombre)


def umbral(ajustes: Settings, nombre: str, clave: str):
    return next(u for u in metrica(ajustes, nombre).thresholds if u.key == clave)


def con(ajustes: Settings, nombre: str, **cambios) -> Settings:
    return ajustes.model_copy(update={
        "metrics": [m.model_copy(update=cambios) if m.metric == nombre else m for m in ajustes.metrics]
    })


def con_umbral(ajustes: Settings, nombre: str, clave: str, valor) -> Settings:
    umbrales = [u.model_copy(update={"value": valor}) if u.key == clave else u for u in metrica(ajustes, nombre).thresholds]
    return con(ajustes, nombre, thresholds=umbrales)


def test_la_semilla_sale_de_metricas_yaml():
    semilla = configuracion.semilla()
    assert [m.metric for m in semilla.metrics] == [
        "margen_pct", "saldo_vencido", "dias_pago_prom", "cobertura_dias", "descuento_en_exceso", "veces_intervalo_habitual",
    ]
    margen = metrica(semilla, "margen_pct")
    assert (margen.name, margen.view, margen.watched) == ("Margen", "v_margen_semanal_linea", True)
    assert margen.rule.startswith("caída > 3 puntos")
    assert (umbral(semilla, "margen_pct", "caida_pts").value, umbral(semilla, "margen_pct", "caida_pts").editable) == (3, True)
    minimo = umbral(semilla, "margen_pct", "margen_pct")
    assert (minimo.value, minimo.editable, minimo.rule) == (None, False, "según el margen mínimo de su línea")
    assert umbral(semilla, "cobertura_dias", "cobertura_dias").rule == "por clase ABC: A 10, B 7"
    assert set(semilla.autonomy.values()) == {"propose"} and len(semilla.autonomy) == 4


def test_la_semilla_deja_en_gerencia_a_un_dueno_que_ningun_lider_tiene():
    semilla = configuracion.semilla()
    assert metrica(semilla, "margen_pct").owner == "Comercial"
    assert metrica(semilla, "saldo_vencido").owner == "Analista de cartera"
    assert metrica(semilla, "descuento_en_exceso").owner is None
    assert metrica(semilla, "veces_intervalo_habitual").owner is None
    assert set(semilla.owners) == {"Comercial", "Analista de cartera", "Compras"}


def test_sin_fila_se_lee_la_semilla_sin_escribir():
    conn = conexion()
    assert configuracion.leer(conn) == configuracion.semilla()
    assert all(llamada.args[0].lstrip().startswith("SELECT") for llamada in conn.execute.call_args_list)


def test_la_fila_guardada_se_funde_con_la_semilla():
    cuerpo = configuracion.semilla().model_dump(mode="json", by_alias=True)
    cuerpo["metrics"] = [m for m in cuerpo["metrics"] if m["metric"] != "dias_pago_prom"]
    margen = next(m for m in cuerpo["metrics"] if m["metric"] == "margen_pct")
    margen["watched"] = False
    margen["owner"] = "vendedor_id"
    margen["thresholds"] = [
        {"key": "caida_pts", "value": 4, "label": "x", "editable": True, "rule": "x"},
        {"key": "margen_pct", "value": 99, "label": "x", "editable": True, "rule": "x"},
        {"key": "ya_no_existe", "value": 1, "label": "x", "editable": True, "rule": "x"},
    ]
    cuerpo["autonomy"]["task"] = "inform"

    leida = configuracion.leer(conexion(cuerpo))
    semilla = configuracion.semilla()
    assert metrica(leida, "dias_pago_prom") == metrica(semilla, "dias_pago_prom")
    assert [u.key for u in metrica(leida, "margen_pct").thresholds] == ["caida_pts", "margen_pct"]
    assert umbral(leida, "margen_pct", "caida_pts").value == 4
    assert umbral(leida, "margen_pct", "margen_pct") == umbral(semilla, "margen_pct", "margen_pct")
    assert (metrica(leida, "margen_pct").watched, metrica(leida, "margen_pct").owner) == (False, None)
    assert leida.autonomy["task"] == "inform"


def guardar(nuevo: Settings, monkeypatch) -> MagicMock:
    registrar = MagicMock()
    monkeypatch.setattr(configuracion.bitacora, "registrar", registrar)
    configuracion.guardar(conexion(), nuevo, ANALISTA)
    return registrar


REFUSALS = [
    (lambda s: s.model_copy(update={"autonomy": {**s.autonomy, "task": "execute"}}), configuracion.PILOTO),
    (lambda s: con_umbral(s, "margen_pct", "margen_pct", 5.0), "no se cambia desde Centinela"),
    (lambda s: con_umbral(s, "margen_pct", "caida_pts", -1.0), "mayor o igual a cero"),
    (lambda s: con_umbral(s, "margen_pct", "caida_pts", math.inf), "mayor o igual a cero"),
    (lambda s: con_umbral(s, "margen_pct", "caida_pts", None), "mayor o igual a cero"),
    (lambda s: con(s, "margen_pct", owner="Gerente Comercial"), "no es un área"),
    (lambda s: s.model_copy(update={"metrics": s.metrics[1:]}), "La lista de KPIs"),
]


@pytest.mark.parametrize("cambio, mensaje", REFUSALS)
def test_guardar_rechaza_lo_que_no_vale(cambio, mensaje, monkeypatch):
    with pytest.raises(configuracion.ConfiguracionInvalida, match=mensaje):
        guardar(cambio(configuracion.semilla()), monkeypatch)


def test_guardar_escribe_la_fila_y_la_bitacora(monkeypatch):
    nuevo = con(con_umbral(configuracion.semilla(), "margen_pct", "caida_pts", 4.0), "margen_pct", watched=False)
    conn = conexion()
    registrar = MagicMock()
    monkeypatch.setattr(configuracion.bitacora, "registrar", registrar)
    guardada = configuracion.guardar(conn, nuevo, ANALISTA)
    assert umbral(guardada, "margen_pct", "caida_pts").value == 4
    assert any("INSERT INTO api.configuracion" in llamada.args[0] for llamada in conn.execute.call_args_list)
    _, alerta_id, tipo, actor, detalle, dia = registrar.call_args.args
    assert (alerta_id, tipo, actor.name, dia) == (None, "configuracion", "Camila", dt.date(2026, 1, 15))
    assert detalle == "Margen, «Caída frente al promedio de 8 semanas, en puntos»: 3 → 4; Margen deja de vigilarse"


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(configuracion.bitacora, "registrar", MagicMock())

    def obtener():
        yield conexion()

    app.dependency_overrides[db.obtener_conexion] = obtener

    def como(persona: Persona) -> TestClient:
        app.dependency_overrides[persona_actual] = lambda: persona
        return TestClient(app)

    yield como
    app.dependency_overrides.clear()


def test_cualquiera_lee_la_configuracion_pero_auditoria_no_la_cambia(cliente):
    leida = cliente(AUDITOR).get("/configuracion")
    assert leida.status_code == 200
    negada = cliente(AUDITOR).put("/configuracion", json=leida.json())
    assert negada.status_code == 403
    assert cliente(ANALISTA).put("/configuracion", json=leida.json()).status_code == 200


def test_las_reglas_y_fuentes_no_muestran_columnas_ni_vistas():
    for m in configuracion.semilla().metrics:
        textos = [m.rule, m.source, *(u.rule for u in m.thresholds)]
        assert not any("_" in texto or "vista" in texto for texto in textos), textos
    assert metrica(configuracion.semilla(), "margen_pct").source == "Kit del reto; margen mínimo en OPE-POL-007 §4"


def test_un_umbral_negativo_se_rechaza_con_su_etiqueta(cliente):
    cuerpo = configuracion.semilla().model_dump(mode="json", by_alias=True)
    margen = next(m for m in cuerpo["metrics"] if m["metric"] == "margen_pct")
    next(u for u in margen["thresholds"] if u["key"] == "caida_pts")["value"] = -1
    respuesta = cliente(ANALISTA).put("/configuracion", json=cuerpo)
    assert (respuesta.status_code, respuesta.json()["detail"]) == (422, "El umbral «Caída frente al promedio de 8 semanas, en puntos» de Margen debe ser un número mayor o igual a cero")


def test_el_422_trae_el_mensaje_en_espanol(cliente):
    cuerpo = configuracion.semilla().model_dump(mode="json", by_alias=True)
    cuerpo["autonomy"]["email_draft"] = "execute"
    respuesta = cliente(ANALISTA).put("/configuracion", json=cuerpo)
    assert (respuesta.status_code, respuesta.json()["detail"]) == (422, configuracion.PILOTO)


def deteccion(metric: str, pesos: float) -> Detection:
    return Detection(metric, (metric,), "e", (), {"pesos_en_riesgo": pesos})


def test_el_dia_descarta_las_metricas_que_no_se_vigilan():
    detecciones = [deteccion("margen_pct", 10), deteccion("saldo_vencido", 5), deteccion("variacion_costo_pct", 50)]
    ajustes = con(configuracion.semilla(), "margen_pct", watched=False)
    elegidas = agentes.prioritized(detecciones, set(), configuracion.vigiladas(ajustes))
    assert [d.metric for d in elegidas] == ["saldo_vencido"]


def de(metric: str, entidad: str, pesos: float) -> Detection:
    return Detection(metric, (entidad,), "e", (), {"pesos_en_riesgo": pesos})


def test_cada_metrica_tiene_su_alerta_antes_que_los_pesos(monkeypatch):
    monkeypatch.setenv("CENTINELA_ALERTAS_POR_DIA", "3")
    detecciones = [de("saldo_vencido", "C1", 900), de("saldo_vencido", "C2", 800), de("veces_intervalo_habitual", "C3", 700), de("margen_pct", "Hogar", 5)]
    elegidas = agentes.prioritized(detecciones, set(), agentes.API_METRICS)
    assert [(d.metric, d.entity) for d in elegidas] == [("saldo_vencido", ("C1",)), ("veces_intervalo_habitual", ("C3",)), ("margen_pct", ("Hogar",))]


def test_el_cupo_sobrante_va_por_pesos(monkeypatch):
    monkeypatch.setenv("CENTINELA_ALERTAS_POR_DIA", "4")
    detecciones = [de("margen_pct", "Hogar", 5), de("saldo_vencido", "C1", 900), de("saldo_vencido", "C2", 800), de("saldo_vencido", "C3", 100), de("margen_pct", "Aseo", 300)]
    elegidas = agentes.prioritized(detecciones, set(), agentes.API_METRICS)
    assert [d.entity for d in elegidas] == [("C1",), ("Aseo",), ("C2",), ("C3",)]


def test_si_hay_mas_metricas_que_cupo_ganan_las_de_mas_pesos(monkeypatch):
    monkeypatch.setenv("CENTINELA_ALERTAS_POR_DIA", "1")
    detecciones = [de("margen_pct", "Hogar", 5), de("saldo_vencido", "C1", 900)]
    assert [d.metric for d in agentes.prioritized(detecciones, set(), agentes.API_METRICS)] == ["saldo_vencido"]


def test_los_umbrales_editados_reemplazan_a_los_del_yaml_y_el_resto_queda():
    umbrales = configuracion.umbrales(con_umbral(configuracion.semilla(), "margen_pct", "caida_pts", 4.0))
    assert umbrales["margen_pct"] == {"caida_pts": 4.0, "margen_pct": {"columna": "margen_minimo_pct"}}
    assert umbrales["cobertura_dias"] == {"cobertura_dias": {"por": "clase_abc", "valores": {"A": 10, "B": 7}}}


def test_el_contexto_del_dia_lleva_los_umbrales_guardados_sin_tocar_el_original():
    ctx = Context({}, Metrics(descriptions={}, thresholds={"margen_pct": {"caida_pts": 3}, "dias_retraso": {"dias_retraso": 0}}), MagicMock(), MagicMock())
    del_dia = agentes.with_thresholds(ctx, {"margen_pct": {"caida_pts": 4.0}})
    assert del_dia.metrics.thresholds == {"margen_pct": {"caida_pts": 4.0}, "dias_retraso": {"dias_retraso": 0}}
    assert ctx.metrics.thresholds["margen_pct"]["caida_pts"] == 3
