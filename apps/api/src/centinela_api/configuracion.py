import math
from functools import cache
from typing import Any, get_args

import psycopg
from centinela_agents.graph import manual_owners
from centinela_agents.metrics import is_number
from centinela_agents.skills import skill
from centinela_agents.yaml_loader import load_yaml
from psycopg.types.json import Jsonb

from . import auth, bitacora, simulacion
from .agentes import API_METRICS, METRICAS
from .modelos import ActionType, ActorPerson, AutonomyLevel, Persona, Settings, Threshold, WatchedMetric

PILOTO = "Ninguna acción puede ejecutarse sola durante el piloto: el máximo es Propone"
GERENCIA = "Gerencia"
NIVELES: dict[AutonomyLevel, str] = {"inform": "Informa", "propose": "Propone", "execute": "Ejecuta"}
ETIQUETAS = {
    "caida_pts": "Caída frente al promedio de 8 semanas, en puntos",
    "margen_pct": "Margen mínimo de la línea",
    "max_dias_vencido": "Días de vencimiento máximos",
    "saldo_abierto": "Saldo abierto frente al cupo de crédito",
    "aumento_pct": "Aumento frente al promedio histórico, en %",
    "cobertura_dias": "Cobertura mínima, en días",
    "descuento_en_exceso": "Descuento por encima del tope, en pesos",
    "pedidos": "Pedidos mínimos del cliente",
    "veces_intervalo_habitual": "Veces el intervalo habitual",
}


class ConfiguracionInvalida(Exception):
    pass


@cache
def _metricas() -> dict[str, dict[str, Any]]:
    return {nombre: entrada for nombre, entrada in load_yaml(METRICAS)["metricas"].items() if nombre in API_METRICS}


def _numero(valor: float) -> str:
    return str(int(valor)) if float(valor).is_integer() else str(valor)


def _umbral(clave: str, spec: Any) -> Threshold:
    etiqueta = ETIQUETAS.get(clave, clave.replace("_", " "))
    if is_number(spec):
        return Threshold(key=clave, value=float(spec), label=etiqueta, editable=True, rule=f"Por defecto {_numero(spec)}")
    if isinstance(spec, bool):
        regla = "sí" if spec else "no"
    elif isinstance(spec, dict) and "columna" in spec:
        regla = f"según la columna {spec['columna']}"
    elif isinstance(spec, dict) and "por" in spec:
        regla = f"por {spec['por']}: " + ", ".join(f"{clase} {_numero(valor)}" for clase, valor in spec["valores"].items())
    else:
        regla = str(spec)
    return Threshold(key=clave, value=None, label=etiqueta, editable=False, rule=regla)


def areas() -> list[str]:
    return list(dict.fromkeys(p.area for p in auth.PERFILES.values() if p.rol == "lider_proceso" and p.area))


def semilla() -> Settings:
    duenos = manual_owners(skill("estratega", "acciones"))
    posibles = areas()
    return Settings(
        metrics=[
            WatchedMetric(
                metric=nombre,
                name=entrada["etiqueta"],
                description=entrada["descripcion"],
                view=entrada["vista"],
                rule=entrada["umbral_alerta"],
                source=entrada["fuente_umbral"],
                thresholds=[_umbral(clave, spec) for clave, spec in (entrada.get("umbrales") or {}).items()],
                watched=True,
                owner=duenos.get(nombre) if duenos.get(nombre) in posibles else None,
            )
            for nombre, entrada in _metricas().items()
        ],
        owners=posibles,
        autonomy={tipo: "propose" for tipo in get_args(ActionType)},
    )


def _fusionar(base: Settings, cuerpo: dict[str, Any]) -> Settings:
    guardadas = {m.get("metric"): m for m in cuerpo.get("metrics") or [] if isinstance(m, dict)}
    autonomia = cuerpo.get("autonomy") or {}
    metricas = []
    for semilla_ in base.metrics:
        guardada = guardadas.get(semilla_.metric)
        if guardada is None:
            metricas.append(semilla_)
            continue
        valores = {u.get("key"): u.get("value") for u in guardada.get("thresholds") or [] if isinstance(u, dict)}
        umbrales = [
            u.model_copy(update={"value": float(valores[u.key])}) if u.editable and is_number(valores.get(u.key)) else u
            for u in semilla_.thresholds
        ]
        dueno = guardada.get("owner")
        metricas.append(semilla_.model_copy(update={
            "thresholds": umbrales,
            "watched": guardada.get("watched") if isinstance(guardada.get("watched"), bool) else semilla_.watched,
            "owner": dueno if dueno in base.owners else None,
        }))
    return base.model_copy(update={
        "metrics": metricas,
        "autonomy": {
            tipo: autonomia[tipo] if autonomia.get(tipo) in NIVELES else nivel
            for tipo, nivel in base.autonomy.items()
        },
    })


def leer(conn: psycopg.Connection) -> Settings:
    fila = conn.execute("SELECT cuerpo FROM api.configuracion").fetchone()
    return semilla() if fila is None else _fusionar(semilla(), fila[0])


def _validar(actual: Settings, nuevo: Settings) -> None:
    if sorted(m.metric for m in nuevo.metrics) != sorted(m.metric for m in actual.metrics):
        raise ConfiguracionInvalida("La lista de KPIs no coincide con la que vigila Centinela")
    if set(nuevo.autonomy) != set(actual.autonomy):
        raise ConfiguracionInvalida("La autonomía debe nombrar cada tipo de acción")
    if any(nivel == "execute" for nivel in nuevo.autonomy.values()):
        raise ConfiguracionInvalida(PILOTO)
    previas = {m.metric: m for m in actual.metrics}
    for metrica in nuevo.metrics:
        previa = previas[metrica.metric]
        umbrales = {u.key: u for u in previa.thresholds}
        if sorted(u.key for u in metrica.thresholds) != sorted(umbrales):
            raise ConfiguracionInvalida(f"Los umbrales de {previa.name} no coinciden con los de data/metricas.yaml")
        for umbral in metrica.thresholds:
            antes = umbrales[umbral.key]
            if not antes.editable:
                if umbral.value != antes.value or umbral.editable:
                    raise ConfiguracionInvalida(f"El umbral {umbral.key} de {previa.name} no se cambia desde Centinela: {antes.rule}")
            elif umbral.value is None or not math.isfinite(umbral.value) or umbral.value < 0:
                raise ConfiguracionInvalida(f"El umbral {umbral.key} de {previa.name} debe ser un número mayor o igual a cero")
        if metrica.owner is not None and metrica.owner not in actual.owners:
            raise ConfiguracionInvalida(f"{metrica.owner} no es un área que lidere un proceso: elige una de la lista o Gerencia")


def cambios(actual: Settings, nuevo: Settings) -> list[str]:
    previas = {m.metric: m for m in actual.metrics}
    lineas = []
    for metrica in nuevo.metrics:
        previa = previas[metrica.metric]
        antes = {u.key: u.value for u in previa.thresholds}
        for umbral in metrica.thresholds:
            if umbral.value is not None and umbral.value != antes[umbral.key]:
                lineas.append(f"Umbral {umbral.key} de {metrica.metric}: {_numero(antes[umbral.key])} → {_numero(umbral.value)}")
        if metrica.watched != previa.watched:
            lineas.append(f"{previa.name} {'vuelve a vigilarse' if metrica.watched else 'deja de vigilarse'}")
        if metrica.owner != previa.owner:
            lineas.append(f"Responsable de {previa.name}: {previa.owner or GERENCIA} → {metrica.owner or GERENCIA}")
    for tipo, nivel in nuevo.autonomy.items():
        if nivel != actual.autonomy[tipo]:
            lineas.append(f"Autonomía de {tipo}: {NIVELES[actual.autonomy[tipo]]} → {NIVELES[nivel]}")
    return lineas


def guardar(conn: psycopg.Connection, nuevo: Settings, persona: Persona) -> Settings:
    actual = leer(conn)
    _validar(actual, nuevo)
    guardada = _fusionar(semilla(), nuevo.model_dump(mode="json", by_alias=True))
    detalle = "; ".join(cambios(actual, guardada)) or "Configuración guardada sin cambios"
    with conn.transaction():
        dia = simulacion.dia_actual(conn)
        conn.execute(
            "INSERT INTO api.configuracion (id, cuerpo, guardado_por, actualizado_en) VALUES (true, %s, %s, now()) "
            "ON CONFLICT (id) DO UPDATE SET cuerpo = EXCLUDED.cuerpo, guardado_por = EXCLUDED.guardado_por, "
            "actualizado_en = EXCLUDED.actualizado_en",
            (Jsonb(guardada.model_dump(mode="json", by_alias=True)), Jsonb(persona.model_dump(mode="json", by_alias=True))),
        )
        bitacora.registrar(conn, None, "configuracion", ActorPerson(name=persona.name, role=persona.role), detalle, dia)
    return guardada


def vigiladas(ajustes: Settings) -> set[str]:
    return {m.metric for m in ajustes.metrics if m.watched}


def umbrales(ajustes: Settings) -> dict[str, dict[str, Any]]:
    editados = {m.metric: {u.key: u.value for u in m.thresholds if u.editable} for m in ajustes.metrics}
    return {
        nombre: {**(entrada.get("umbrales") or {}), **editados.get(nombre, {})}
        for nombre, entrada in _metricas().items()
    }
