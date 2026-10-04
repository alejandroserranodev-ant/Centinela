from collections.abc import Iterator

import psycopg

from . import config


def conectar() -> psycopg.Connection:
    if not config.DSN_ADMIN:
        raise RuntimeError("DSN_ADMIN no está configurado; defínelo en el .env de la raíz")
    return psycopg.connect(config.DSN_ADMIN, autocommit=True)


def obtener_conexion() -> Iterator[psycopg.Connection]:
    with conectar() as conn:
        yield conn
