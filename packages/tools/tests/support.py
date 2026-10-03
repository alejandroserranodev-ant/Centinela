# Helpers the kernel's tests share: a parser of data/sql/01_esquema.sql, so fuentes.yaml is checked
# against the tables the schema really creates, and the fixture KPIs of tests/fixtures/metricas.yaml.
import copy
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from centinela_tools.paths import SQL_DIR

TESTS = Path(__file__).resolve().parent
FIXTURE_METRICAS = TESTS / "fixtures" / "metricas.yaml"
TABLE = re.compile(r"CREATE TABLE (\w+) \((.*?)\);", re.S)
SQL_TYPES = {"varchar": "text", "char": "text", "text": "text", "int": "integer", "bigint": "bigint", "numeric": "numeric", "date": "date"}


@dataclass(frozen=True)
class SchemaTable:
    columns: dict[str, str]
    key: tuple[str, ...]
    references: dict[str, str]


def split_top(body: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in body:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    return [*parts, current.strip()]


def schema_tables(path: Path = SQL_DIR / "01_esquema.sql") -> dict[str, SchemaTable]:
    tables = {}
    for name, body in TABLE.findall(path.read_text()):
        columns, key, references = {}, (), {}
        for part in split_top(body):
            words = part.split()
            if words[0] == "PRIMARY":
                key = tuple(column.strip() for column in part[part.index("(") + 1 : part.rindex(")")].split(","))
                continue
            columns[words[0]] = SQL_TYPES[re.match(r"[a-z]+", words[1]).group(0)]
            if "PRIMARY KEY" in part:
                key = (words[0],)
            if "REFERENCES" in words:
                references[words[0]] = words[words.index("REFERENCES") + 1]
        tables[name] = SchemaTable(columns, key, references)
    return tables


def fixture_entries() -> dict:
    return copy.deepcopy(yaml.safe_load(FIXTURE_METRICAS.read_text())["metricas"])


def fixture_block(metric: str) -> dict:
    return fixture_entries()[metric]["kernel"]
