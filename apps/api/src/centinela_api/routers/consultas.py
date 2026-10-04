import psycopg
from fastapi import APIRouter, Depends, HTTPException

from .. import consultas as consultas_repo
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import Query

router = APIRouter(tags=["queries"], dependencies=[Depends(persona_actual)])


@router.get("/consultas/{query_id}", response_model=Query)
async def obtener(query_id: str, conn: psycopg.Connection = Depends(obtener_conexion)) -> Query:
    """The query that produced a figure, as the API recorded it when the figure was cited."""
    consulta = consultas_repo.obtener(conn, query_id)
    if consulta is None:
        raise HTTPException(404, "No existe esa consulta")
    return consulta
