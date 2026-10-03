import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from psycopg import sql

from .language import check_block
from .refusal import Refused
from .sources import Join, Source, Sources, Table

COMPILER_VERSION = "1"
NAME = re.compile(r"^[a-z][a-z0-9_]{0,60}$")
NUMERIC = frozenset({"integer", "bigint", "numeric"})
RESERVED = frozenset({"dia", "periodo"})
LITERALS = {"text": (str,), "integer": (int,), "bigint": (int,), "numeric": (int, float), "boolean": (bool,), "date": (str,)}
TYPES = {
    "text": sql.SQL("text"),
    "integer": sql.SQL("integer"),
    "bigint": sql.SQL("bigint"),
    "numeric": sql.SQL("numeric"),
    "date": sql.SQL("date"),
    "boolean": sql.SQL("boolean"),
}
COMPARE = {
    "=": sql.SQL("{} = {}"),
    "!=": sql.SQL("{} <> {}"),
    "<": sql.SQL("{} < {}"),
    "<=": sql.SQL("{} <= {}"),
    ">": sql.SQL("{} > {}"),
    ">=": sql.SQL("{} >= {}"),
}
ARITH = {
    "+": sql.SQL("({}::numeric + {}::numeric)"),
    "-": sql.SQL("({}::numeric - {}::numeric)"),
    "*": sql.SQL("({}::numeric * {}::numeric)"),
    "/": sql.SQL("({}::numeric / NULLIF({}::numeric, 0))"),
}
AGGREGATE = {
    "sum": sql.SQL("sum({})::numeric"),
    "avg": sql.SQL("avg({})::numeric"),
    "mediana": sql.SQL("percentile_cont(0.5) WITHIN GROUP (ORDER BY {})::numeric"),
    "min": sql.SQL("min({})"),
    "max": sql.SQL("max({})"),
    "count": sql.SQL("count({})"),
}
TRUNC = {"semana": sql.SQL("date_trunc('week', {})::date"), "mes": sql.SQL("date_trunc('month', {})::date")}
LAST = {"semana": sql.SQL("date_trunc('week', {} - 6)::date"), "mes": sql.SQL("(date_trunc('month', {} + 1) - interval '1 month')::date")}
START = {"semana": sql.SQL("({} - 7 * {})"), "mes": sql.SQL("({} - interval '1 month' * {})::date")}
END = {"semana": sql.SQL("({} + 7)"), "mes": sql.SQL("({} + interval '1 month')::date")}
STEP = {"semana": sql.SQL("interval '1 week'"), "mes": sql.SQL("interval '1 month'")}
FILL = {True: sql.SQL("coalesce(periodos.valor, 0)"), False: sql.SQL("periodos.valor")}
ZERO_WHEN_EMPTY = frozenset({"sum", "count"})
DELTA = {
    "delta": sql.SQL("({valor} - {base})::numeric"),
    "delta_pct": sql.SQL("round(100 * ({valor} / NULLIF({base}, 0) - 1), 2)"),
}


@dataclass(frozen=True)
class Compiled:
    query: sql.Composable
    columns: tuple[tuple[str, str], ...]
    entity: tuple[str, ...]


@dataclass(frozen=True)
class Frozen:
    sql: str
    hash: str
    compiler_version: str


@dataclass(frozen=True)
class Scope:
    sources: Sources
    source: Source
    aliases: Mapping[str, str]
    day: sql.Composable

    def table_of(self, alias: str) -> Table:
        return self.sources.tables[self.aliases[alias]]

    def column(self, ref: str) -> tuple[str, str, str]:
        alias, _, name = ref.partition(".")
        if alias not in self.aliases:
            raise Refused("fuente", f"{ref}: {alias} is neither the source nor a join this KPI names")
        table = self.table_of(alias)
        if name in table.excluded:
            raise Refused("fuente", f"{ref} is not readable: {table.excluded[name]}")
        if name not in table.columns:
            raise Refused("fuente", f"{ref} is not a column fuentes.yaml lets the kernel read")
        return alias, name, table.columns[name]

    def role(self, ref: str) -> str | None:
        alias, name, _ = self.column(ref)
        return self.table_of(alias).dates.get(name)

    def raw(self, alias: str, name: str) -> sql.Composable:
        column = sql.Identifier(alias, name)
        if self.table_of(alias).dates.get(name) == "cierre":
            return sql.SQL("(CASE WHEN {c} <= {d} THEN {c} END)").format(c=column, d=self.day)
        return column

    def read(self, ref: str) -> tuple[sql.Composable, str]:
        alias, name, kind = self.column(ref)
        if name in self.table_of(alias).leaks:
            raise Refused("fuente", f"{ref} holds the end of the dataset; only a filter on a value known when the row is created reads it")
        return self.raw(alias, name), kind


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def freeze(compiled: Compiled) -> Frozen:
    text = compiled.query.as_string()
    return Frozen(text, digest(text), COMPILER_VERSION)


def scope_of(block: Mapping[str, Any], sources: Sources, day: sql.Composable) -> tuple[Scope, list[Join]]:
    source = sources.sources.get(block["fuente"])
    if source is None:
        raise Refused("fuente", f"fuente: {block['fuente']} is not a source fuentes.yaml declares")
    aliases = {source.name: source.name}
    joins = []
    for name in block.get("unir", []):
        join = source.joins.get(name)
        if join is None:
            raise Refused("fuente", f"unir: {name} is not a join fuentes.yaml declares for {source.name}")
        if join.origin not in aliases:
            raise Refused("fuente", f"unir: {name} joins from {join.origin}, which unir does not name before it")
        aliases[name] = join.table
        joins.append(join)
    if source.dated_by is not None and source.dated_by not in aliases:
        raise Refused("reloj", f"{source.name} has no date of its own; unir must name {source.dated_by}, which dates it")
    return Scope(sources, source, aliases, day), joins


def event_bounds(scope: Scope, alias: str) -> list[sql.Composable]:
    dates = scope.table_of(alias).dates
    return [sql.SQL("{} <= {}").format(sql.Identifier(alias, column), scope.day) for column, role in dates.items() if role == "evento"]


def from_clause(scope: Scope, joins: list[Join]) -> sql.Composable:
    parts = [sql.SQL("FROM {} AS {}").format(sql.Identifier("centinela", scope.source.name), sql.Identifier(scope.source.name))]
    for join in joins:
        on = [sql.SQL("{} = {}").format(sql.Identifier(join.origin, local), sql.Identifier(join.name, remote)) for local, remote in join.on.items()]
        on += event_bounds(scope, join.name)
        parts.append(sql.SQL("LEFT JOIN {} AS {} ON {}").format(sql.Identifier("centinela", join.table), sql.Identifier(join.name), sql.SQL(" AND ").join(on)))
    return sql.SQL(" ").join(parts)


def event_column(scope: Scope, ref: str, key: str) -> sql.Composable:
    alias, name, _ = scope.column(ref)
    if scope.table_of(alias).dates.get(name) != "evento":
        raise Refused("reloj", f"{key}: {ref} is not a date of an event, so dia cannot bound it")
    return sql.Identifier(alias, name)


def open_on_day(spec: Mapping[str, str], scope: Scope) -> list[sql.Composable]:
    start = event_column(scope, spec["desde"], "abierto_al_dia.desde")
    bounds = [sql.SQL("{} <= {}").format(start, scope.day)]
    end = spec["hasta"]
    if "." in end:
        alias, name, _ = scope.column(end)
        if scope.table_of(alias).dates.get(name) != "cierre":
            raise Refused("reloj", f"abierto_al_dia.hasta: {end} is not a date that closes a row")
        column = sql.Identifier(alias, name)
        return [*bounds, sql.SQL("({c} IS NULL OR {c} > {d})").format(c=column, d=scope.day)]
    closing = scope.source.closings.get(end)
    if closing is None:
        raise Refused("reloj", f"abierto_al_dia.hasta: {end} is neither a closing date nor a closing fuentes.yaml declares for {scope.source.name}")
    match = [sql.SQL("{} = {}").format(sql.Identifier(closing.name, child), sql.Identifier(scope.source.name, parent)) for child, parent in closing.on.items()]
    match.append(sql.SQL("{} <= {}").format(sql.Identifier(closing.name, closing.date), scope.day))
    exists = sql.SQL("NOT EXISTS (SELECT 1 FROM {} AS {} WHERE {})").format(
        sql.Identifier("centinela", closing.table), sql.Identifier(closing.name), sql.SQL(" AND ").join(match)
    )
    return [*bounds, exists]


def clock(block: Mapping[str, Any], scope: Scope) -> list[sql.Composable]:
    conditions = event_bounds(scope, scope.source.name)
    if scope.source.dated_by is not None:
        conditions += event_bounds(scope, scope.source.dated_by)
    if "ventana" in block:
        column = event_column(scope, block["ventana"]["columna"], "ventana")
        conditions.append(sql.SQL("{} > {} - {}").format(column, scope.day, sql.Literal(block["ventana"]["dias"])))
    if "abierto_al_dia" in block:
        conditions += open_on_day(block["abierto_al_dia"], scope)
    return conditions


def literal(value: Any, kind: str, ref: str) -> sql.Composable:
    if isinstance(value, bool) != (kind == "boolean") or not isinstance(value, LITERALS[kind]):
        raise Refused("lenguaje", f"filtro: {value!r} is not a {kind}, the type of {ref}")
    if kind == "date":
        try:
            date.fromisoformat(value)
        except ValueError as error:
            raise Refused("lenguaje", f"filtro: {value!r} is not a date YYYY-MM-DD") from error
    return sql.Literal(value)


def condition(spec: Mapping[str, Any], scope: Scope) -> sql.Composable:
    ref, operator, value = spec["columna"], spec["op"], spec["valor"]
    alias, name, kind = scope.column(ref)
    known = scope.table_of(alias).leaks.get(name)
    values = value if operator == "en" else [value]
    if known is not None and (operator not in ("=", "!=", "en") or not set(values) <= set(known)):
        raise Refused("fuente", f"filtro: {ref} holds the end of the dataset; only =, != or en on {list(known)} reads it")
    column = scope.raw(alias, name)
    if operator == "en":
        return sql.SQL("{} IN ({})").format(column, sql.SQL(", ").join(literal(item, kind, ref) for item in values))
    return COMPARE[operator].format(column, literal(value, kind, ref))


def expression(node: Any, scope: Scope) -> tuple[sql.Composable, str]:
    if isinstance(node, str):
        return scope.read(node)
    left, left_kind = expression(node["izq"], scope)
    right, right_kind = expression(node["der"], scope)
    if node["op"] == "-" and left_kind == right_kind == "date":
        return sql.SQL("({} - {})").format(left, right), "integer"
    if left_kind in NUMERIC and right_kind in NUMERIC:
        return ARITH[node["op"]].format(left, right), "numeric"
    raise Refused("lenguaje", f"{node['op']} does not apply to {left_kind} and {right_kind}")


def measure(spec: Mapping[str, Any], scope: Scope) -> tuple[sql.Composable, str]:
    aggregate = spec["agregado"]
    if "de" not in spec:
        return sql.SQL("count(*)"), "bigint"
    expr, kind = expression(spec["de"], scope)
    if aggregate == "count":
        return AGGREGATE["count"].format(expr), "bigint"
    if aggregate in ("min", "max"):
        return AGGREGATE[aggregate].format(expr), kind
    if kind not in NUMERIC:
        raise Refused("lenguaje", f"{aggregate} needs a number, and {spec['de']} is {kind}")
    return AGGREGATE[aggregate].format(expr), "numeric"


def value(block: Mapping[str, Any], scope: Scope) -> tuple[sql.Composable, str]:
    if "medida" in block:
        return measure(block["medida"], scope)
    numerator, numerator_kind = measure(block["razon"]["numerador"], scope)
    denominator, denominator_kind = measure(block["razon"]["denominador"], scope)
    if numerator_kind not in NUMERIC or denominator_kind not in NUMERIC:
        raise Refused("lenguaje", "razon: both measures must be numbers")
    return sql.SQL("({}::numeric / NULLIF({}::numeric, 0))").format(numerator, denominator), "numeric"


def dimension(item: Any, scope: Scope) -> tuple[str, sql.Composable, str]:
    if isinstance(item, str):
        scope.column(item)
        if item not in scope.source.dimensions:
            raise Refused("fuente", f"agrupar: {item} is not a dimension fuentes.yaml declares for {scope.source.name}")
        expr, kind = scope.read(item)
        return item.partition(".")[2], expr, kind
    ref, period = item["columna"], item["por"]
    if scope.role(ref) not in ("evento", "plazo"):
        raise Refused("reloj", f"agrupar: {ref} is not a date of an event or a term, so it has no {period}")
    expr, _ = scope.read(ref)
    return period, TRUNC[period].format(expr), "date"


def compile_kpi(block: Mapping[str, Any], sources: Sources, day: sql.Composable = sql.Placeholder("dia")) -> Compiled:
    check_block(block)
    scope, joins = scope_of(block, sources, sql.SQL("CAST({} AS date)").format(day))
    dims = [dimension(item, scope) for item in block["agrupar"]]
    names = [name for name, _, _ in dims] + list(block["salida"].values())
    if len(set(names)) != len(names) or RESERVED & set(names):
        raise Refused("lenguaje", f"agrupar and salida name {names}: each output column needs a unique name other than dia or periodo")
    measured, kind = value(block, scope)
    conditions = clock(block, scope) + [condition(spec, scope) for spec in block.get("filtro", [])]
    source = from_clause(scope, joins)
    if "linea_base" in block:
        return baseline(block, scope, dims, measured, kind, conditions, source)
    selected = [sql.SQL("{}::{} AS {}").format(expr, TYPES[k], sql.Identifier(name)) for name, expr, k in dims]
    selected.append(sql.SQL("{}::{} AS {}").format(measured, TYPES[kind], sql.Identifier(block["salida"]["valor"])))
    query = sql.SQL("SELECT {} {} WHERE {} GROUP BY {}").format(
        sql.SQL(", ").join(selected),
        source,
        sql.SQL(" AND ").join(conditions or [sql.SQL("TRUE")]),
        sql.SQL(", ").join(expr for _, expr, _ in dims),
    )
    columns = tuple((name, k) for name, _, k in dims) + ((block["salida"]["valor"], kind),)
    return Compiled(query, columns, tuple(name for name, _, _ in dims))


def baseline(block, scope, dims, measured, kind, conditions, source) -> Compiled:
    spec = block["linea_base"]
    if kind not in NUMERIC:
        raise Refused("lenguaje", "linea_base: the measure must be a number")
    if any(not isinstance(item, str) for item in block["agrupar"]):
        raise Refused("lenguaje", "linea_base groups by its own period; agrupar may not hold another")
    period = spec["periodo"]
    column = event_column(scope, spec["columna"], "linea_base")
    current = LAST[period].format(scope.day)
    bounds = [
        sql.SQL("{} >= {}").format(column, START[period].format(current, sql.Literal(spec["n"]))),
        sql.SQL("{} < {}").format(column, END[period].format(current)),
    ]
    truncated = TRUNC[period].format(column)
    inner = sql.SQL("SELECT {dims}, {period} AS periodo, {value} AS valor {source} WHERE {where} GROUP BY {group}").format(
        dims=sql.SQL(", ").join(sql.SQL("{} AS {}").format(expr, sql.Identifier(name)) for name, expr, _ in dims),
        period=truncated,
        value=measured,
        source=source,
        where=sql.SQL(" AND ").join(conditions + bounds),
        group=sql.SQL(", ").join([expr for _, expr, _ in dims] + [truncated]),
    )
    names = [name for name, _, _ in dims]
    same = sql.SQL(" AND ").join(
        sql.SQL("{} IS NOT DISTINCT FROM {}").format(sql.Identifier("periodos", name), sql.Identifier("entidades", name)) for name in names
    )
    filled = "medida" in block and block["medida"]["agregado"] in ZERO_WHEN_EMPTY
    out = block["salida"]
    value_now = sql.SQL("max(marco.valor) FILTER (WHERE marco.periodo = {})::numeric").format(current)
    base_before = sql.SQL("avg(marco.valor) FILTER (WHERE marco.periodo < {})::numeric").format(current)
    query = sql.SQL(
        "WITH periodos AS ({inner}), entidades AS (SELECT DISTINCT {entity} FROM periodos), "
        "marco AS (SELECT {framed}, serie.periodo, {fill} AS valor "
        "FROM entidades CROSS JOIN (SELECT generate_series({first}, {current}, {step})::date AS periodo) AS serie "
        "LEFT JOIN periodos ON {same} AND periodos.periodo = serie.periodo) "
        "SELECT {dims}, {value_now} AS {valor}, {base_before} AS {base}, {delta} AS {delta_name} "
        "FROM marco GROUP BY {group}"
    ).format(
        inner=inner,
        entity=sql.SQL(", ").join(sql.Identifier(name) for name in names),
        framed=sql.SQL(", ").join(sql.Identifier("entidades", name) for name in names),
        fill=FILL[filled],
        same=same,
        first=START[period].format(current, sql.Literal(spec["n"])),
        current=current,
        step=STEP[period],
        dims=sql.SQL(", ").join(sql.SQL("{}::{} AS {}").format(sql.Identifier("marco", name), TYPES[k], sql.Identifier(name)) for name, _, k in dims),
        value_now=value_now,
        valor=sql.Identifier(out["valor"]),
        base_before=base_before,
        base=sql.Identifier(out["base"]),
        delta=DELTA[spec["salida"]].format(valor=value_now, base=base_before),
        delta_name=sql.Identifier(out["delta"]),
        group=sql.SQL(", ").join(sql.Identifier("marco", name) for name in names),
    )
    columns = tuple((name, k) for name, _, k in dims) + ((out["valor"], "numeric"), (out["base"], "numeric"), (out["delta"], "numeric"))
    return Compiled(query, columns, tuple(name for name, _, _ in dims))


def function_definition(metric: str, block: Mapping[str, Any], sources: Sources) -> sql.Composable:
    if NAME.match(metric) is None:
        raise Refused("lenguaje", f"{metric} is not a metric name of lowercase letters, digits and underscores")
    compiled = compile_kpi(block, sources, day=sql.SQL("dia"))
    function = sql.Identifier("centinela", f"k_{metric}")
    returns = sql.SQL(", ").join(sql.SQL("{} {}").format(sql.Identifier(name), TYPES[kind]) for name, kind in compiled.columns)
    return sql.SQL(
        "CREATE OR REPLACE FUNCTION {fn}(dia date) RETURNS TABLE ({returns}) LANGUAGE sql STABLE SECURITY DEFINER "
        "SET search_path = pg_catalog, pg_temp AS {body};\n"
        "ALTER FUNCTION {fn}(date) OWNER TO centinela_propietario;\n"
        "REVOKE ALL ON FUNCTION {fn}(date) FROM PUBLIC;\n"
        "GRANT EXECUTE ON FUNCTION {fn}(date) TO centinela_lector;\n"
    ).format(fn=function, returns=returns, body=sql.Literal(compiled.query.as_string()))
