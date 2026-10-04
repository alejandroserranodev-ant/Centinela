import psycopg
from fastapi import APIRouter, Depends, HTTPException

from .. import configuracion, permisos
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import Persona, Settings

router = APIRouter(tags=["settings"], dependencies=[Depends(persona_actual)])

SOLO_QUIEN_CONFIGURA = "La configuración la cambian la analista o la gerencia"


@router.get("/configuracion", response_model=Settings)
async def leer(conn: psycopg.Connection = Depends(obtener_conexion)) -> Settings:
    return configuracion.leer(conn)


@router.put("/configuracion", response_model=Settings)
async def guardar(
    ajustes: Settings,
    persona: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> Settings:
    if not permisos.puede_configurar(persona):
        raise HTTPException(403, SOLO_QUIEN_CONFIGURA)
    try:
        return configuracion.guardar(conn, ajustes, persona)
    except configuracion.ConfiguracionInvalida as e:
        raise HTTPException(422, str(e)) from e
