import datetime
from collections.abc import Sequence

import psycopg
from psycopg.types.json import Jsonb

from centinela_agents.growth import Rejection


def registrar(conn: psycopg.Connection, alerta_id: str, metrica: str, destino: str, acciones: Sequence[str], motivo: str, dia: datetime.date) -> None:
    conn.execute(
        "INSERT INTO api.rechazos (alerta_id, metrica, destino, acciones, motivo, dia_simulado) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (alerta_id) DO NOTHING",
        (alerta_id, metrica, destino, Jsonb(list(acciones)), motivo, dia),
    )


def listar(conn: psycopg.Connection) -> list[Rejection]:
    filas = conn.execute("SELECT alerta_id, metrica, destino, acciones FROM api.rechazos ORDER BY creado_en").fetchall()
    return [Rejection(alerta_id, metrica, destino, tuple(acciones)) for alerta_id, metrica, destino, acciones in filas]
