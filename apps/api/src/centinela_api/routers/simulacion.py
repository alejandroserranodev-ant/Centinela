import psycopg
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from .. import simulacion
from ..db import obtener_conexion
from ..sse import flujo

router = APIRouter()


@router.post("/simulacion/avanzar")
async def avanzar(
    dias: int = Query(1, ge=1), conn: psycopg.Connection = Depends(obtener_conexion)
) -> StreamingResponse:
    async def eventos():
        with conn.transaction():
            nuevo_dia = simulacion.avanzar(conn, dias)
        yield "end", {"simulatedDay": nuevo_dia.isoformat(), "newAlerts": []}

    return StreamingResponse(flujo(eventos()), media_type="text/event-stream")
