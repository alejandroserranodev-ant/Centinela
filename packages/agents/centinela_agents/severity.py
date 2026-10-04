from typing import Any, Mapping

from .catalog import Catalog
from .metrics import Metrics, is_number
from .predicate import compare

LEVELS = ("critical", "high", "medium", "low")
OPERATORS = (">", ">=", "<", "<=", "=", "!=")


def holds(condition: Mapping[str, Any], row: Mapping[str, Any]) -> bool:
    umbral = condition["umbral"]
    right = row.get(umbral["columna"]) if isinstance(umbral, Mapping) else umbral
    return compare(condition["op"], row.get(condition["columna"]), right)


def tranche_of(metric: str, row: Mapping[str, Any], metrics: Metrics) -> str | None:
    block = metrics.tranches.get(metric)
    if not block:
        return None
    value = row.get(block["columna"])
    if not is_number(value):
        return None
    for level in block["niveles"]:
        if value >= level["desde"] and ("hasta" not in level or value <= level["hasta"]):
            return level["tramo"]
    return None


def severity_of(metric: str, row: Mapping[str, Any], metrics: Metrics) -> str:
    block = metrics.severities[metric]
    tranche = tranche_of(metric, row, metrics)
    for level in sorted(block.get("niveles") or [], key=lambda level: LEVELS.index(level["nivel"])):
        if "tramo" in level and level["tramo"] == tranche:
            return level["nivel"]
        if "cuando" in level and all(holds(condition, row) for condition in level["cuando"]):
            return level["nivel"]
    return block["por_defecto"]["nivel"]


def severity_problems(metrics: Metrics, catalog: Catalog) -> list[str]:
    found: list[str] = []
    for metric in metrics.names:
        kpi = catalog.kpis.get(metric)
        columns = kpi.columns if kpi is not None else frozenset()
        tranches = metrics.tranches.get(metric)
        if tranches is not None:
            found += tranche_problems(metric, tranches, columns)
        block = metrics.severities.get(metric)
        if not isinstance(block, Mapping):
            found.append(f"metric {metric} has no severidad")
            continue
        default = block.get("por_defecto")
        if not isinstance(default, Mapping) or default.get("nivel") not in LEVELS or not str(default.get("fuente") or "").strip():
            found.append(f"metric {metric}: severidad.por_defecto needs a nivel of {', '.join(LEVELS)} and a fuente")
            default = None
        named = {level.get("tramo") for level in (tranches.get("niveles") if isinstance(tranches, Mapping) else None) or [] if isinstance(level, Mapping)}
        for index, level in enumerate(block.get("niveles") or []):
            found += level_problems(f"metric {metric}: severidad.niveles[{index}]", level, columns, named, default)
    return found


def level_problems(where: str, level: Any, columns: frozenset[str], tranches: set, default: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(level, Mapping):
        return [f"{where} is no mapping"]
    found: list[str] = []
    if level.get("nivel") not in LEVELS:
        found.append(f"{where} has nivel {level.get('nivel')!r}, outside {', '.join(LEVELS)}")
    elif default is not None and LEVELS.index(level["nivel"]) >= LEVELS.index(default["nivel"]):
        found.append(f"{where} is {level['nivel']}, no higher than por_defecto")
    if not str(level.get("fuente") or "").strip():
        found.append(f"{where} has no fuente")
    if ("cuando" in level) == ("tramo" in level):
        return [*found, f"{where} needs cuando or tramo, not both nor neither"]
    if "tramo" in level:
        return found if level["tramo"] in tranches else [*found, f"{where} names tramo {level['tramo']}, absent from the metric's tramos"]
    conditions = level["cuando"]
    if not isinstance(conditions, list) or not conditions:
        return [*found, f"{where}: cuando is no list of conditions"]
    for condition in conditions:
        found += condition_problems(where, condition, columns)
    return found


def condition_problems(where: str, condition: Any, columns: frozenset[str]) -> list[str]:
    if not isinstance(condition, Mapping) or set(condition) != {"columna", "op", "umbral"}:
        return [f"{where}: a condition is {condition!r}, not columna, op and umbral"]
    found: list[str] = []
    if condition["columna"] not in columns:
        found.append(f"{where} reads {condition['columna']}, which the metric's KPI does not build")
    if condition["op"] not in OPERATORS:
        found.append(f"{where} compares with {condition['op']!r}, outside {' '.join(OPERATORS)}")
    umbral = condition["umbral"]
    if isinstance(umbral, Mapping):
        if set(umbral) != {"columna"} or umbral["columna"] not in columns:
            found.append(f"{where}: umbral {umbral!r} is no column the metric's KPI builds")
    elif not is_number(umbral):
        found.append(f"{where}: umbral {umbral!r} is no number")
    return found


def tranche_problems(metric: str, block: Any, columns: frozenset[str]) -> list[str]:
    where = f"metric {metric}: tramos"
    if not isinstance(block, Mapping) or set(block) != {"fuente", "columna", "niveles"}:
        return [f"{where} needs fuente, columna and niveles"]
    found: list[str] = []
    if not str(block["fuente"]).strip():
        found.append(f"{where} has no fuente")
    if block["columna"] not in columns:
        found.append(f"{where} reads {block['columna']}, which the metric's KPI does not build")
    levels = block["niveles"]
    if not isinstance(levels, list) or not levels:
        return [*found, f"{where}: niveles is no list"]
    for index, level in enumerate(levels):
        if not isinstance(level, Mapping) or not level.get("tramo") or not is_number(level.get("desde")) or ("hasta" in level and not is_number(level["hasta"])):
            return [*found, f"{where}.niveles[{index}] needs tramo, a number desde and an optional number hasta"]
    for before, after in zip(levels, levels[1:]):
        if "hasta" not in before:
            found.append(f"{where}: {before['tramo']} has no hasta and is not the last")
        elif after["desde"] != before["hasta"] + 1:
            found.append(f"{where}: {before['tramo']} ends at {before['hasta']} and {after['tramo']} starts at {after['desde']}, a gap or an overlap")
    return found
