"""
Exports the API's OpenAPI document, with the SSE payloads no route declares,
to the file the web generates its TypeScript types from.
Run as `python -m centinela_api.contrato`.
"""
import json
from pathlib import Path

from pydantic.json_schema import models_json_schema

from .config import RAIZ
from .main import app
from .modelos import AdvanceEnd, AgentStep, ChatMessage

DESTINO = RAIZ / "apps" / "web" / "src" / "api" / "openapi.json"
REFERENCIAS = "#/components/schemas/{model}"


def esquema() -> dict:
    documento = app.openapi()
    _, definiciones = models_json_schema(
        [(modelo, "serialization") for modelo in (AgentStep, ChatMessage, AdvanceEnd)],
        by_alias=True,
        ref_template=REFERENCIAS,
    )
    esquemas = documento.setdefault("components", {}).setdefault("schemas", {})
    for nombre, definicion in definiciones.get("$defs", {}).items():
        esquemas.setdefault(nombre, definicion)
    return json.loads(json.dumps(documento))


def exportar(destino: Path = DESTINO) -> None:
    destino.write_text(json.dumps(esquema(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    exportar()
