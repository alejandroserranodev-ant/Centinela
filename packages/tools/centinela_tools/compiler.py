import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from psycopg import sql

from .language import check_block
from .refusal import Refused
from .sources import Join, Source, Sources, Table

COMPILER_VERSION = "2"
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
    "sum": sql.SQL("sum({})"),
    "avg": sql.SQL("avg({})"),
    "mediana": sql.SQL("percentile_cont(0.5) WITHIN GROUP (ORDER BY {})"),
    "min": sql.SQL("min({})"),
    "max": sql.SQL("max({})"),
    "count": sql.SQL("count({})"),
    "ultimo": sql.SQL("array_agg({} ORDER BY {} DESC)"),
    "anterior": sql.SQL("array_agg({} ORDER BY {} DESC)"),
}
FILTERED = sql.SQL("{} FILTER (WHERE {})")
PICK = {"ultimo": sql.SQL("({})[1]"), "anterior": sql.SQL("({})[2]")}
ZERO = sql.SQL("coalesce({}, 0)")
AS_NUMERIC = sql.SQL("{}::numeric")
ORDERED = frozenset({"ultimo", "anterior"})
DAYS_BACK = sql.SQL("({} - {})")
MONTHS_BACK = sql.SQL("({} - interval '1 month' * {})::date")
BUSINESS_DAYS = sql.SQL("(SELECT count(*) FROM generate_series({} + 1, {}, interval '1 day') AS habil(d) WHERE extract(isodow FROM habil.d) < 6)::integer")
GREATEST = {"mayor": sql.SQL("greatest({}, {})"), "menor": sql.SQL("least({}, {})")}
EXISTS = sql.SQL("({} IS NOT NULL)")
SHARE = sql.SQL("(100 * {x}::numeric / NULLIF(sum({x}) OVER (), 0))")
PREVIOUS = sql.SQL("max({x}) OVER ({partition}ORDER BY {period} RANGE BETWEEN {step} PRECEDING AND {step} PRECEDING)")
PARTITION = sql.SQL("PARTITION BY {} ")
WHEN = sql.SQL("(CASE WHEN {} THEN {} ELSE {} END)")
ROUND = sql.SQL("round({}::numeric, {})")
BY_VALUE = sql.SQL("(CASE {} {} END)")
WHEN_VALUE = sql.SQL("WHEN {} THEN {}")
MAX_TAKEN_DEPTH = 2
MAX_DERIVED_DEPTH = 4
TRUNC = {"semana": sql.SQL("date_trunc('week', {})::date"), "mes": sql.SQL("date_trunc('month', {})::date")}
LAST = {"semana": sql.SQL("date_trunc('week', {} - 6)::date"), "mes": sql.SQL("(date_trunc('month', {} + 1) - interval '1 month')::date")}
START = {"semana": sql.SQL("({} - 7 * {})"), "mes": sql.SQL("({} - interval '1 month' * {})::date")}
END = {"semana": sql.SQL("({} + 7)"), "mes": sql.SQL("({} + interval '1 month')::date")}
STEP = {"semana": sql.SQL("interval '1 week'"), "mes": sql.SQL("interval '1 month'")}
ZERO_WHEN_EMPTY = frozenset({"sum", "count"})
DELTA = {
    "delta": sql.SQL("({valor} - {base})::numeric"),
    "caida": sql.SQL("({base} - {valor})::numeric"),
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
class Taken:
    name: str
    compiled: Compiled
    on: Mapping[str, str]


@dataclass(frozen=True)
class Scope:
    sources: Sources
    source: Source
    tables: Mapping[str, Table]
    day: sql.Composable

    def table_of(self, alias: str) -> Table:
        return self.tables[alias]

    def column(self, ref: str) -> tuple[str, str, str]:
        alias, _, name = ref.partition(".")
        if alias not in self.tables:
            raise Refused("fuente", f"{ref}: {alias} is neither the source nor a join or a taken KPI this KPI names")
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


def taken_table(taken: Taken) -> Table:
    return Table(taken.name, taken.compiled.entity, dict(taken.compiled.columns), {}, {}, {})


def scope_of(block: Mapping[str, Any], sources: Sources, day: sql.Composable, taken: list[Taken]) -> tuple[Scope, list[Join]]:
    source = sources.sources.get(block["fuente"])
    if source is None:
        raise Refused("fuente", f"fuente: {block['fuente']} is not a source fuentes.yaml declares")
    tables = {source.name: sources.tables[source.name]}
    joins = []
    for name in block.get("unir", []):
        join = source.joins.get(name)
        if join is None:
            raise Refused("fuente", f"unir: {name} is not a join fuentes.yaml declares for {source.name}")
        if join.origin not in tables:
            raise Refused("fuente", f"unir: {name} joins from {join.origin}, which unir does not name before it")
        tables[name] = sources.tables[join.table]
        joins.append(join)
    if source.dated_by is not None and source.dated_by not in tables:
        raise Refused("reloj", f"{source.name} has no date of its own; unir must name {source.dated_by}, which dates it")
    for item in taken:
        if item.name in tables:
            raise Refused("fuente", f"tomar: {item.name} is already the name of the source or of a join")
        tables[item.name] = taken_table(item)
    return Scope(sources, source, tables, day), joins


def event_bounds(scope: Scope, alias: str) -> list[sql.Composable]:
    dates = scope.table_of(alias).dates
    return [sql.SQL("{} <= {}").format(sql.Identifier(alias, column), scope.day) for column, role in dates.items() if role == "evento"]


def taken_join(item: Taken, scope: Scope) -> sql.Composable:
    if set(item.on) != set(item.compiled.entity):
        raise Refused("fuente", f"tomar: {item.name} joins by {sorted(item.on)}, and must join by the whole entity {list(item.compiled.entity)} of the KPI it takes")
    kinds = dict(item.compiled.columns)
    on = []
    for remote, local in item.on.items():
        column, kind = scope.read(local)
        if kind != kinds[remote]:
            raise Refused("lenguaje", f"tomar: {item.name} joins {local}, a {kind}, to {remote}, a {kinds[remote]}")
        on.append(sql.SQL("{} = {}").format(sql.Identifier(item.name, remote), column))
    return sql.SQL("LEFT JOIN ({}) AS {} ON {}").format(item.compiled.query, sql.Identifier(item.name), sql.SQL(" AND ").join(on))


def from_clause(scope: Scope, joins: list[Join], taken: list[Taken]) -> sql.Composable:
    parts = [sql.SQL("FROM {} AS {}").format(sql.Identifier("centinela", scope.source.name), sql.Identifier(scope.source.name))]
    for join in joins:
        on = [sql.SQL("{} = {}").format(sql.Identifier(join.origin, local), sql.Identifier(join.name, remote)) for local, remote in join.on.items()]
        on += event_bounds(scope, join.name)
        parts.append(sql.SQL("LEFT JOIN {} AS {} ON {}").format(sql.Identifier("centinela", join.table), sql.Identifier(join.name), sql.SQL(" AND ").join(on)))
    parts += [taken_join(item, scope) for item in taken]
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
    if kind == "date" and not is_date(value):
        raise Refused("lenguaje", f"filtro: {value!r} is not a date YYYY-MM-DD")
    return sql.Literal(value)


def is_date(value: str) -> bool:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def comparable(left: str, right: str) -> bool:
    return left == right or (left in NUMERIC and right in NUMERIC)


def against(spec: Mapping[str, Any], scope: Scope) -> sql.Composable:
    left, left_kind = scope.read(spec["columna"])
    right, right_kind = (scope.day, "date") if spec["contra"] == "dia" else scope.read(spec["contra"])
    if "menos_dias" in spec or "menos_meses" in spec:
        if right_kind != "date":
            raise Refused("lenguaje", f"filtro: {spec['contra']} is no date, so it has no days or months to subtract")
        back = DAYS_BACK if "menos_dias" in spec else MONTHS_BACK
        right = back.format(right, sql.Literal(spec.get("menos_dias", spec.get("menos_meses"))))
    if not comparable(left_kind, right_kind):
        raise Refused("lenguaje", f"filtro: {spec['columna']}, a {left_kind}, cannot be compared with {spec['contra']}, a {right_kind}")
    return COMPARE[spec["op"]].format(left, right)


def condition(spec: Mapping[str, Any], scope: Scope) -> sql.Composable:
    if "contra" in spec:
        return against(spec, scope)
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


def operand(node: Any, scope: Scope) -> tuple[sql.Composable, str]:
    if node == "dia":
        return scope.day, "date"
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return sql.Literal(node), "integer" if isinstance(node, int) else "numeric"
    return scope.read(node)


def arithmetic(operator: str, left: sql.Composable, left_kind: str, right: sql.Composable, right_kind: str) -> tuple[sql.Composable, str]:
    if operator == "-" and left_kind == right_kind == "date":
        return sql.SQL("({} - {})").format(left, right), "integer"
    if left_kind in NUMERIC and right_kind in NUMERIC:
        return ARITH[operator].format(left, right), "numeric"
    raise Refused("lenguaje", f"{operator} does not apply to {left_kind} and {right_kind}")


def expression(node: Any, scope: Scope) -> tuple[sql.Composable, str]:
    if not isinstance(node, Mapping):
        return operand(node, scope)
    left, left_kind = expression(node["izq"], scope)
    right, right_kind = expression(node["der"], scope)
    return arithmetic(node["op"], left, left_kind, right, right_kind)


def measure(spec: Mapping[str, Any], scope: Scope) -> tuple[sql.Composable, str]:
    aggregate = spec["agregado"]
    if "de" in spec:
        expr, kind = expression(spec["de"], scope)
    else:
        expr, kind = sql.SQL("*"), "bigint"
    if aggregate in ("sum", "avg", "mediana") and kind not in NUMERIC:
        raise Refused("lenguaje", f"{aggregate} needs a number, and {spec['de']} is {kind}")
    if aggregate in ORDERED:
        call = AGGREGATE[aggregate].format(expr, event_column(scope, spec["por"], aggregate))
    else:
        call = AGGREGATE[aggregate].format(expr)
    if "si" in spec:
        call = FILTERED.format(call, sql.SQL(" AND ").join(condition(item, scope) for item in spec["si"]))
    if aggregate in ORDERED:
        return PICK[aggregate].format(call), kind
    if aggregate == "count":
        return call, "bigint"
    if aggregate == "sum" and "si" in spec:
        call = ZERO.format(call)
    if aggregate in ("min", "max"):
        return call, kind
    return AS_NUMERIC.format(call), "numeric"


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


def output_names(block: Mapping[str, Any], dims: list) -> list[str]:
    names = [name for name, _, _ in dims] + list(block["salida"].values()) + list(block.get("columnas", {})) + list(block.get("derivadas", {}))
    if len(set(names)) != len(names) or RESERVED & set(names):
        raise Refused("lenguaje", f"agrupar, salida, columnas and derivadas name {names}: each output column needs a unique name other than dia or periodo")
    return names


def compile_kpi(block: Mapping[str, Any], sources: Sources, day: sql.Composable = sql.Placeholder("dia"), thresholds: Mapping[str, Any] | None = None) -> Compiled:
    check_block(block)
    return build(block, sources, sql.SQL("CAST({} AS date)").format(day), thresholds or {}, 0)


def build(block: Mapping[str, Any], sources: Sources, day: sql.Composable, thresholds: Mapping[str, Any], depth: int) -> Compiled:
    if depth > MAX_TAKEN_DEPTH:
        raise Refused("lenguaje", f"tomar nests at most {MAX_TAKEN_DEPTH} levels of KPIs")
    taken = [Taken(name, build(spec["kpi"], sources, day, {}, depth + 1), spec["por"]) for name, spec in block.get("tomar", {}).items()]
    scope, joins = scope_of(block, sources, day, taken)
    dims = [dimension(item, scope) for item in block["agrupar"]]
    output_names(block, dims)
    measured, kind = value(block, scope)
    extras = [(name, *measure(spec, scope), spec["agregado"]) for name, spec in block.get("columnas", {}).items()]
    conditions = clock(block, scope) + [condition(spec, scope) for spec in block.get("filtro", [])]
    source = from_clause(scope, joins, taken)
    if "linea_base" in block:
        core = baseline(block, scope, dims, measured, kind, extras, conditions, source)
    else:
        selected = [sql.SQL("{}::{} AS {}").format(expr, TYPES[k], sql.Identifier(name)) for name, expr, k in dims]
        selected.append(sql.SQL("{}::{} AS {}").format(measured, TYPES[kind], sql.Identifier(block["salida"]["valor"])))
        selected += [sql.SQL("{}::{} AS {}").format(expr, TYPES[k], sql.Identifier(name)) for name, expr, k, _ in extras]
        query = sql.SQL("SELECT {} {} WHERE {} GROUP BY {}").format(
            sql.SQL(", ").join(selected),
            source,
            sql.SQL(" AND ").join(conditions or [sql.SQL("TRUE")]),
            sql.SQL(", ").join(expr for _, expr, _ in dims),
        )
        columns = tuple((name, k) for name, _, k in dims) + ((block["salida"]["valor"], kind),) + tuple((name, k) for name, _, k, _ in extras)
        core = Compiled(query, columns, tuple(name for name, _, _ in dims))
    return finish(block, core, scope.day, thresholds)


def baseline(block, scope, dims, measured, kind, extras, conditions, source) -> Compiled:
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
    inner = sql.SQL("SELECT {dims}, {period} AS periodo, {value} AS valor{extras} {source} WHERE {where} GROUP BY {group}").format(
        dims=sql.SQL(", ").join(sql.SQL("{} AS {}").format(expr, sql.Identifier(name)) for name, expr, _ in dims),
        period=truncated,
        value=measured,
        extras=sql.SQL("").join(sql.SQL(", {} AS {}").format(expr, sql.Identifier(name)) for name, expr, _, _ in extras),
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
        "marco AS (SELECT {framed}, serie.periodo, {fill} AS valor{extra_fill} "
        "FROM entidades CROSS JOIN (SELECT generate_series({first}, {current}, {step})::date AS periodo) AS serie "
        "LEFT JOIN periodos ON {same} AND periodos.periodo = serie.periodo) "
        "SELECT {dims}, {value_now} AS {valor}, {base_before} AS {base}, {delta} AS {delta_name}{extra_now} "
        "FROM marco GROUP BY {group}"
    ).format(
        inner=inner,
        entity=sql.SQL(", ").join(sql.Identifier(name) for name in names),
        framed=sql.SQL(", ").join(sql.Identifier("entidades", name) for name in names),
        fill=sql.SQL("coalesce(periodos.valor, 0)") if filled else sql.SQL("periodos.valor"),
        extra_fill=sql.SQL("").join(
            sql.SQL(", {} AS {}").format(ZERO.format(sql.Identifier("periodos", name)) if aggregate in ZERO_WHEN_EMPTY else sql.Identifier("periodos", name), sql.Identifier(name))
            for name, _, _, aggregate in extras
        ),
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
        extra_now=sql.SQL("").join(
            sql.SQL(", max({}) FILTER (WHERE marco.periodo = {})::{} AS {}").format(sql.Identifier("marco", name), current, TYPES[k], sql.Identifier(name))
            for name, _, k, _ in extras
        ),
        group=sql.SQL(", ").join(sql.Identifier("marco", name) for name in names),
    )
    columns = tuple((name, k) for name, _, k in dims) + ((out["valor"], "numeric"), (out["base"], "numeric"), (out["delta"], "numeric")) + tuple((name, k) for name, _, k, _ in extras)
    return Compiled(query, columns, tuple(name for name, _, _ in dims))


def threshold(name: str, available: Mapping[str, tuple[sql.Composable, str]], thresholds: Mapping[str, Any]) -> tuple[sql.Composable, str]:
    spec = thresholds.get(name)
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        return sql.Literal(spec), "numeric"
    if isinstance(spec, Mapping) and "columna" in spec and spec["columna"] in available:
        return available[spec["columna"]]
    if isinstance(spec, Mapping) and "por" in spec and spec["por"] in available:
        cases = sql.SQL(" ").join(WHEN_VALUE.format(sql.Literal(key), sql.Literal(number)) for key, number in spec["valores"].items())
        return BY_VALUE.format(available[spec["por"]][0], cases), "numeric"
    raise Refused("lenguaje", f"derivadas: umbral {name} names no numeric threshold of this KPI's umbrales over its own columns")


def unify(left: str, right: str, key: str) -> str:
    if left == right:
        return left
    if {left, right} == {"integer", "bigint"}:
        return "bigint"
    if left in NUMERIC and right in NUMERIC:
        return "numeric"
    raise Refused("lenguaje", f"derivadas: {key} mixes a {left} with a {right}")


def derived(node: Any, available: Mapping[str, tuple[sql.Composable, str]], day: sql.Composable, thresholds: Mapping[str, Any], frame: tuple[tuple[str, ...], tuple[str, ...]], depth: int = 1) -> tuple[sql.Composable, str]:
    if isinstance(node, Mapping) and depth > MAX_DERIVED_DEPTH:
        raise Refused("lenguaje", f"derivadas nest at most {MAX_DERIVED_DEPTH} operations")
    if node == "dia":
        return day, "date"
    if isinstance(node, str):
        if node not in available:
            raise Refused("lenguaje", f"derivadas: {node} is no column this KPI outputs before it")
        return available[node]
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return sql.Literal(node), "integer" if isinstance(node, int) else "numeric"
    inner = lambda child: derived(child, available, day, thresholds, frame, depth + 1)
    if "umbral" in node:
        return threshold(node["umbral"], available, thresholds)
    if "op" in node:
        left, left_kind = inner(node["izq"])
        right, right_kind = inner(node["der"])
        return arithmetic(node["op"], left, left_kind, right, right_kind)
    if "mayor" in node or "menor" in node:
        key = "mayor" if "mayor" in node else "menor"
        (left, left_kind), (right, right_kind) = (inner(item) for item in node[key])
        return GREATEST[key].format(left, right), unify(left_kind, right_kind, key)
    if "dias_habiles" in node:
        (start, start_kind), (end, end_kind) = inner(node["dias_habiles"]["desde"]), inner(node["dias_habiles"]["hasta"])
        if start_kind != "date" or end_kind != "date":
            raise Refused("lenguaje", "derivadas: dias_habiles counts the days between two dates")
        return BUSINESS_DAYS.format(start, end), "integer"
    if "compara" in node:
        spec = node["compara"]
        (left, left_kind), (right, right_kind) = inner(spec["izq"]), inner(spec["der"])
        if not comparable(left_kind, right_kind):
            raise Refused("lenguaje", f"derivadas: compara cannot compare a {left_kind} with a {right_kind}")
        return COMPARE[spec["op"]].format(left, right), "boolean"
    if "existe" in node:
        return EXISTS.format(inner(node["existe"])[0]), "boolean"
    if "participacion" in node:
        share, kind = inner(node["participacion"])
        if kind not in NUMERIC:
            raise Refused("lenguaje", "derivadas: participacion needs a number")
        return SHARE.format(x=share), "numeric"
    if "periodo_anterior" in node:
        return previous(node["periodo_anterior"], available, frame)
    spec = node["si"]
    when, when_kind = inner(spec["cuando"])
    if when_kind != "boolean":
        raise Refused("lenguaje", "derivadas: si needs cuando to be a comparison or existe")
    (then, then_kind), (otherwise, otherwise_kind) = inner(spec["entonces"]), inner(spec["sino"])
    return WHEN.format(when, then, otherwise), unify(then_kind, otherwise_kind, "si")


def previous(name: str, available: Mapping[str, tuple[sql.Composable, str]], frame: tuple[tuple[str, ...], tuple[str, ...]]) -> tuple[sql.Composable, str]:
    periods, others = frame
    if len(periods) != 1:
        raise Refused("lenguaje", "derivadas: periodo_anterior needs agrupar to hold exactly one {columna, por}")
    if name not in available:
        raise Refused("lenguaje", f"derivadas: {name} is no column this KPI outputs before it")
    partition = PARTITION.format(sql.SQL(", ").join(sql.Identifier("nucleo", other) for other in others)) if others else sql.SQL("")
    period = periods[0]
    return PREVIOUS.format(x=available[name][0], partition=partition, period=sql.Identifier("nucleo", period), step=STEP[period]), available[name][1]


def finish(block: Mapping[str, Any], core: Compiled, day: sql.Composable, thresholds: Mapping[str, Any]) -> Compiled:
    available = {name: (sql.Identifier("nucleo", name), kind) for name, kind in core.columns}
    periods = tuple(item["por"] for item in block["agrupar"] if not isinstance(item, str))
    frame = (periods, tuple(name for name in core.entity if name not in periods))
    columns = list(core.columns)
    for name, node in block.get("derivadas", {}).items():
        available[name] = derived(node, available, day, thresholds, frame)
        columns.append((name, available[name][1]))
    places = block.get("decimales", {})
    for name in places:
        if name in core.entity or name not in available or available[name][1] not in NUMERIC:
            raise Refused("lenguaje", f"decimales: {name} is no numeric output column of this KPI")
    selected = []
    for name, kind in columns:
        expr = available[name][0]
        if name in places:
            expr, kind = ROUND.format(expr, sql.Literal(places[name])), "numeric"
        selected.append(sql.SQL("{}::{} AS {}").format(expr, TYPES[kind], sql.Identifier(name)))
    columns = [(name, "numeric" if name in places else kind) for name, kind in columns]
    query = sql.SQL("SELECT {} FROM ({}) AS nucleo").format(sql.SQL(", ").join(selected), core.query)
    kinds = dict(columns)
    having = []
    for spec in block.get("tener", []):
        if kinds.get(spec["columna"]) not in NUMERIC:
            raise Refused("lenguaje", f"tener: {spec['columna']} is no numeric output column of this KPI")
        having.append(COMPARE[spec["op"]].format(sql.Identifier("kpi", spec["columna"]), sql.Literal(spec["valor"])))
    if having:
        query = sql.SQL("SELECT * FROM ({}) AS kpi WHERE {}").format(query, sql.SQL(" AND ").join(having))
    return Compiled(query, tuple(columns), core.entity)


def function_definition(metric: str, block: Mapping[str, Any], sources: Sources, thresholds: Mapping[str, Any] | None = None) -> sql.Composable:
    if NAME.match(metric) is None:
        raise Refused("lenguaje", f"{metric} is not a metric name of lowercase letters, digits and underscores")
    compiled = compile_kpi(block, sources, day=sql.SQL("dia"), thresholds=thresholds)
    function = sql.Identifier("centinela", f"k_{metric}")
    returns = sql.SQL(", ").join(sql.SQL("{} {}").format(sql.Identifier(name), TYPES[kind]) for name, kind in compiled.columns)
    return sql.SQL(
        "DROP FUNCTION IF EXISTS {fn}(date);\n"
        "CREATE FUNCTION {fn}(dia date) RETURNS TABLE ({returns}) LANGUAGE sql STABLE SECURITY DEFINER "
        "SET search_path = pg_catalog, pg_temp AS {body};\n"
        "ALTER FUNCTION {fn}(date) OWNER TO centinela_propietario;\n"
        "REVOKE ALL ON FUNCTION {fn}(date) FROM PUBLIC;\n"
        "GRANT EXECUTE ON FUNCTION {fn}(date) TO centinela_lector;\n"
    ).format(fn=function, returns=returns, body=sql.Literal(compiled.query.as_string()))
