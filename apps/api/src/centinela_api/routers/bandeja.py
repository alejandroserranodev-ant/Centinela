import psycopg
from fastapi import APIRouter, Depends

from .. import resumen
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import InboxSummary

router = APIRouter(tags=["inbox"], dependencies=[Depends(persona_actual)])


@router.get("/bandeja/resumen", response_model=InboxSummary)
async def totales(conn: psycopg.Connection = Depends(obtener_conexion)) -> InboxSummary:
    """The inbox totals over the proposed alerts, each with the query that produced it."""
    return resumen.calcular(conn)
