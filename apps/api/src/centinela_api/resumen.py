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
        "SELECT id, cuerpo->>'metric' AS metrica,\n"
        "       (cuerpo->'pesosAtRisk'->>'value')::numeric AS pesos_en_riesgo\n"
        "FROM api.alertas\nWHERE status = 'proposed'\nORDER BY pesos_en_riesgo DESC",
    ),
    (
        "bandeja_recuperable_mes",
        "COP",
        "SELECT coalesce(sum(coalesce((cuerpo->'recoverablePerMonth'->>'value')::numeric, 0)), 0)\n"
        "FROM api.alertas\nWHERE status = 'proposed'",
        "SELECT id, cuerpo->>'metric' AS metrica,\n"
        "       coalesce((cuerpo->'recoverablePerMonth'->>'value')::numeric, 0) AS valor_recuperable_mes\n"
        "FROM api.alertas\nWHERE status = 'proposed'\nORDER BY valor_recuperable_mes DESC",
    ),
    (
        "bandeja_decisiones_pendientes",
        "units",
        "SELECT count(*)\nFROM api.alertas\nWHERE status = 'proposed'",
        "SELECT id, cuerpo->>'metric' AS metrica\n"
        "FROM api.alertas\nWHERE status = 'proposed'",
    ),
)


def calcular(conn: psycopg.Connection) -> InboxSummary:
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        dia = simulacion.dia_actual(conn)
        resultados = []
        for _, _, sql_agg, sql_det in TOTALES:
            valor = float(conn.execute(sql_agg).fetchone()[0])
            cur = conn.execute(sql_det)
            cols = [d[0] for d in cur.description]
            filas = [dict(zip(cols, row)) for row in cur.fetchall()]
            resultados.append((valor, filas))
    cifras = []
    for (kpi, unidad, sql_agg, _), (valor, filas) in zip(TOTALES, resultados):
        id = "q_" + hashlib.sha256(f"{sql_agg}|{dia.isoformat()}|{valor}".encode()).hexdigest()[:12]
        with conn.transaction():
            consultas.registrar(
                conn,
                [{"queryId": id, "kpi": kpi, "dia": dia, "consulta": sql_agg, "fuente": "alertas", "filas": filas}],
            )
        cifras.append(Figure(value=valor, unit=unidad, query_id=id))
    return InboxSummary(
        money_at_risk=cifras[0], recoverable_per_month=cifras[1], pending_decisions=cifras[2]
    )
