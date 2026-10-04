import hashlib

import psycopg

from . import consultas, simulacion
from .modelos import Figure, InboxSummary

TOTALES = (
    (
        "bandeja_pesos_en_riesgo",
        "COP",
        "SELECT coalesce(sum((cuerpo->'pesosAtRisk'->>'value')::numeric), 0)\n"
        "FROM api.alertas\nWHERE status = 'proposed'",
    ),
    (
        "bandeja_recuperable_mes",
        "COP",
        "SELECT coalesce(sum(coalesce((cuerpo->'recoverablePerMonth'->>'value')::numeric, 0)), 0)\n"
        "FROM api.alertas\nWHERE status = 'proposed'",
    ),
    (
        "bandeja_decisiones_pendientes",
        "units",
        "SELECT count(*)\nFROM api.alertas\nWHERE status = 'proposed'",
    ),
)


def calcular(conn: psycopg.Connection) -> InboxSummary:
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        dia = simulacion.dia_actual(conn)
        valores = [float(conn.execute(sql).fetchone()[0]) for _, _, sql in TOTALES]
    cifras = []
    for (kpi, unidad, sql), valor in zip(TOTALES, valores):
        id = "q_" + hashlib.sha256(f"{sql}|{dia.isoformat()}|{valor}".encode()).hexdigest()[:12]
        with conn.transaction():
            consultas.registrar(
                conn,
                [{"queryId": id, "kpi": kpi, "dia": dia, "consulta": sql, "fuente": "alertas"}],
            )
        cifras.append(Figure(value=valor, unit=unidad, query_id=id))
    return InboxSummary(
        money_at_risk=cifras[0], recoverable_per_month=cifras[1], pending_decisions=cifras[2]
    )
