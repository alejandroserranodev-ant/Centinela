import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from .. import alertas as alertas_repo
from .. import arboles, permisos, simulacion
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import Persona, RetireExpansion, TreeExpansion

router = APIRouter(tags=["tree"], dependencies=[Depends(persona_actual)])

SOLO_QUIEN_RETIRA = "Los cambios del árbol los retiran la analista o la gerencia"
SIN_MOTIVO = "Para retirar un cambio del árbol hace falta un motivo"
YA_NO_APLICA = "Ese cambio del árbol ya no se aplica, así que no hay nada que retirar"
NO_ADMITE = "El árbol no admite ese retiro, porque dejaría de cumplir sus reglas"

logger = logging.getLogger(__name__)


def _titulos(conn: psycopg.Connection) -> dict:
    return {alerta.id: alerta.title for alerta in alertas_repo.listar(conn, None)}


@router.get("/arbol/expansiones", response_model=list[TreeExpansion])
async def listar(conn: psycopg.Connection = Depends(obtener_conexion)) -> list[TreeExpansion]:
    return arboles.expansiones(arboles.versiones(conn), _titulos(conn))


@router.post("/arbol/expansiones/{id}/retiro", response_model=TreeExpansion)
async def retirar(
    id: int,
    retiro: RetireExpansion,
    persona: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> TreeExpansion:
    if not permisos.puede_retirar(persona):
        raise HTTPException(403, SOLO_QUIEN_RETIRA)
    if not retiro.reason.strip():
        raise HTTPException(422, SIN_MOTIVO)
    try:
        return arboles.retirar(conn, id, retiro.reason, persona, simulacion.dia_actual(conn), _titulos(conn))
    except arboles.ExpansionDesconocida as e:
        raise HTTPException(404, "No existe ese cambio del árbol") from e
    except arboles.YaRetirada as e:
        raise HTTPException(409, "Ese cambio del árbol ya está retirado") from e
    except arboles.YaNoAplica as e:
        raise HTTPException(422, YA_NO_APLICA) from e
    except arboles.RetiroRechazado as e:
        logger.warning("Retiring version %s was refused: %s", id, e.problemas)
        raise HTTPException(422, NO_ADMITE) from e
