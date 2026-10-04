# The fake day run the router tests drive: it yields the events it is given, collects the verdict
# avanzar sends back for each AlertRun, and serves a walk context built with no database.
from unittest.mock import MagicMock

from centinela_agents.catalog import catalog_from_kernel
from centinela_agents.day import AlertRun
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Tree
from centinela_agents.walk import Context, Detection
from centinela_agents.yaml_loader import load_yaml
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_catalogo, load_entries

from centinela_api import agentes
from centinela_api.routers import simulacion as simulacion_router

ARBOL = Tree.model_validate(load_yaml(agentes._ARBOL))
CONTEXTO = Context.of(
    ARBOL,
    load_metrics(agentes.METRICAS),
    catalog_from_kernel({"kpis": kpi_catalogo(catalogue_of(load_entries(agentes.METRICAS), load_sources()))}),
    lambda metric, day: [],
)


def deteccion(cliente: str = "CLI-001", pesos: float | None = 1000.0, metric: str = "saldo_vencido", dia: str = "2026-01-15", severity: str = "high") -> Detection:
    consulta = {"queryId": f"q_{metric}_{cliente}", "kpi": metric, "dia": dia, "consulta": f"kpi_consultar('{metric}', '{dia}')", "filas": []}
    figura = None if pesos is None else {"value": pesos, "unit": "COP", "queryId": consulta["queryId"]}
    fila = {"cliente_id": cliente, "max_dias_vencido": 40, "saldo_vencido": pesos, "pesos_en_riesgo": pesos}
    return Detection(metric, (cliente,), "hoja.vigia.titular", (), fila, severity=severity, pesos=figura, query=consulta)


def corrida(alert_id: str, detection: Detection, *estados: str, absorbed=None, **estado) -> AlertRun:
    state = {"status": estados[-1], "transitions": [[alert_id, e] for e in estados], "actions": [], "queries": [dict(detection.query)], **estado}
    return AlertRun(alert_id, detection, state, dict(absorbed or {}))


def dia_con(monkeypatch, *eventos, anteriores=()):
    veredictos: list = []
    llamadas: list = []

    def run_day(ctx, day, **opciones):
        llamadas.append(opciones)
        for evento in eventos:
            recibido = yield evento
            if isinstance(evento, AlertRun):
                veredictos.append(recibido)

    orquestador = MagicMock()
    orquestador.run_day.side_effect = run_day
    monkeypatch.setattr(simulacion_router, "get_orchestrator", lambda: orquestador)
    monkeypatch.setattr(simulacion_router, "get_context", lambda: CONTEXTO)
    monkeypatch.setattr(agentes, "get_context", lambda: CONTEXTO)
    monkeypatch.setattr(simulacion_router.alertas_repo, "anteriores", lambda conn: list(anteriores))
    monkeypatch.setattr(simulacion_router.alertas_repo, "fijar_entidad", MagicMock())
    monkeypatch.setattr(simulacion_router.alertas_repo, "fijar_costo", MagicMock())
    monkeypatch.setattr(simulacion_router.consultas, "registrar", MagicMock())
    monkeypatch.setattr(simulacion_router.arboles, "del_dia", lambda conn, dia: ARBOL)
    monkeypatch.setattr(simulacion_router.alertas_repo, "fijar_version", MagicMock())
    return veredictos, llamadas
