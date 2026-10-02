import psycopg
from psycopg.types.json import Jsonb

from .modelos import Alert, AlertStatus


def listar(conn: psycopg.Connection, status: AlertStatus | None) -> list[Alert]:
    if status is None:
        filas = conn.execute(
            "SELECT id, status, cuerpo FROM api.alertas "
            "ORDER BY (cuerpo->'pesosAtRisk'->>'value')::numeric DESC"
        ).fetchall()
    else:
        filas = conn.execute(
            "SELECT id, status, cuerpo FROM api.alertas WHERE status = %s "
            "ORDER BY (cuerpo->'pesosAtRisk'->>'value')::numeric DESC",
            (status,),
        ).fetchall()
    return [_a_alerta(fila) for fila in filas]


def obtener(conn: psycopg.Connection, id: str) -> Alert | None:
    fila = conn.execute(
        "SELECT id, status, cuerpo FROM api.alertas WHERE id = %s", (id,)
    ).fetchone()
    return _a_alerta(fila) if fila else None


def guardar(conn: psycopg.Connection, alerta: Alert) -> None:
    cuerpo = alerta.model_dump(by_alias=True, exclude={"id", "status"})
    conn.execute(
        "INSERT INTO api.alertas (id, status, cuerpo) VALUES (%s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET status = excluded.status, cuerpo = excluded.cuerpo, "
        "actualizado_en = now()",
        (alerta.id, alerta.status, Jsonb(cuerpo)),
    )


def _a_alerta(fila: tuple) -> Alert:
    id, status, cuerpo = fila
    return Alert.model_validate({**cuerpo, "id": id, "status": status})
