from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .yaml_loader import load_yaml


@dataclass(frozen=True)
class Metrics:
    descriptions: Mapping[str, str]
    thresholds: Mapping[str, Mapping[str, Any]]
    labels: Mapping[str, str] = field(default_factory=dict)
    dimension_labels: Mapping[str, str] = field(default_factory=dict)
    rules: Mapping[str, str] = field(default_factory=dict)
    threshold_sources: Mapping[str, str] = field(default_factory=dict)
    severities: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    tranches: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    periods: Mapping[str, str] = field(default_factory=dict)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self.descriptions)


def load_metrics(path: Path) -> Metrics:
    document = load_yaml(path)
    entries = document["metricas"]
    return Metrics(
        descriptions={name: entry["descripcion"] for name, entry in entries.items()},
        thresholds={name: entry.get("umbrales", {}) for name, entry in entries.items()},
        labels={name: entry["etiqueta"] for name, entry in entries.items()},
        dimension_labels=document["nombres_dimensiones"],
        rules={name: entry.get("umbral_alerta", "") for name, entry in entries.items()},
        threshold_sources={name: entry.get("fuente_umbral", "") for name, entry in entries.items()},
        severities={name: entry["severidad"] for name, entry in entries.items() if "severidad" in entry},
        tranches={name: entry["tramos"] for name, entry in entries.items() if "tramos" in entry},
        periods={name: entry["kernel"]["linea_base"]["periodo"] for name, entry in entries.items() if "linea_base" in entry.get("kernel", {})},
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
