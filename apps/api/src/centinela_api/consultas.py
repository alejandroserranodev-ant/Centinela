from collections.abc import Iterable, Mapping
from typing import Any

import psycopg

from .modelos import Query


def registrar(conn: psycopg.Connection, consultas: Iterable[Any]) -> None:
    for consulta in consultas:
        if not isinstance(consulta, Mapping) or not consulta.get("queryId"):
            continue
        conn.execute(
            "INSERT INTO api.consultas (query_id, kpi, dia, consulta) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (query_id) DO NOTHING",
            (consulta["queryId"], consulta["kpi"], consulta["dia"], consulta["consulta"]),
        )


def obtener(conn: psycopg.Connection, query_id: str) -> Query | None:
    fila = conn.execute(
        "SELECT query_id, kpi, dia, consulta FROM api.consultas WHERE query_id = %s", (query_id,)
    ).fetchone()
    if fila is None:
        return None
    id, kpi, dia, consulta = fila
    return Query(id=id, sql=consulta, description=f"KPI {kpi} del {dia.isoformat()}")
