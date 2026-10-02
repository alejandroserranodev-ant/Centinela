import datetime

import psycopg


def dia_actual(conn: psycopg.Connection) -> datetime.date:
    fila = conn.execute("SELECT dia_actual FROM api.simulacion LIMIT 1").fetchone()
    if fila:
        return fila[0]
    inicial = conn.execute("SELECT centinela.fecha_corte()").fetchone()[0]
    conn.execute("INSERT INTO api.simulacion (dia_actual) VALUES (%s)", (inicial,))
    return inicial


def avanzar(conn: psycopg.Connection, dias: int) -> datetime.date:
    actual = dia_actual(conn)
    siguiente = actual + datetime.timedelta(days=dias)
    conn.execute("UPDATE api.simulacion SET dia_actual = %s", (siguiente,))
    return siguiente
