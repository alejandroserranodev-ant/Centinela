import json

import psycopg
from psycopg.types.json import Jsonb

from .modelos import Alert, AlertStatus, MergedAlert


def listar(conn: psycopg.Connection, status: AlertStatus | None) -> list[Alert]:
    if status is None:
        filas = conn.execute(
            "SELECT id, status, cuerpo FROM api.alertas WHERE status <> 'merged' "
            "ORDER BY (cuerpo->'pesosAtRisk'->>'value')::numeric DESC"
        ).fetchall()
    else:
        filas = conn.execute(
            "SELECT id, status, cuerpo FROM api.alertas WHERE status = %s "
            "ORDER BY (cuerpo->'pesosAtRisk'->>'value')::numeric DESC",
            (status,),
        ).fetchall()
    return [_a_alerta(fila) for fila in filas]


def anteriores(conn: psycopg.Connection) -> list[tuple[Alert, list | None]]:
    filas = conn.execute("SELECT id, status, cuerpo, entidad FROM api.alertas").fetchall()
    return [(_a_alerta(fila[:3]), fila[3]) for fila in filas]


def fijar_entidad(conn: psycopg.Connection, id: str, entidad) -> None:
    conn.execute("UPDATE api.alertas SET entidad = %s WHERE id = %s", (Jsonb(json.loads(json.dumps(list(entidad), default=str))), id))


def fijar_costo(conn: psycopg.Connection, id: str, costo) -> None:
    conn.execute("UPDATE api.alertas SET costos = %s WHERE id = %s", (Jsonb(dict(costo)), id))


def obtener(conn: psycopg.Connection, id: str, *, bloquear: bool = False) -> Alert | None:
    fila = conn.execute(
        "SELECT id, status, cuerpo FROM api.alertas WHERE id = %s" + (" FOR UPDATE" if bloquear else ""), (id,)
    ).fetchone()
    return _a_alerta(fila) if fila else None


def guardar(conn: psycopg.Connection, alerta: Alert) -> Alert:
    with conn.transaction():
        fila = conn.execute(
            "SELECT cuerpo->'mergedAlerts' FROM api.alertas WHERE id = %s FOR UPDATE", (alerta.id,)
        ).fetchone()
        propias = {unida.id for unida in alerta.merged_alerts}
        guardadas = [MergedAlert.model_validate(m) for m in ((fila[0] if fila else None) or []) if m.get("id") not in propias]
        if guardadas:
            alerta = alerta.model_copy(update={"merged_alerts": [*guardadas, *alerta.merged_alerts]})
        _escribir(conn, alerta)
    return alerta


def _escribir(conn: psycopg.Connection, alerta: Alert) -> None:
    cuerpo = alerta.model_dump(by_alias=True, exclude={"id", "status", "decided_by", "can_decide"})
    conn.execute(
        "INSERT INTO api.alertas (id, status, cuerpo) VALUES (%s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET status = excluded.status, cuerpo = excluded.cuerpo, "
        "actualizado_en = now()",
        (alerta.id, alerta.status, Jsonb(cuerpo)),
    )


def _a_alerta(fila: tuple) -> Alert:
    id, status, cuerpo = fila
    return Alert.model_validate({**cuerpo, "id": id, "status": status})
