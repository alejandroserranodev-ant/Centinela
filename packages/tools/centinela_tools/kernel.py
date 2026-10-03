import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping

import psycopg
from jsonschema import Draft202012Validator

from . import tools
from .language import refuse_first
from .paths import METRICAS
from .refusal import Refused
from .settings import Settings
from .sources import Sources, load_sources

BLOQUE = {"type": "object", "additionalProperties": True}
DIA = {"type": "string"}

CONTRACT = (
    {
        "name": "kpi_validar",
        "description": "Checks a kernel: block against the language, fuentes.yaml, the clock rules and the planner's cost on dia; returns its compiled SQL, hash and columns, or the guard that refused it.",
        "input_schema": {"type": "object", "properties": {"bloque": BLOQUE, "dia": DIA}, "required": ["bloque", "dia"]},
    },
    {
        "name": "kpi_dry_run",
        "description": "Validates a kernel: block and runs it read-only on dia under the timeout; returns the first rows, the row count and the time, or the guard that refused it.",
        "input_schema": {"type": "object", "properties": {"bloque": BLOQUE, "dia": DIA}, "required": ["bloque", "dia"]},
    },
    {
        "name": "kpi_consultar",
        "description": "Runs a KPI of the client's catalogue by id on dia; returns its rows with the query that produced them.",
        "input_schema": {"type": "object", "properties": {"kpi": {"type": "string"}, "dia": DIA}, "required": ["kpi", "dia"]},
    },
    {
        "name": "kpi_catalogo",
        "description": "Lists the client's KPIs, base and approved, with their ISO 22400-2 fields, entity, columns and whether each is descriptive.",
        "input_schema": {"type": "object", "properties": {}},
    },
)


def answer(call: Callable[[], Any]) -> Any:
    try:
        return call()
    except Refused as error:
        return {"rechazado": {"guarda": error.guard, "detalle": error.detail}}


def day_of(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise Refused("lenguaje", f"dia: {text!r} is not a date YYYY-MM-DD") from error


@dataclass(frozen=True)
class Kernel:
    sources: Sources
    catalogue: tools.Catalogue
    settings: Settings
    connect: tools.Connect

    def run(self, name: str, arguments: Mapping[str, Any]) -> dict:
        if name == "kpi_validar":
            return tools.kpi_validar(arguments["bloque"], day_of(arguments["dia"]), self.sources, self.connect, self.settings)
        if name == "kpi_dry_run":
            return tools.kpi_dry_run(arguments["bloque"], day_of(arguments["dia"]), self.sources, self.connect, self.settings)
        if name == "kpi_consultar":
            return tools.kpi_consultar(arguments["kpi"], day_of(arguments["dia"]), self.catalogue, self.connect, self.settings)
        return {"kpis": tools.kpi_catalogo(self.catalogue)}

    def call(self, name: str, arguments: Mapping[str, Any]) -> dict:
        schemas = {tool["name"]: tool["input_schema"] for tool in CONTRACT}
        if name not in schemas:
            raise ValueError(f"{name} is no tool of the kernel")

        def checked() -> dict:
            refuse_first(Draft202012Validator(schemas[name]), arguments, name)
            return self.run(name, arguments)

        return answer(checked)


def connector(env: Mapping[str, str]) -> tools.Connect:
    dsns = {"lector": env["CENTINELA_LECTOR_DSN"], "kernel": env["CENTINELA_KERNEL_DSN"]}
    return lambda role: psycopg.connect(dsns[role], autocommit=True)


def kernel_from_env(env: Mapping[str, str] = os.environ) -> Kernel:
    sources = load_sources()
    path = env.get("CENTINELA_KPIS_APROBADOS")
    approved = json.loads(Path(path).read_text()) if path else []
    catalogue = tools.catalogue_of(tools.load_entries(METRICAS), sources, approved)
    return Kernel(sources, catalogue, Settings.from_env(env), connector(env))
