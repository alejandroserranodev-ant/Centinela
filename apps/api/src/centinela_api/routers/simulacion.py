import psycopg
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from .. import simulacion
from ..db import obtener_conexion
from ..modelos import SimulatedDay
from ..sse import flujo

router = APIRouter()


@router.get("/simulacion/dia-actual", response_model=SimulatedDay)
async def dia_actual(conn: psycopg.Connection = Depends(obtener_conexion)) -> SimulatedDay:
    """
    Get the current simulated day.
    Used by Vigía to know what date to filter queries by.
    """
    dia = simulacion.dia_actual(conn)
    return SimulatedDay(dia=dia.isoformat())


@router.post("/simulacion/avanzar")
async def avanzar(
    dias: int = Query(1, ge=1), conn: psycopg.Connection = Depends(obtener_conexion)
) -> StreamingResponse:
    async def eventos():
        with conn.transaction():
            nuevo_dia = simulacion.avanzar(conn, dias)
        yield "end", {"simulatedDay": nuevo_dia.isoformat(), "newAlerts": []}

    return StreamingResponse(flujo(eventos()), media_type="text/event-stream")
