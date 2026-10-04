from typing import Any, Iterable, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

STAGES = ("detectar", "explicar", "proponer", "aprobar", "ejecutar", "cerrar", "medir", "conversar")
FAMILIES = ("cartera", "margen", "inventario", "comercial", "abastecimiento", "clientes")
AGENT_DECISIONS = {
    "vigia": ("detectar", "titular", "proponer_kpi", "expandir"),
    "analista": ("explicar", "expandir"),
    "estratega": ("proponer", "revision_manual", "expandir"),
    "ejecutor": ("ejecutar", "nota_manual", "expandir"),
    "chat": ("clasificar", "responder"),
}
AGENT_STAGE = {"vigia": "detectar", "analista": "explicar", "estratega": "proponer", "ejecutor": "ejecutar", "chat": "conversar"}
ENDS = frozenset(
    {
        "fin.sin_alerta",
        "fin.unida",
        "fin.rechazada",
        "fin.recarga_agotada",
        "fin.ya_no_aplica",
        "fin.ejecutada",
        "fin.fallo_ejecucion",
        "fin.chat_respondida",
        "fin.chat_sin_evidencia",
        "fin.chat_otro_periodo",
        "fin.chat_fuera_de_alcance",
        "fin.chat_rechazada",
    }
)
ROOT = "detectar.raiz"
CHAT_ROOT = "conversar.raiz"
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




class Figure(BaseModel):
    """
    A single numeric or text figure from a tool query.

    Every figure in agent output (Cause, Action, ExecutedAction) must have:
    - value: the actual value (int, float, str)
    - unit: unit of measure (COP, %, days, units, etc.) or None for dimensionless
    - queryId: unique identifier of the query that produced this figure
    """
    model_config = ConfigDict(extra="forbid")

    value: int | float | str
    unit: str | None = None
    queryId: str

class Sentence(BaseModel):
    """Natural language statement with optional supporting figures."""
    model_config = ConfigDict(extra="forbid")

    text: str
    figures: list[Figure] = Field(default_factory=list)

class Evidence(BaseModel):
    """
    One piece of evidence supporting a cause.

    claim: Spanish text describing what the evidence shows
    figures: list of Figure objects referenced in the claim (matched by placeholder {0}, {1}, etc.)
    """
    model_config = ConfigDict(extra="forbid")

    claim: str
    figures: list[Figure] = Field(default_factory=list)


class Confidence(BaseModel):
    """
    Confidence assessment of an agent's output.

    level: high (two views or formulas support it)
           medium (one view or formula)
           low (passes tests but incomplete or no formula)
    assumptions: list of limitations, clock constraints, or missing evidence
    """
    model_config = ConfigDict(extra="forbid")

    level: Literal["high", "medium", "low"]
    assumptions: list[str] = Field(default_factory=list)


class CauseIdentified(BaseModel):
    """Cause that Analista identified with evidence."""
    model_config = ConfigDict(extra="forbid")

    kind: Literal["identified"]
    sentence: Sentence | str
    evidence: list[Evidence] = Field(min_length=1)
    confidence: Confidence | None = None
    same_cause_as: str | None = None


class CauseNoEvidence(BaseModel):
    """Cause could not be identified due to insufficient evidence."""
    model_config = ConfigDict(extra="forbid")

    kind: Literal["no_evidence"]
    reason: str
    queriesReviewed: list[str] = Field(default_factory=list)


Cause = CauseIdentified | CauseNoEvidence


class Action(BaseModel):
    """
    Action proposed by Estratega for an alert.

    type: one of the closed list (email_draft, task, purchase_order_draft, price_change_draft)
    parameters: dict of action-specific parameters (cliente_id, sku, owner, etc.)
    impact: figure showing the impact of this action (null if no formula)
    """
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    type: Literal["email_draft", "task", "purchase_order_draft", "price_change_draft"]
    parameters: dict[str, str | int | float]
    impact: Figure | None = None
    confidence: Confidence


class InsufficientCause(BaseModel):
    """Estratega found no action that the cause supports."""
    model_config = ConfigDict(extra="forbid")

    insufficient_cause: bool = True


class ExecutedAction(BaseModel):
    """
    Result of executing an approved action (Ejecutor output).

    Either a draft (email_draft, price_change_draft, purchase_order_draft)
    or a manual task (task, manual note).
    """
    model_config = ConfigDict(extra="forbid")

    actionId: str
    type: Literal["email_draft", "task", "purchase_order_draft", "price_change_draft", "nota_manual"]
    result: str
    parameters: dict[str, str | int | float]


class Decision(BaseModel):
    """
    Human decision on an alert (recorded by API, used to resume).

    kind: approve (execute this action)
          edit (execute with modified parameters)
          reject (refuse and end the alert)
          request_changes (ask Estratega to propose again)
    """
    model_config = ConfigDict(extra="forbid")

    kind: Literal["approve", "edit", "reject", "request_changes"]
    actionId: str | None = None
    parameters: dict[str, str | int | float] | None = None
    reason: str | None = None


class RejectionClassifierOutput(BaseModel):
    """
    Orquestador classifier output: where to route the rejection reason.

    destino: causa (route to Analista)
             propuesta (route to Estratega)
             ambos (route to both)
             ninguno (keep in log, no agent action)
    """
    model_config = ConfigDict(extra="forbid")

    destino: Literal["causa", "propuesta", "ambos", "ninguno"]


class ChatAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    figures: list[Figure] = Field(default_factory=list)
    enough_evidence: bool
    assumptions: list[str] = Field(default_factory=list)
