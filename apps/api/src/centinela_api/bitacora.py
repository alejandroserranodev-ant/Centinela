import datetime

import psycopg
from psycopg.types.json import Jsonb

from collections.abc import Mapping, Sequence

from .modelos import Actor, Figure, LogEvent, LogEventType


def registrar(
    conn: psycopg.Connection,
    alerta_id: str | None,
    tipo: LogEventType,
    actor: Actor,
    detalle: str,
    dia_simulado: datetime.date,
    query_id: str | None = None,
    figures: Sequence[Figure] = (),
) -> LogEvent:
    figuras = [figura.model_dump(by_alias=True) for figura in figures]
    fila = conn.execute(
        "INSERT INTO api.bitacora (alerta_id, tipo, actor, detalle, query_id, dia_simulado, figuras) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, creado_en",
        (alerta_id, tipo, Jsonb(actor.model_dump(by_alias=True)), detalle, query_id, dia_simulado, Jsonb(figuras)),
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
        figures=list(figures),
    )


def registrar_costo(conn: psycopg.Connection, alerta_id: str | None, actor: Actor, detalle: str, dia_simulado: datetime.date) -> None:
    conn.execute(
        "INSERT INTO api.bitacora (alerta_id, tipo, actor, detalle, dia_simulado) VALUES (%s, 'costo', %s, %s, %s)",
        (alerta_id, Jsonb(actor.model_dump(by_alias=True)), detalle, dia_simulado),
    )


def registrar_prompts(conn: psycopg.Connection, alerta_id: str | None, prompts: Sequence[Mapping[str, str]], dia_simulado: datetime.date) -> None:
    for prompt in prompts:
        conn.execute(
            "INSERT INTO api.bitacora (alerta_id, tipo, actor, detalle, dia_simulado) VALUES (%s, 'prompt', %s, %s, %s)",
            (alerta_id, Jsonb({"kind": "agent", "agent": prompt["agent"]}), detalle_de_prompt(prompt), dia_simulado),
        )


def detalle_de_prompt(prompt: Mapping[str, str]) -> str:
    return f"{prompt['agent']}\n--- system\n{prompt['system']}\n--- user\n{prompt['user']}"


def listar(
    conn: psycopg.Connection, alerta_id: str | None, tipo: LogEventType | None
) -> list[LogEvent]:
    condiciones = ["tipo NOT IN ('costo', 'prompt')"]
    parametros: list[str] = []
    if alerta_id is not None:
        condiciones.append("alerta_id = %s")
        parametros.append(alerta_id)
    if tipo is not None:
        condiciones.append("tipo = %s")
        parametros.append(tipo)
    donde = f"WHERE {' AND '.join(condiciones)}"
    filas = conn.execute(
        f"SELECT id, alerta_id, tipo, actor, detalle, query_id, dia_simulado, creado_en, figuras "
        f"FROM api.bitacora {donde} ORDER BY creado_en DESC",
        parametros,
    ).fetchall()
    return [_a_evento(fila) for fila in filas]


def _a_evento(fila: tuple) -> LogEvent:
    id, alerta_id, tipo, actor, detalle, query_id, dia_simulado, creado_en, figuras = fila
    return LogEvent(
        id=str(id),
        date=creado_en.isoformat(),
        simulated_day=dia_simulado.isoformat(),
        alert_id=alerta_id,
        type=tipo,
        actor=actor,
        detail=detalle,
        query_id=query_id,
        figures=figuras,
    )
