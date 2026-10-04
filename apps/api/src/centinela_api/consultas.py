from collections.abc import Iterable, Mapping
from typing import Any

import psycopg

from .modelos import Query

DESCRIPCION_ALERTAS = {
    "bandeja_pesos_en_riesgo": "Suma de pesos en riesgo de las alertas propuestas",
    "bandeja_recuperable_mes": "Suma de pesos recuperables al mes de las alertas propuestas",
    "bandeja_decisiones_pendientes": "Cantidad de alertas propuestas que esperan una decisión",
}


def registrar(conn: psycopg.Connection, consultas: Iterable[Any]) -> None:
    for consulta in consultas:
        if not isinstance(consulta, Mapping) or not consulta.get("queryId"):
            continue
        conn.execute(
            "INSERT INTO api.consultas (query_id, kpi, dia, consulta, fuente) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (query_id) DO NOTHING",
            (consulta["queryId"], consulta["kpi"], consulta["dia"], consulta["consulta"], consulta.get("fuente", "kernel")),
        )


def obtener(conn: psycopg.Connection, query_id: str) -> Query | None:
    fila = conn.execute(
        "SELECT query_id, kpi, dia, consulta, fuente FROM api.consultas WHERE query_id = %s", (query_id,)
    ).fetchone()
    if fila is None:
        return None
    id, kpi, dia, consulta, fuente = fila
    if fuente == "alertas":
        descripcion = f"{DESCRIPCION_ALERTAS[kpi]}, día {dia.isoformat()}"
    else:
        descripcion = f"KPI {kpi} del {dia.isoformat()}"
    return Query(id=id, source=fuente, sql=consulta, description=descripcion)
