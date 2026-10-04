from centinela_agents.graph import manual_owners
from centinela_agents.skills import skill

from . import auth
from .modelos import Alert, Persona

GERENCIA = "Gerencia"


def responsable(metric: str) -> str | None:
    return manual_owners(skill("estratega", "acciones")).get(metric)


def area_que_decide(metric: str) -> str | None:
    area = responsable(metric)
    lideres = {p.area for p in auth.PERFILES.values() if p.rol == "lider_proceso" and p.area}
    return area if area in lideres else None


def puede_decidir(persona: Persona, alerta: Alert) -> bool:
    if persona.role == "gerente":
        return True
    area = area_que_decide(alerta.metric)
    return persona.role == "lider_proceso" and area is not None and persona.area == area


def puede_configurar(persona: Persona) -> bool:
    return persona.role in ("analista", "gerente")


def negada(alerta: Alert) -> str:
    area = area_que_decide(alerta.metric)
    return f"Esta alerta la decide {area}" if area else "Esta alerta la decide la gerencia"


def vista(persona: Persona, alerta: Alert) -> Alert:
    return alerta.model_copy(update={
        "decided_by": area_que_decide(alerta.metric) or GERENCIA,
        "can_decide": puede_decidir(persona, alerta),
    })
