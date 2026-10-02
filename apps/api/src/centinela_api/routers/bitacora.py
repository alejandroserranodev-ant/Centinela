import psycopg
from fastapi import APIRouter, Depends

from .. import bitacora as bitacora_repo
from ..db import obtener_conexion
from ..modelos import LogEvent, LogEventType

router = APIRouter()


@router.get("/bitacora", response_model=list[LogEvent])
async def listar(
    alertId: str | None = None,
    type: LogEventType | None = None,
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> list[LogEvent]:
    return bitacora_repo.listar(conn, alertId, type)
