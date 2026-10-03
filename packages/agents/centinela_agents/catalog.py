from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .metrics import Metrics

KpiReader = Callable[[str, str], list[Mapping[str, Any]]]
KernelCall = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class Kpi:
    entity: tuple[str, ...]
    columns: frozenset[str]
    descriptive: bool = False
    thresholds: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Catalog:
    kpis: Mapping[str, Kpi]


def thresholds_named(name: str, metrics: Metrics, catalog: Catalog) -> Mapping[str, Any] | None:
    if name in metrics.thresholds:
        return metrics.thresholds[name]
    kpi = catalog.kpis.get(name)
    return kpi.thresholds if kpi is not None and kpi.thresholds else None


def catalog_from_kernel(answer: Mapping[str, Any]) -> Catalog:
    return Catalog(
        {
            kpi["id"]: Kpi(tuple(kpi["entidad"]), frozenset(column["nombre"] for column in kpi["columnas"]), bool(kpi["descriptivo"]))
            for kpi in answer["kpis"]
        }
    )


def kernel_reader(call: KernelCall) -> KpiReader:
    def read(metric: str, day: str) -> list[Mapping[str, Any]]:
        answer = call("kpi_consultar", {"kpi": metric, "dia": day})
        if "rechazado" in answer:
            raise RuntimeError(f"the kernel refused {metric} on {day}: {answer['rechazado']['guarda']}: {answer['rechazado']['detalle']}")
        return list(answer["filas"])

    return read
