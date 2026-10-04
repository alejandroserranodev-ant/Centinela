import datetime
import decimal
import json
from collections.abc import Iterable, Mapping
from typing import Any

import psycopg
from centinela_agents.evidence import unit_of
from psycopg.types.json import Jsonb

from .agentes import etiqueta
from .modelos import Query

DESCRIPCION_ALERTAS = {
    "bandeja_pesos_en_riesgo": "Suma de pesos en riesgo de las alertas propuestas",
    "bandeja_recuperable_mes": "Suma de pesos recuperables al mes de las alertas propuestas",
    "bandeja_decisiones_pendientes": "Cantidad de alertas propuestas que esperan una decisión",
}


def _plano(valor: Any) -> Any:
    if isinstance(valor, decimal.Decimal):
        return float(valor)
    if isinstance(valor, (datetime.date, datetime.datetime)):
        return valor.isoformat()
    return str(valor)


def registrar(conn: psycopg.Connection, consultas: Iterable[Any]) -> None:
    for consulta in consultas:
        if not isinstance(consulta, Mapping) or not consulta.get("queryId"):
            continue
        conn.execute(
            "INSERT INTO api.consultas (query_id, kpi, dia, consulta, fuente, filas) VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (query_id) DO NOTHING",
            (
                consulta["queryId"], consulta["kpi"], consulta["dia"], consulta["consulta"], consulta.get("fuente", "kernel"),
                Jsonb(list(consulta.get("filas") or []), dumps=lambda filas: json.dumps(filas, default=_plano)),
            ),
        )


def obtener(conn: psycopg.Connection, query_id: str) -> Query | None:
    fila = conn.execute(
        "SELECT query_id, kpi, dia, consulta, fuente, filas FROM api.consultas WHERE query_id = %s", (query_id,)
    ).fetchone()
    if fila is None:
        return None
    id, kpi, dia, consulta, fuente, filas = fila
    if fuente == "alertas":
        descripcion = f"{DESCRIPCION_ALERTAS[kpi]}, día {dia.isoformat()}"
    else:
        descripcion = f"{etiqueta(kpi)} del {dia.isoformat()}"
    numericas = {columna for f in filas for columna, valor in f.items() if isinstance(valor, (int, float)) and not isinstance(valor, bool)}
    return Query(id=id, source=fuente, sql=consulta, description=descripcion, rows=filas, units={columna: unit_of(columna) for columna in sorted(numericas)})
