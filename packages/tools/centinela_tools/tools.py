import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

import psycopg
import yaml
from psycopg import ClientCursor, sql
from psycopg.rows import dict_row

from .compiler import NAME, compile_kpi, digest, freeze
from .language import check_card
from .refusal import Refused
from .settings import Settings
from .sources import Sources


def load_entries(path: Path) -> dict[str, dict]:
    return dict(yaml.safe_load(path.read_text())["metricas"])


def planner_cost(conn: psycopg.Connection, query: sql.Composable, day: date) -> float:
    with ClientCursor(conn) as cursor:
        cursor.execute(sql.SQL("EXPLAIN (FORMAT JSON) {}").format(query), {"dia": day})
        return float(cursor.fetchone()[0][0]["Plan"]["Total Cost"])


Connect = Callable[[str], psycopg.Connection]
CARD = ("descripcion", "unidad", "rango", "tendencia", "temporalidad", "audiencia")


@dataclass(frozen=True)
class Kpi:
    id: str
    origin: str
    card: Mapping[str, Any]
    descriptive: bool
    entity: tuple[str, ...]
    columns: tuple[tuple[str, str], ...]
    sql: str | None = None
    hash: str | None = None
    compiler_version: str | None = None


@dataclass(frozen=True)
class Catalogue:
    kpis: Mapping[str, Kpi]


def named(kpi_id: str) -> str:
    if NAME.match(kpi_id) is None:
        raise Refused("lenguaje", f"{kpi_id} is not a KPI id of lowercase letters, digits and underscores")
    return kpi_id


def catalogue_of(entries: Mapping[str, Mapping[str, Any]], sources: Sources, approved: Iterable[Mapping[str, Any]] = ()) -> Catalogue:
    kpis = {}
    for kpi_id, entry in entries.items():
        if "kernel" not in entry:
            continue
        check_card(entry)
        compiled = compile_kpi(entry["kernel"], sources)
        kpis[named(kpi_id)] = Kpi(kpi_id, "base", {key: entry[key] for key in CARD}, not entry.get("fuente_umbral"), compiled.entity, compiled.columns)
    for record in approved:
        if record["id"] in kpis:
            raise ValueError(f"{record['id']} is both a base and an approved KPI")
        kpis[named(record["id"])] = Kpi(
            record["id"], "aprobado", dict(record["ficha"]), bool(record["descriptivo"]), tuple(record["entidad"]),
            tuple((column["nombre"], column["tipo"]) for column in record["columnas"]),
            record["sql"], record["hash"], record["version_compilador"],
        )
    return Catalogue(kpis)


def plain(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: float(value) if isinstance(value, Decimal) else value.isoformat() if isinstance(value, date) else value for key, value in row.items()}


@contextmanager
def guarded(conn: psycopg.Connection, settings: Settings) -> Iterator[psycopg.Connection]:
    try:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute(sql.SQL("SET LOCAL statement_timeout = {}").format(sql.Literal(settings.timeout_ms)))
            yield conn
    except psycopg.errors.QueryCanceled as error:
        raise Refused("tiempo", f"the run passed the statement_timeout of {settings.timeout_ms} ms") from error


def kpi_validar(block: Mapping[str, Any], day: date, sources: Sources, connect: Connect, settings: Settings) -> dict[str, Any]:
    compiled = compile_kpi(block, sources)
    with connect("kernel") as conn, guarded(conn, settings):
        cost = planner_cost(conn, compiled.query, day)
    if cost > settings.max_cost:
        raise Refused("costo", f"the planner estimates {cost:.0f}, over the cap of {settings.max_cost:.0f}")
    frozen = freeze(compiled)
    return {
        "sql": frozen.sql,
        "hash": frozen.hash,
        "version_compilador": frozen.compiler_version,
        "entidad": list(compiled.entity),
        "columnas": [{"nombre": name, "tipo": kind} for name, kind in compiled.columns],
        "costo": cost,
    }


def kpi_dry_run(block: Mapping[str, Any], day: date, sources: Sources, connect: Connect, settings: Settings) -> dict[str, Any]:
    validated = kpi_validar(block, day, sources, connect, settings)
    compiled = compile_kpi(block, sources)
    started = time.perf_counter()
    with connect("kernel") as conn, guarded(conn, settings), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(compiled.query, {"dia": day})
        found = cursor.fetchmany(settings.max_groups + 1)
    elapsed = round((time.perf_counter() - started) * 1000)
    if len(found) > settings.max_groups:
        raise Refused("cardinalidad", f"the KPI returns more than {settings.max_groups} groups")
    return {**validated, "dia": day.isoformat(), "filas": [plain(row) for row in found[: settings.sample_rows]], "total_filas": len(found), "ms": elapsed}


def kpi_consultar(kpi_id: str, day: date, catalogue: Catalogue, connect: Connect, settings: Settings) -> dict[str, Any]:
    kpi = catalogue.kpis.get(kpi_id)
    if kpi is None:
        raise Refused("catalogo", f"{kpi_id} is no KPI of this client's catalogue")
    if kpi.origin == "base":
        query = sql.SQL("SELECT * FROM {}({})").format(sql.Identifier("centinela", f"k_{kpi.id}"), sql.Placeholder("dia"))
        role, text = "lector", query.as_string()
    else:
        if digest(kpi.sql) != kpi.hash:
            raise Refused("hash", f"the stored SQL of {kpi_id} does not match the hash recorded at its approval")
        query, role, text = kpi.sql, "kernel", kpi.sql
    with connect(role) as conn, guarded(conn, settings), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, {"dia": day})
        found = cursor.fetchall()
    return {"kpi": kpi_id, "dia": day.isoformat(), "consulta": text, "filas": [plain(row) for row in found]}


def kpi_catalogo(catalogue: Catalogue) -> list[dict[str, Any]]:
    return [
        {
            "id": kpi.id,
            "origen": kpi.origin,
            "ficha": dict(kpi.card),
            "descriptivo": kpi.descriptive,
            "entidad": list(kpi.entity),
            "columnas": [{"nombre": name, "tipo": kind} for name, kind in kpi.columns],
        }
        for kpi in catalogue.kpis.values()
    ]
