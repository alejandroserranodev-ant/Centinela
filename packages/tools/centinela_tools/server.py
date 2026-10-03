import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping

import psycopg
from mcp.server.mcpserver import MCPServer

from . import tools
from .paths import METRICAS
from .refusal import Refused
from .settings import Settings
from .sources import Sources, load_sources


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


def build_server(sources: Sources, catalogue: tools.Catalogue, settings: Settings, connect: tools.Connect) -> MCPServer:
    server = MCPServer("centinela-kernel")

    @server.tool(description="Checks a kernel: block against the language, fuentes.yaml, the clock rules and the planner's cost on dia; returns its compiled SQL, hash and columns, or the guard that refused it.")
    def kpi_validar(bloque: dict, dia: str) -> dict:
        return answer(lambda: tools.kpi_validar(bloque, day_of(dia), sources, connect, settings))

    @server.tool(description="Validates a kernel: block and runs it read-only on dia under the timeout; returns the first rows, the row count and the time, or the guard that refused it.")
    def kpi_dry_run(bloque: dict, dia: str) -> dict:
        return answer(lambda: tools.kpi_dry_run(bloque, day_of(dia), sources, connect, settings))

    @server.tool(description="Runs a KPI of the client's catalogue by id on dia; returns its rows with the query that produced them.")
    def kpi_consultar(kpi: str, dia: str) -> dict:
        return answer(lambda: tools.kpi_consultar(kpi, day_of(dia), catalogue, connect, settings))

    @server.tool(description="Lists the client's KPIs, base and approved, with their ISO 22400-2 fields, entity, columns and whether each is descriptive.")
    def kpi_catalogo() -> dict:
        return {"kpis": tools.kpi_catalogo(catalogue)}

    return server


def connector(env: Mapping[str, str]) -> tools.Connect:
    dsns = {"lector": env["CENTINELA_LECTOR_DSN"], "kernel": env["CENTINELA_KERNEL_DSN"]}
    return lambda role: psycopg.connect(dsns[role], autocommit=True)


def main(env: Mapping[str, str] = os.environ) -> None:
    sources = load_sources()
    path = env.get("CENTINELA_KPIS_APROBADOS")
    approved = json.loads(Path(path).read_text()) if path else []
    catalogue = tools.catalogue_of(tools.load_entries(METRICAS), sources, approved)
    build_server(sources, catalogue, Settings.from_env(env), connector(env)).run()


if __name__ == "__main__":
    main()
