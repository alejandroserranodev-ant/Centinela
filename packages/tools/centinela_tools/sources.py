from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .paths import FUENTES

ROLES = frozenset({"evento", "plazo", "cierre"})
TYPES = frozenset({"text", "integer", "bigint", "numeric", "date", "boolean"})


@dataclass(frozen=True)
class Table:
    name: str
    key: tuple[str, ...]
    columns: Mapping[str, str]
    dates: Mapping[str, str]
    leaks: Mapping[str, tuple[Any, ...]]
    excluded: Mapping[str, str]


@dataclass(frozen=True)
class Join:
    name: str
    origin: str
    table: str
    on: Mapping[str, str]


@dataclass(frozen=True)
class Closing:
    name: str
    table: str
    on: Mapping[str, str]
    date: str


@dataclass(frozen=True)
class Source:
    name: str
    joins: Mapping[str, Join]
    closings: Mapping[str, Closing]
    dimensions: frozenset[str]
    dated_by: str | None


@dataclass(frozen=True)
class Sources:
    tables: Mapping[str, Table]
    sources: Mapping[str, Source]


def load_sources(path: Path = FUENTES) -> Sources:
    data = yaml.safe_load(path.read_text())
    tables = {name: table_of(name, spec) for name, spec in data["tablas"].items()}
    return Sources(tables, {name: source_of(name, spec, tables) for name, spec in data["fuentes"].items()})


def problem(message: str) -> ValueError:
    return ValueError(f"fuentes.yaml: {message}")


def table_of(name: str, spec: Mapping[str, Any]) -> Table:
    columns = dict(spec["columnas"])
    dates = dict(spec.get("fechas", {}))
    leaks = spec.get("fuga", {})
    excluded = dict(spec.get("excluidas", {}))
    if "dia" in columns:
        raise problem(f"{name}: a column named dia would shadow the argument of every kernel function")
    if set(columns.values()) - TYPES:
        raise problem(f"{name} declares a type outside {sorted(TYPES)}")
    if {column for column, kind in columns.items() if kind == "date"} != set(dates):
        raise problem(f"{name}: every date column, and only a date column, carries a role")
    if set(dates.values()) - ROLES:
        raise problem(f"{name}: a date role is one of {sorted(ROLES)}")
    if set(leaks) - set(columns) or any(not leak.get("razon") for leak in leaks.values()):
        raise problem(f"{name}: a fuga column is readable and carries its razon")
    if set(excluded) & set(columns) or set(spec["clave"]) - set(columns):
        raise problem(f"{name}: an excluded column is not readable, and the key is readable")
    known = {column: tuple(leak.get("conocidos_al_crear", [])) for column, leak in leaks.items()}
    return Table(name, tuple(spec["clave"]), columns, dates, known, excluded)


def source_of(name: str, spec: Mapping[str, Any], tables: Mapping[str, Table]) -> Source:
    if name not in tables:
        raise problem(f"the source {name} is no table")
    owners = {name: tables[name]}
    joins = {}
    for join_name, join in spec.get("uniones", {}).items():
        remote = tables.get(join["tabla"])
        origin = owners.get(join["desde"])
        if join_name in owners or origin is None:
            raise problem(f"{name}: {join_name} reuses a name or joins from {join['desde']}, declared after it or nowhere")
        if remote is None or set(join["por"].values()) != set(remote.key) or set(join["por"]) - set(origin.columns):
            raise problem(f"{name}: {join_name} joins columns of {join['desde']} to the whole key of {join['tabla']}")
        owners[join_name] = remote
        joins[join_name] = Join(join_name, join["desde"], join["tabla"], dict(join["por"]))
    closings = {}
    for closing_name, closing in spec.get("cierres", {}).items():
        child = tables.get(closing["tabla"])
        if closing_name in owners or child is None or child.dates.get(closing["fecha"]) != "evento":
            raise problem(f"{name}: the closing {closing_name} reads an event date of a declared table")
        if set(closing["por"]) - set(child.columns) or set(closing["por"].values()) - set(tables[name].columns):
            raise problem(f"{name}: the closing {closing_name} matches columns both tables hold")
        closings[closing_name] = Closing(closing_name, closing["tabla"], dict(closing["por"]), closing["fecha"])
    dated_by = spec.get("fechada_por")
    if dated_by is not None and dated_by not in joins:
        raise problem(f"{name}: fechada_por names {dated_by}, which is no join of it")
    if "evento" not in owners[dated_by or name].dates.values():
        raise problem(f"{name} has no event date, and no fechada_por names a join that has one")
    dimensions = frozenset(spec.get("dimensiones", []))
    for ref in dimensions:
        alias, _, column = ref.partition(".")
        table = owners.get(alias)
        if table is None or column not in table.columns or column in table.leaks:
            raise problem(f"{name}: the dimension {ref} is no readable column of the source or its joins")
    return Source(name, joins, closings, dimensions, dated_by)
