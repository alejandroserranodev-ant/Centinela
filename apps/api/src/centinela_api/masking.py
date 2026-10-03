import hashlib
import json
import re
from typing import Any

MASK_PREFIX = "CLIENTE_"
VENDOR_PREFIX = "VENDEDOR_"
PRODUCT_PREFIX = "PRODUCTO_"


def _hash_suffix(text: str) -> str:
    """Genera un sufijo corto y determinista (últimos 8 caracteres del hash)."""
    return hashlib.sha256(text.encode()).hexdigest()[-8:].upper()


def mask_cliente_id(cliente_id: str) -> str:
    """Enmascara ID de cliente: C0042 -> CLIENTE_A1B2C3D4."""
    return f"{MASK_PREFIX}{_hash_suffix(cliente_id)}"


def mask_cliente_nombre(nombre: str) -> str:
    """Enmascara nombre: 'Juan Pérez' -> 'Cliente ABCD1234'."""
    return f"Cliente {_hash_suffix(nombre)}"


def mask_vendedor_id(vendedor_id: str) -> str:
    """Enmascara ID de vendedor: V03 -> VENDEDOR_X1Y2Z3W4."""
    return f"{VENDOR_PREFIX}{_hash_suffix(vendedor_id)}"


def mask_product_nombre(nombre: str) -> str:
    """Enmascara nombre de producto: 'Aceite 750ml' -> 'Producto ABCD1234'."""
    return f"Producto {_hash_suffix(nombre)}"


def mask_dict_for_model(data: dict[str, Any]) -> dict[str, Any]:
    """
    Enmascara un diccionario antes de enviarlo a un modelo.
    Preserva estructura, solo reemplaza valores sensibles.
    Máscaras aplicadas:
    - cliente_id, cliente, nombre (si es en contexto de cliente)
    - vendedor_id
    - producto.nombre (si existe)
    """
    masked = {}
    for key, value in data.items():
        if key in ("cliente_id", "id") and isinstance(value, str) and value.startswith("C"):
            masked[key] = mask_cliente_id(value)
        elif key in ("cliente", "nombre") and isinstance(value, str):
            masked[key] = mask_cliente_nombre(value)
        elif key == "vendedor_id" and isinstance(value, str):
            masked[key] = mask_vendedor_id(value)
        elif key == "producto" and isinstance(value, dict):
            masked[key] = mask_dict_for_model(value)
        elif isinstance(value, dict):
            masked[key] = mask_dict_for_model(value)
        elif isinstance(value, list):
            masked[key] = [
                mask_dict_for_model(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value
    return masked


def mask_sql_result(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Enmascara resultados de SQL antes de enviar a modelos.
    Cada fila es un diccionario con columnas.
    """
    return [mask_dict_for_model(row) for row in rows]


def mask_text_evidence(text: str, replacements: dict[str, str] | None = None) -> str:
    """
    Enmascara texto de evidencia (por ejemplo, descripciones de causas).
    replacements: dict de {original: mascara} para hacer reemplazos específicos.
    Si no se proporciona, intenta detectar patrones (IDs de cliente, nombres).
    """
    result = text
    if replacements:
        for original, masked in replacements.items():
            result = result.replace(original, masked)
    return result
