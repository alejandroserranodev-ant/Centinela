from urllib.parse import unquote

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException

from .. import alertas as alertas_repo
from .. import bitacora, decisiones, simulacion
from ..ciclo_vida import ESTADO_A_STATUS
from ..config import ROLES_CON_DECISION
from ..db import obtener_conexion
from ..modelos import ActorPerson, Alert, Decision

router = APIRouter()


@router.get("/alertas", response_model=list[Alert])
async def listar(
    estado: str | None = None, conn: psycopg.Connection = Depends(obtener_conexion)
) -> list[Alert]:
    status = None
    if estado is not None:
        status = ESTADO_A_STATUS.get(estado)
        if status is None:
            raise HTTPException(422, f"estado desconocido: {estado}")
    return alertas_repo.listar(conn, status)


@router.get("/alertas/{id}", response_model=Alert)
async def obtener(id: str, conn: psycopg.Connection = Depends(obtener_conexion)) -> Alert:
    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "No existe esa alerta")
    return alerta


@router.post("/alertas/{id}/decision", response_model=Alert)
async def decidir(
    id: str,
    decision: Decision,
    x_user_name: str = Header(...),
    x_user_role: str = Header(...),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> Alert:
    if x_user_role not in ROLES_CON_DECISION:
        raise HTTPException(403, "Este rol no puede decidir sobre una alerta")
    alerta = alertas_repo.obtener(conn, id)
    if alerta is None:
        raise HTTPException(404, "No existe esa alerta")

    try:
        nueva, eventos = decisiones.aplicar(alerta, decision)
    except decisiones.ConflictoEstado as e:
        raise HTTPException(409, str(e)) from e
    except decisiones.DecisionInvalida as e:
        raise HTTPException(422, str(e)) from e

    actor = ActorPerson(name=unquote(x_user_name), role=x_user_role)
    with conn.transaction():
        alertas_repo.guardar(conn, nueva)
        dia = simulacion.dia_actual(conn)
        for tipo, detalle in eventos:
            bitacora.registrar(conn, nueva.id, tipo, actor, detalle, dia)
    return nueva
