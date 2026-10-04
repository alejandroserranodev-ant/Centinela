import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .catalog import Catalog, KernelCall, KpiReader
from .metrics import Metrics
from .predicate import is_kpi, kpi_column
from .schema import Node

MONEY = ("pesos_en_riesgo", "saldo", "ventas", "costo", "precio", "valor", "margen_bruto", "descuento_en_exceso", "exceso_semana_anterior", "cupo")
COUNTS = ("existencia", "demanda", "unidades", "pedidos", "cantidad", "facturas", "veces_")
MAX_RELATED_ROWS = 3
ALLOWED_NUMBERS = (r"\{\d+\}", r"\d{4}-\d{2}-\d{2}", r"\b[A-Z]{3}-POL-\d{3}\b", r"§\s?\d+")


class UnknownFigure(ValueError):
    pass


def unit_of(column: str) -> str:
    if column.endswith("_pct"):
        return "percent"
    if column.endswith("_pts"):
        return "points"
    if column.startswith(COUNTS):
        return "units"
    if column.startswith(MONEY):
        return "COP"
    if "dias" in column:
        return "days"
    return "units"


def query_id(consulta: str, day: str) -> str:
    return "q_" + hashlib.sha256(f"{consulta}|{day}".encode()).hexdigest()[:12]


def stray_digits(text: str, allowed: tuple[str, ...] = ()) -> bool:
    for pattern in ALLOWED_NUMBERS:
        text = re.sub(pattern, " ", text)
    for token in sorted(allowed, key=len, reverse=True):
        text = text.replace(token, " ")
    return re.search(r"\d", text) is not None


def placeholders(text: str) -> set[int]:
    return {int(index) for index in re.findall(r"\{(\d+)\}", text)}


def fills(text: str, figures: int) -> bool:
    return all(index < figures for index in placeholders(text))


def cited(text: str, refs: list[str]) -> list[str]:
    indexes = placeholders(text)
    return refs[: max(indexes) + 1] if indexes else []


def call_from_reader(reader: KpiReader) -> KernelCall:
    def call(name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if name != "kpi_consultar":
            raise ValueError(f"a reader answers kpi_consultar, not {name}")
        kpi, day = arguments["kpi"], arguments["dia"]
        return {"kpi": kpi, "dia": day, "consulta": f"kpi_consultar('{kpi}', '{day}')", "filas": reader(kpi, day)}

    return call


@dataclass(frozen=True)
class Fact:
    ref: str
    kpi: str
    column: str
    entity: tuple[Any, ...]
    value: int | float
    query_id: str

    def figure(self) -> dict[str, Any]:
        return {"value": self.value, "unit": unit_of(self.column), "queryId": self.query_id}

    def line(self) -> str:
        entity = ", ".join(map(str, self.entity))
        return f"{self.ref}: {self.kpi}.{self.column} de {entity} = {self.value} ({unit_of(self.column)})"


@dataclass
class Ledger:
    call: KernelCall
    catalog: Catalog
    queries: dict[str, dict[str, Any]] = field(default_factory=dict)
    facts: list[Fact] = field(default_factory=list)

    def consult(self, kpi: str, day: str) -> tuple[str, list[Mapping[str, Any]]]:
        answer = self.call("kpi_consultar", {"kpi": kpi, "dia": day})
        if "rechazado" in answer:
            raise RuntimeError(f"the kernel refused {kpi} on {day}: {answer['rechazado']['guarda']}: {answer['rechazado']['detalle']}")
        qid = query_id(answer["consulta"], day)
        self.queries[qid] = {"queryId": qid, "kpi": kpi, "dia": day, "consulta": answer["consulta"]}
        return qid, list(answer["filas"])

    def add(self, kpi: str, row: Mapping[str, Any], qid: str, columns: tuple[str, ...] | None = None) -> list[Fact]:
        entity_columns = self.catalog.kpis[kpi].entity
        entity = tuple(row.get(column) for column in entity_columns)
        added = []
        for column in columns or tuple(row):
            value = row.get(column)
            if column in entity_columns or isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            fact = Fact(f"f{len(self.facts) + 1}", kpi, column, entity, value, qid)
            self.facts.append(fact)
            added.append(fact)
        return added

    def alert_row(self, metric: str, entity: list[Any], day: str) -> tuple[str, Mapping[str, Any] | None]:
        qid, rows = self.consult(metric, day)
        columns = self.catalog.kpis[metric].entity
        matching = [row for row in rows if [row.get(column) for column in columns] == list(entity)]
        return qid, matching[0] if matching else None

    def related(self, metric: str, entity: list[Any], day: str) -> None:
        keys = dict(zip(self.catalog.kpis[metric].entity, entity))
        for kpi, spec in self.catalog.kpis.items():
            shared = {column: value for column, value in keys.items() if column in spec.columns}
            if kpi == metric or not shared:
                continue
            qid, rows = self.consult(kpi, day)
            matching = [row for row in rows if all(row.get(column) == value for column, value in shared.items())]
            for row in matching[:MAX_RELATED_ROWS]:
                self.add(kpi, row, qid, tuple(column for column in row if column != "pesos_en_riesgo"))

    def by_ref(self) -> dict[str, Fact]:
        return {fact.ref: fact for fact in self.facts}

    def figures(self, refs: list[str]) -> list[dict[str, Any]]:
        known = self.by_ref()
        unknown = [ref for ref in refs if ref not in known]
        if unknown:
            raise UnknownFigure(f"the model cited figures no query returned: {unknown}")
        return [known[ref].figure() for ref in refs]

    def lines(self) -> str:
        return "\n".join(fact.line() for fact in self.facts)

    def query_list(self) -> list[dict[str, Any]]:
        return list(self.queries.values())


def merged_queries(state: Mapping[str, Any], ledger: Ledger) -> list[dict[str, Any]]:
    known = {query["queryId"]: query for query in state.get("queries") or [] if isinstance(query, Mapping)}
    known.update(ledger.queries)
    return list(known.values())


@dataclass(frozen=True)
class Sources:
    call: KernelCall
    catalog: Catalog
    metrics: Metrics
    nodes: Mapping[str, Node]

    def ledger(self) -> Ledger:
        return Ledger(self.call, self.catalog)

    def compared(self, detection: Mapping[str, Any]) -> tuple[str, ...]:
        columns = []
        for node_id, branch in detection.get("path") or []:
            node = self.nodes.get(node_id)
            if branch != "si" or node is None or node.predicado is None or not is_kpi(node.predicado.lee):
                continue
            metric, column = kpi_column(node.predicado.lee)
            if metric == detection["metric"] and column not in columns:
                columns.append(column)
        return tuple(columns)
