import psycopg

from . import configuracion
from .modelos import Alert, Persona, Settings

GERENCIA = configuracion.GERENCIA


def _dueno(ajustes: Settings, metric: str) -> str | None:
    return next((m.owner for m in ajustes.metrics if m.metric == metric), None)


def _area(ajustes: Settings, metric: str) -> str | None:
    area = _dueno(ajustes, metric)
    return area if area in configuracion.areas() else None


def _decide(persona: Persona, area: str | None) -> bool:
    if persona.role == "gerente":
        return True
    return persona.role == "lider_proceso" and area is not None and persona.area == area


def responsable(conn: psycopg.Connection, metric: str) -> str | None:
    return _dueno(configuracion.leer(conn), metric)


def area_que_decide(conn: psycopg.Connection, metric: str) -> str | None:
    return _area(configuracion.leer(conn), metric)


def puede_decidir(conn: psycopg.Connection, persona: Persona, alerta: Alert) -> bool:
    return _decide(persona, area_que_decide(conn, alerta.metric))


def puede_configurar(persona: Persona) -> bool:
    return persona.role in ("analista", "gerente")


def puede_retirar(persona: Persona) -> bool:
    return persona.role in ("analista", "gerente")


AUDITORIA = "Auditoría consulta las alertas; no las decide"


def negada(conn: psycopg.Connection, persona: Persona, alerta: Alert) -> str:
    if persona.role == "auditor":
        return AUDITORIA
    area = area_que_decide(conn, alerta.metric)
    return f"Esta alerta la decide {area}" if area else "Esta alerta la decide la gerencia"


def _vista(persona: Persona, alerta: Alert, area: str | None) -> Alert:
    return alerta.model_copy(update={"decided_by": area or GERENCIA, "can_decide": _decide(persona, area)})


def vista_con(ajustes: Settings, persona: Persona, alerta: Alert) -> Alert:
    return _vista(persona, alerta, _area(ajustes, alerta.metric))


def vistas(conn: psycopg.Connection, persona: Persona, alertas: list[Alert]) -> list[Alert]:
    ajustes = configuracion.leer(conn)
    return [vista_con(ajustes, persona, alerta) for alerta in alertas]


def vista(conn: psycopg.Connection, persona: Persona, alerta: Alert) -> Alert:
    return vistas(conn, persona, [alerta])[0]
