import operator
import re
from typing import Any, Mapping

KPI_PATH = re.compile(r"^kpi\.([a-z0-9_]+)\.([a-z0-9_]+)$")
STATE_PATH = re.compile(r"^estado(\.[a-z_]+)+$")
ORDER = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "!=": operator.ne,
}


def is_kpi(lee: str) -> bool:
    return KPI_PATH.match(lee) is not None


def kpi_column(lee: str) -> tuple[str, str]:
    match = KPI_PATH.match(lee)
    if match is None:
        raise ValueError(f"{lee} names no KPI column")
    return match.group(1), match.group(2)


def compare(op: str, left: Any, right: Any) -> bool:
    if op == "existe":
        return left is not None and left != [] and left != {}
    if op == "en":
        return left in right
    if left is None or right is None:
        return False
    return ORDER[op](left, right)


def threshold_value(spec: Any, row: Mapping[str, Any]) -> Any:
    if isinstance(spec, dict) and "columna" in spec:
        return row.get(spec["columna"])
    if isinstance(spec, dict) and "por" in spec:
        key = row.get(spec["por"])
        return None if key is None else spec["valores"].get(str(key))
    return spec
