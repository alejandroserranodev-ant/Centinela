from collections.abc import Mapping

from . import ciclo_vida
from .modelos import Alert, AutonomyLevel, Decision, DecisionApprove, DecisionEdit, DecisionRequestChanges, LogEventType

SOLO_INFORMA = "Este tipo de acción solo informa: no se aprueba desde Centinela"


CAMBIOS_YA_PEDIDOS = "Ya se pidieron cambios una vez: queda aprobar, editar o rechazar"


class ConflictoEstado(Exception):
    pass


class DecisionInvalida(Exception):
    pass


def aplicar(
    alerta: Alert, decision: Decision, autonomia: Mapping[str, AutonomyLevel]
) -> tuple[Alert, list[tuple[LogEventType, str]]]:
    if alerta.status != "proposed":
        raise ConflictoEstado("Esta alerta ya no espera una decisión")

    if decision.kind == "reject":
        motivo = decision.reason.strip()
        if not motivo:
            raise DecisionInvalida("Para rechazar hace falta un motivo")
        ciclo_vida.transicionar(alerta.status, "rejected")
        nueva = alerta.model_copy(update={"status": "rejected"})
        return nueva, [("decision", f"Rechazada. Motivo: {motivo}")]

    if isinstance(decision, DecisionRequestChanges):
        motivo = decision.reason.strip()
        if not motivo:
            raise DecisionInvalida("Para pedir cambios hace falta un motivo")
        if alerta.changes_requested:
            raise ConflictoEstado(CAMBIOS_YA_PEDIDOS)
        nueva = alerta.model_copy(update={"changes_requested": True})
        return nueva, [("decision", f"Cambios solicitados. Motivo: {motivo}")]

    accion = next((a for a in alerta.actions if a.id == decision.action_id), None)
    if accion is None:
        raise DecisionInvalida("La acción elegida no pertenece a esta alerta")
    if autonomia.get(accion.type) == "inform":
        raise DecisionInvalida(SOLO_INFORMA)

    acciones = list(alerta.actions)
    if isinstance(decision, DecisionEdit):
        indice = acciones.index(accion)
        accion = accion.model_copy(update={"parameters": {**accion.parameters, **decision.parameters}})
        acciones[indice] = accion

    ciclo_vida.transicionar(alerta.status, "approved")
    nueva = alerta.model_copy(update={"status": "approved", "actions": acciones})
    detalle = (
        f"Aprobada: {accion.title}"
        if isinstance(decision, DecisionApprove)
        else f"Aprobada con cambios: {accion.title}"
    )
    return nueva, [("decision", detalle)]
