from .modelos import AlertStatus

ESTADO_A_STATUS: dict[str, AlertStatus] = {
    "nueva": "new",
    "en_analisis": "analyzing",
    "propuesta": "proposed",
    "aprobada": "approved",
    "rechazada": "rejected",
    "ejecutada": "executed",
}

TRANSICIONES: dict[AlertStatus, frozenset[AlertStatus]] = {
    "new": frozenset({"analyzing"}),
    "analyzing": frozenset({"proposed"}),
    "proposed": frozenset({"approved", "rejected"}),
    "approved": frozenset({"executed"}),
    "rejected": frozenset(),
    "executed": frozenset(),
}


class TransicionInvalida(Exception):
    pass


def transicionar(actual: AlertStatus, siguiente: AlertStatus) -> None:
    if siguiente not in TRANSICIONES[actual]:
        raise TransicionInvalida(f"{actual} -> {siguiente} no está en el ciclo de vida")


def recorrer(estados: list[AlertStatus]) -> None:
    if not estados or estados[0] != "new":
        raise TransicionInvalida(f"el ciclo de vida empieza en new, no en {estados[:1]}")
    for actual, siguiente in zip(estados, estados[1:]):
        transicionar(actual, siguiente)
