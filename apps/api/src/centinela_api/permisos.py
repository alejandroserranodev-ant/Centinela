from centinela_agents.graph import manual_owners
from centinela_agents.skills import skill

from .modelos import Alert, Persona

GERENCIA = "Gerencia"


def responsable(metric: str) -> str | None:
    return manual_owners(skill("estratega", "acciones")).get(metric)


def puede_decidir(persona: Persona, alerta: Alert) -> bool:
    if persona.role == "gerente":
        return True
    area = responsable(alerta.metric)
    return persona.role == "lider_proceso" and area is not None and persona.area == area


def puede_configurar(persona: Persona) -> bool:
    return persona.role in ("analista", "gerente")


def negada(alerta: Alert) -> str:
    area = responsable(alerta.metric)
    return f"Esta alerta la decide {area}" if area else "Esta alerta la decide la gerencia"


def vista(persona: Persona, alerta: Alert) -> Alert:
    return alerta.model_copy(update={
        "decided_by": responsable(alerta.metric) or GERENCIA,
        "can_decide": puede_decidir(persona, alerta),
    })
