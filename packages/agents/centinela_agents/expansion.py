import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, Mapping, Sequence

from pydantic import Field, TypeAdapter

from .schema import AGENT_STAGE, ROOT, Node, Strict, Tree, branches, index, level
from .validator import Grounds, capped_return, problems, resolved
from .yaml_loader import load_yaml


class Split(Strict):
    movimiento: Literal["dividir_hoja"] = "dividir_hoja"
    agente: str
    hoja: str
    nodo: Node
    nueva: Node


class Branch(Strict):
    movimiento: Literal["agregar_rama"] = "agregar_rama"
    agente: str
    familia: str
    metrica: str
    nodos: tuple[Node, ...]


class Retire(Strict):
    movimiento: Literal["retirar"] = "retirar"
    nodo: str
    motivo: str
    agente: str | None = None


Move = Annotated[Split | Branch | Retire, Field(discriminator="movimiento")]
MOVE = TypeAdapter(Move)


@dataclass(frozen=True)
class Caps:
    depth: int
    nodes_per_stage: int


@dataclass(frozen=True)
class Growth:
    repetitions: Mapping[str, int]
    caps: Caps


def load_growth(path: Path) -> Growth:
    document = load_yaml(path)
    caps = document["topes"]
    return Growth(
        repetitions={agent: entry["valor"] for agent, entry in document["repeticiones"].items()},
        caps=Caps(caps["profundidad"]["valor"], caps["nodos_por_etapa"]["valor"]),
    )


def entry_of(move) -> str:
    return move.nodo.id if isinstance(move, Split) else move.nodos[0].id


def chain_end(nodes: Mapping[str, Node], family: str) -> tuple[str | None, str | None]:
    last, target = None, nodes[family].si
    while (
        target in nodes
        and target.startswith(family + ".")
        and nodes[target].predicado is not None
        and (nodes[target].predicado.lee, nodes[target].predicado.op) == ("estado.candidato.metrica", "=")
    ):
        last, target = target, nodes[target].no
    return last, target


def replaced(node: Node, old: str, new: str) -> Node:
    return node.model_copy(update={key: new for key in ("si", "no", "sigue") if getattr(node, key) == old})


def apply_move(tree: Tree, move) -> Tree:
    if isinstance(move, Retire):
        nodos = tuple(node.model_copy(update={"retirado": move.motivo}) if node.id == move.nodo else node for node in tree.nodos)
    elif isinstance(move, Split):
        nodos = (*(replaced(node, move.hoja, move.nodo.id) for node in tree.nodos), move.nodo, move.nueva)
    else:
        last, _ = chain_end(index(tree), move.familia)

        def grown(node: Node) -> Node:
            if node.id == move.familia:
                return node.model_copy(update={"predicado": node.predicado.model_copy(update={"valor": [*node.predicado.valor, move.metrica]})})
            if node.id == last:
                return node.model_copy(update={"no": move.nodos[0].id})
            return node

        nodos = (*map(grown, tree.nodos), *move.nodos)
    return tree.model_copy(update={"nodos": nodos})


def fresh_problems(nodes: Mapping[str, Node], new: Sequence[Node]) -> list[str]:
    found = [f"{node.id} is already in the tree" for node in new if node.id in nodes]
    found += [f"{node.id} is born retired" for node in new if node.retirado is not None]
    return found


def retire_problems(nodes: Mapping[str, Node], move: Retire) -> list[str]:
    node = nodes.get(move.nodo)
    if node is None:
        return [f"the retirement names {move.nodo}, which is no node of the tree"]
    found: list[str] = []
    if node.hoja is not None:
        found.append(f"{move.nodo} is a leaf; only an L2 or L3 node retires")
    elif level(move.nodo) == 1:
        found.append(f"{move.nodo} is an L1 node; only an L2 or L3 node retires")
    if node.retirado is not None:
        found.append(f"{move.nodo} is already retired")
    if not move.motivo.strip():
        found.append(f"the retirement of {move.nodo} carries no reason")
    if move.agente is not None and move.nodo.split(".")[0] != AGENT_STAGE.get(move.agente):
        found.append(f"{move.agente} retires {move.nodo}, outside its stage {AGENT_STAGE.get(move.agente)}")
    return found


def split_move_problems(nodes: Mapping[str, Node], move: Split) -> list[str]:
    leaf = nodes.get(move.hoja)
    if leaf is None or leaf.hoja is None:
        return [f"{move.agente} splits {move.hoja}, which is no leaf of the tree"]
    found: list[str] = []
    if leaf.hoja.agente != move.agente:
        found.append(f"{move.agente} splits {move.hoja}, a leaf of {leaf.hoja.agente}")
    found += fresh_problems(nodes, [move.nodo, move.nueva])
    if move.nueva.sigue != leaf.sigue:
        found.append(f"{move.nueva.id} continues to {move.nueva.sigue}, where {move.hoja} continues to {leaf.sigue}")
    return found


def exclusion_metric_problems(move: Split) -> list[str]:
    rows = move.nueva.hoja.excluye if move.nueva.hoja is not None else ()
    if not rows:
        return []
    predicate = move.nodo.predicado
    if predicate is None or (predicate.lee, predicate.op) != ("estado.detection.metric", "=") or not isinstance(predicate.valor, str):
        return [f"{move.nueva.id} excludes rows without testing estado.detection.metric = one metric"]
    return [f"{move.nueva.id} excludes {row}, a row of another metric than {predicate.valor}" for row in rows if row.rsplit("-", 1)[0] != f"act-{predicate.valor}"]


def branch_problems(nodes: Mapping[str, Node], move: Branch, stage: str, grounds: Grounds) -> list[str]:
    family = nodes.get(move.familia)
    predicate = family.predicado if family is not None else None
    if (
        predicate is None
        or level(move.familia) != 2
        or move.familia.split(".")[0] != stage
        or (predicate.lee, predicate.op) != ("estado.candidato.metrica", "en")
    ):
        return [f"{move.agente} adds under {move.familia}, which is no L2 family of {stage}"]
    if move.metrica in predicate.valor:
        return [f"{move.familia} already admits {move.metrica}"]
    if not move.nodos:
        return [f"the branch of {move.metrica} holds no node"]
    _, exit_ = chain_end(nodes, move.familia)
    new = {node.id for node in move.nodos}
    leaves = {node_id for node_id, node in nodes.items() if node.hoja is not None and node.hoja.agente == move.agente}
    routes = {(node.hoja.decision, node.sigue) for node in grounds.base.nodos if node.hoja is not None and node.hoja.agente == move.agente}
    found = fresh_problems(nodes, move.nodos)
    entry = move.nodos[0]
    if entry.id != f"{move.familia}.{move.metrica}" or entry.predicado is None or (entry.predicado.lee, entry.predicado.op, entry.predicado.valor) != ("estado.candidato.metrica", "=", move.metrica):
        found.append(f"the branch of {move.metrica} starts at {move.familia}.{move.metrica}, which tests estado.candidato.metrica = {move.metrica}")
    for node in move.nodos:
        if node.hoja is not None:
            if node.hoja.agente != move.agente or (node.hoja.decision, node.sigue) not in routes:
                found.append(f"{node.id} is no leaf of {move.agente} taking a decision and a route its base leaves take")
            continue
        if not node.id.startswith(move.familia + "."):
            found.append(f"{node.id} is outside the family {move.familia}")
        found += [
            f"{node.id} exits to {target}, which is no node of the move, leaf of {move.agente} or {exit_}"
            for _, target in branches(node)
            if target not in new and target not in leaves and target != exit_
        ]
        umbral = node.predicado.umbral if node.predicado is not None else None
        if umbral in grounds.metrics.thresholds and not grounds.metrics.threshold_sources.get(umbral, "").strip():
            found.append(f"{node.id} names umbral {umbral}, whose fuente_umbral quotes no document")
    return found


def move_problems(parent: Tree, move, grounds: Grounds) -> list[str]:
    nodes = index(parent)
    if isinstance(move, Retire):
        return retire_problems(nodes, move)
    if move.agente not in AGENT_STAGE or move.agente == "chat":
        return [f"{move.agente} expands nothing; only vigia, analista, estratega and ejecutor do"]
    stage = AGENT_STAGE[move.agente]
    if isinstance(move, Split):
        return split_move_problems(nodes, move)
    return branch_problems(nodes, move, stage, grounds)


def depth(nodes: Mapping[str, Node]) -> int:
    memo: dict[str, int] = {}

    def longest(node_id: str, trail: frozenset[str]) -> int:
        node = nodes.get(node_id)
        if node is None or node_id in trail:
            return 0
        if node_id not in memo:
            below = [longest(target, trail | {node_id}) for branch, target in branches(node) if not capped_return(node, branch, target, nodes)]
            memo[node_id] = 1 + max(below, default=0)
        return memo[node_id]

    return longest(ROOT, frozenset())


def cap_problems(tree: Tree, caps: Caps) -> list[str]:
    found: list[str] = []
    longest = depth(index(tree))
    if longest > caps.depth:
        found.append(f"the longest path holds {longest} nodes, past the cap of {caps.depth}")
    counts = Counter(node.id.split(".")[0] for node in tree.nodos if node.hoja is None)
    found += [f"stage {stage} holds {count} nodes, past the cap of {caps.nodes_per_stage}" for stage, count in sorted(counts.items()) if count > caps.nodes_per_stage]
    return found


def expansion_problems(parent: Tree, move, grounds: Grounds, caps: Caps) -> list[str]:
    found = move_problems(parent, move, grounds)
    if found:
        return found
    child = apply_move(parent, move)
    held = [*problems(child.model_dump(), grounds), *(exclusion_metric_problems(move) if isinstance(move, Split) else [])]
    return held if isinstance(move, Retire) else [*held, *cap_problems(child, caps)]


def layer_hash(tree: Tree) -> str:
    nodes = index(tree)
    layer = [
        [law.model_dump() for law in tree.leyes],
        sorted((resolved(node, nodes).model_dump() for node in tree.nodos if node.hoja is None and level(node.id) == 1), key=lambda node: node["id"]),
    ]
    return hashlib.sha256(json.dumps(layer, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def replay(base: Tree, moves: Sequence, grounds: Grounds, caps: Caps) -> tuple[Tree, list[tuple[int, list[str]]]]:
    tree, dropped = base, []
    for position, move in enumerate(moves):
        found = expansion_problems(tree, move, grounds, caps)
        if found:
            dropped.append((position, found))
        else:
            tree = apply_move(tree, move)
    return tree, dropped
