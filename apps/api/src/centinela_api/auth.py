import base64
import binascii
import hashlib
import hmac
import json
import os
import sys
import time

from fastapi import Header, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from .config import AUTH_SECRET_KEY, CENTINELA_USUARIOS
from .modelos import Persona, Role

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 600_000
VIGENCIA_S = 8 * 3600
SIN_SESION = "Inicia sesión para continuar"
FICTICIA = f"{ALGORITMO}${ITERACIONES}${base64.b64encode(bytes(16)).decode()}${base64.b64encode(bytes(32)).decode()}"


class Perfil(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    correo: str
    nombre: str
    rol: Role
    area: str | None = None
    clave: str

    @field_validator("correo")
    @classmethod
    def minusculas(cls, correo: str) -> str:
        return correo.strip().lower()

    @field_validator("clave")
    @classmethod
    def cifrada(cls, clave: str) -> str:
        partes = clave.split("$")
        try:
            legible = len(partes) == 4 and partes[0] == ALGORITMO and int(partes[1]) == ITERACIONES
            legible = legible and bool(base64.b64decode(partes[2], validate=True)) and bool(base64.b64decode(partes[3], validate=True))
        except (ValueError, binascii.Error):
            legible = False
        if not legible:
            raise ValueError(f"la clave debe ser {ALGORITMO}${ITERACIONES}$<sal>$<hash>, escrita por python -m centinela_api.auth hash")
        return clave

    def persona(self) -> Persona:
        return Persona(email=self.correo, name=self.nombre, role=self.rol, area=self.area)


def cargar(texto: str) -> dict[str, Perfil]:
    if not texto.strip():
        return {}
    try:
        perfiles = [Perfil.model_validate(p) for p in json.loads(texto)]
    except (json.JSONDecodeError, TypeError, ValidationError) as error:
        raise RuntimeError(f"CENTINELA_USUARIOS no es una lista JSON de perfiles válida: {error}") from error
    correos = [p.correo for p in perfiles]
    if len(set(correos)) != len(correos):
        raise RuntimeError("CENTINELA_USUARIOS repite un correo")
    return {p.correo: p for p in perfiles}


PERFILES = cargar(CENTINELA_USUARIOS)


def cifrar(clave: str, iteraciones: int = ITERACIONES, sal: bytes | None = None) -> str:
    sal = sal if sal is not None else os.urandom(16)
    resumen = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, iteraciones)
    return f"{ALGORITMO}${iteraciones}${base64.b64encode(sal).decode()}${base64.b64encode(resumen).decode()}"


def coincide(clave: str, cifrada: str) -> bool:
    _, iteraciones, sal, resumen = cifrada.split("$")
    calculado = hashlib.pbkdf2_hmac("sha256", clave.encode(), base64.b64decode(sal), int(iteraciones))
    return hmac.compare_digest(calculado, base64.b64decode(resumen))


def verificar(correo: str, clave: str) -> Persona | None:
    perfil = PERFILES.get(correo.strip().lower())
    valida = coincide(clave, perfil.clave if perfil else FICTICIA)
    return perfil.persona() if perfil and valida else None


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firma(carga: str) -> str:
    return _b64(hmac.new(AUTH_SECRET_KEY, carga.encode(), hashlib.sha256).digest())


def emitir(persona: Persona, ahora: float | None = None) -> str:
    vence = int((ahora if ahora is not None else time.time()) + VIGENCIA_S)
    carga = _b64(json.dumps({"correo": persona.email, "exp": vence}, separators=(",", ":")).encode())
    return f"{carga}.{_firma(carga)}"


def leer(token: str, ahora: float | None = None) -> Persona | None:
    carga, _, firma = token.partition(".")
    if not carga or not hmac.compare_digest(firma.encode(), _firma(carga).encode()):
        return None
    try:
        datos = json.loads(_de_b64(carga))
        correo, vence = str(datos["correo"]), float(datos["exp"])
    except (binascii.Error, ValueError, KeyError, TypeError):
        return None
    if vence <= (ahora if ahora is not None else time.time()):
        return None
    perfil = PERFILES.get(correo)
    return perfil.persona() if perfil else None


def persona_actual(authorization: str | None = Header(None)) -> Persona:
    esquema, _, token = (authorization or "").partition(" ")
    persona = leer(token.strip()) if esquema.lower() == "bearer" else None
    if persona is None:
        raise HTTPException(401, SIN_SESION, headers={"WWW-Authenticate": "Bearer"})
    return persona


if __name__ == "__main__":
    if sys.argv[1:] != ["hash"]:
        sys.exit("uso: python -m centinela_api.auth hash < clave")
    print(cifrar(sys.stdin.readline().rstrip("\n")))
