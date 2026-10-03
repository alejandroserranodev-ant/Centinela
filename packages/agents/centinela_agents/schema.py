from typing import Any, Iterable, Literal, Mapping

from pydantic import BaseModel, ConfigDict

STAGES = ("detectar", "explicar", "proponer", "aprobar", "ejecutar", "cerrar", "medir")
FAMILIES = ("cartera", "margen", "inventario", "comercial", "abastecimiento", "clientes")
AGENT_DECISIONS = {
    "vigia": ("detectar", "titular", "proponer_kpi", "expandir"),
    "analista": ("explicar", "responder_chat", "expandir"),
    "estratega": ("proponer", "revision_manual", "expandir"),
    "ejecutor": ("ejecutar", "nota_manual", "expandir"),
}
AGENT_STAGE = {"vigia": "detectar", "analista": "explicar", "estratega": "proponer", "ejecutor": "ejecutar"}
ENDS = frozenset(
    {
        "fin.sin_alerta",
        "fin.unida",
        "fin.rechazada",
        "fin.recarga_agotada",
        "fin.ya_no_aplica",
        "fin.ejecutada",
        "fin.fallo_ejecucion",
    }
)
ROOT = "detectar.raiz"
GATE = "aprobar.decision"
VIGENTE = "ejecutar.vigente"
Operator = Literal[">", ">=", "<", "<=", "=", "!=", "en", "existe"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Predicate(Strict):
    lee: str
    op: Operator
    umbral: str | None = None
    valor: Any = None


class Leaf(Strict):
    agente: str
    decision: str
    skill: str


class Node(Strict):
    id: str
    fundamento: str | None = None
    predicado: Predicate | None = None
    si: str | None = None
    no: str | None = None
    hoja: Leaf | None = None
    sigue: str | None = None


class Law(Strict):
    id: str
    fundamento: str


class Tree(Strict):
    version: int
    leyes: tuple[Law, ...] = ()
    nodos: tuple[Node, ...]


def index(tree: Tree) -> dict[str, Node]:
    return {node.id: node for node in tree.nodos}


def branches(node: Node) -> list[tuple[str, str]]:
    if node.hoja is not None:
        return [("sigue", node.sigue)] if node.sigue else []
    return [(name, target) for name, target in (("si", node.si), ("no", node.no)) if target]


def level(node_id: str) -> int:
    parts = node_id.split(".")
    if parts[0] in STAGES and len(parts) >= 2 and parts[1] in FAMILIES:
        return 2 if len(parts) == 2 else 3
    return 1


def stage_of(target: str, nodes: Mapping[str, Node]) -> str:
    if target in ENDS:
        return "cerrar"
    node = nodes.get(target)
    if node is not None and node.hoja is not None:
        return AGENT_STAGE.get(node.hoja.agente, "")
    return target.split(".")[0]


def reachable(nodes: Mapping[str, Node], starts: Iterable[str], without: frozenset[str] = frozenset()) -> set[str]:
    seen: set[str] = set()
    stack = [start for start in starts if start not in without]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        node = nodes.get(current)
        if node is not None:
            stack.extend(target for _, target in branches(node) if target not in without)
    return seen
