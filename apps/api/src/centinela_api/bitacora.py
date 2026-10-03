import datetime

import psycopg
from psycopg.types.json import Jsonb

from .modelos import Actor, LogEvent, LogEventType


def registrar(
    conn: psycopg.Connection,
    alerta_id: str,
    tipo: LogEventType,
    actor: Actor,
    detalle: str,
    dia_simulado: datetime.date,
    query_id: str | None = None,
) -> LogEvent:
    fila = conn.execute(
        "INSERT INTO api.bitacora (alerta_id, tipo, actor, detalle, query_id, dia_simulado) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, creado_en",
        (alerta_id, tipo, Jsonb(actor.model_dump(by_alias=True)), detalle, query_id, dia_simulado),
    ).fetchone()
    id, creado_en = fila
    return LogEvent(
        id=str(id),
        date=creado_en.isoformat(),
        simulated_day=dia_simulado.isoformat(),
        alert_id=alerta_id,
        type=tipo,
        actor=actor,
        detail=detalle,
        query_id=query_id,
    )


def listar(
    conn: psycopg.Connection, alerta_id: str | None, tipo: LogEventType | None
) -> list[LogEvent]:
    condiciones = []
    parametros: list[str] = []
    if alerta_id is not None:
        condiciones.append("alerta_id = %s")
        parametros.append(alerta_id)
    if tipo is not None:
        condiciones.append("tipo = %s")
        parametros.append(tipo)
    donde = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    filas = conn.execute(
        f"SELECT id, alerta_id, tipo, actor, detalle, query_id, dia_simulado, creado_en "
        f"FROM api.bitacora {donde} ORDER BY creado_en DESC",
        parametros,
    ).fetchall()
    return [_a_evento(fila) for fila in filas]


def _a_evento(fila: tuple) -> LogEvent:
    id, alerta_id, tipo, actor, detalle, query_id, dia_simulado, creado_en = fila
    return LogEvent(
        id=str(id),
        date=creado_en.isoformat(),
        simulated_day=dia_simulado.isoformat(),
        alert_id=alerta_id,
        type=tipo,
        actor=actor,
        detail=detalle,
        query_id=query_id,
    )
