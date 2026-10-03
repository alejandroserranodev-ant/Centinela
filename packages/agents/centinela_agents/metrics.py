from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .yaml_loader import load_yaml


@dataclass(frozen=True)
class Metrics:
    descriptions: Mapping[str, str]
    thresholds: Mapping[str, Mapping[str, Any]]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self.descriptions)


def load_metrics(path: Path) -> Metrics:
    entries = load_yaml(path)["metricas"]
    return Metrics(
        descriptions={name: entry["descripcion"] for name, entry in entries.items()},
        thresholds={name: entry.get("umbrales", {}) for name, entry in entries.items()},
    )


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def threshold_shape_problem(spec: Any) -> str | None:
    if isinstance(spec, bool) or is_number(spec):
        return None
    if isinstance(spec, dict) and set(spec) == {"columna"} and isinstance(spec["columna"], str):
        return None
    if (
        isinstance(spec, dict)
        and set(spec) == {"por", "valores"}
        and isinstance(spec["por"], str)
        and isinstance(spec["valores"], dict)
        and all(is_number(value) for value in spec["valores"].values())
    ):
        return None
    return f"is {spec!r}, which is no number, boolean, columna or por with valores"
