import asyncio

from fastapi import APIRouter, Depends, HTTPException

from .. import auth
from ..modelos import Credenciales, Persona, Sesion

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Sesion)
async def login(credenciales: Credenciales) -> Sesion:
    persona = await asyncio.to_thread(auth.verificar, credenciales.email, credenciales.password)
    if persona is None:
        raise HTTPException(401, "Correo o contraseña incorrectos")
    return Sesion(token=auth.emitir(persona), persona=persona)


@router.get("/sesion", response_model=Persona)
async def sesion(persona: Persona = Depends(auth.persona_actual)) -> Persona:
    return persona
