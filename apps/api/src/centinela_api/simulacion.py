import datetime
import os

import psycopg

DIAS_DE_DEMO = "CENTINELA_DIAS_DE_DEMO"


def dia_actual(conn: psycopg.Connection) -> datetime.date:
    fila = conn.execute("SELECT dia_actual FROM api.simulacion LIMIT 1").fetchone()
    if fila:
        return fila[0]
    inicial = ultimo_dia(conn) - datetime.timedelta(days=int(os.environ.get(DIAS_DE_DEMO, "30")))
    conn.execute("INSERT INTO api.simulacion (dia_actual) VALUES (%s)", (inicial,))
    return inicial


def ultimo_dia(conn: psycopg.Connection) -> datetime.date:
    return conn.execute("SELECT centinela.fecha_corte()").fetchone()[0]


def sin_datos(conn: psycopg.Connection, dias: int) -> str | None:
    ultimo = ultimo_dia(conn)
    if dia_actual(conn) + datetime.timedelta(days=dias) <= ultimo:
        return None
    return f"Los datos llegan hasta el {ultimo.isoformat()}: no hay un día siguiente que revisar"


def avanzar(conn: psycopg.Connection, dias: int) -> datetime.date:
    actual = dia_actual(conn)
    siguiente = actual + datetime.timedelta(days=dias)
    conn.execute("UPDATE api.simulacion SET dia_actual = %s", (siguiente,))
    return siguiente
