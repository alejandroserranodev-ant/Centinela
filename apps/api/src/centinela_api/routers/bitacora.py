import psycopg
from fastapi import APIRouter, Depends, Query

from .. import bitacora as bitacora_repo
from ..db import obtener_conexion
from ..modelos import LogEvent, LogEventType

router = APIRouter()


@router.get("/bitacora", response_model=list[LogEvent])
async def listar(
    alertId: str | None = Query(None, description="Filter by alert ID (UUID-like identifier)"),
    type: LogEventType | None = Query(None, description="Filter by event type"),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> list[LogEvent]:
    """Get audit log (bitácora) of alert lifecycle events, optionally filtered by alert and event type."""
    return bitacora_repo.listar(conn, alertId, type)
