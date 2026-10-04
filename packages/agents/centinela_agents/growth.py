import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .expansion import Growth, Split, apply_move, expansion_problems
from .schema import Node, Predicate, Tree, index, level, resolve
from .validator import Grounds

SPLIT_GROUND = "iso31000.6.5.2"
COUNTED_TARGETS = ("propuesta",)
PROPOSER = "hoja.estratega.proponer"
ROW = re.compile(r"^act-([a-z0-9_]+)-r\d+$")


@dataclass(frozen=True)
class Rejection:
    alert_id: str
    metric: str
    target: str
    actions: tuple[str, ...]


@dataclass(frozen=True)
class Grown:
    agent: str
    move: Split
    evidence: tuple[str, ...]
    tree: Tree | None
    problems: tuple[str, ...] = ()


def rejected_rows(rejections: Iterable[Rejection], consumed: set[str]) -> dict[str, dict[str, set[str]]]:
    by_metric: dict[str, dict[str, set[str]]] = {}
    for rejection in rejections:
        if rejection.target not in COUNTED_TARGETS or rejection.alert_id in consumed:
            continue
        for action in rejection.actions:
            match = ROW.match(action)
            if match is not None and match.group(1) == rejection.metric:
                by_metric.setdefault(rejection.metric, {}).setdefault(action, set()).add(rejection.alert_id)
    return by_metric


def family_of(metric: str, nodes: Mapping[str, Node]) -> str | None:
    for node in nodes.values():
        predicate = node.predicado
        if (
            node.id.startswith("detectar.")
            and level(node.id) == 2
            and predicate is not None
            and (predicate.lee, predicate.op) == ("estado.candidato.metrica", "en")
            and metric in predicate.valor
        ):
            return node.id.split(".")[1]
    return None


def metric_leaf(nodes: Mapping[str, Node], metric: str, leaf: str = PROPOSER) -> str:
    for node in sorted(nodes.values(), key=lambda node: node.id):
        predicate = node.predicado
        if (
            node.divide == leaf
            and node.retirado is None
            and predicate is not None
            and (predicate.lee, predicate.op, predicate.valor) == ("estado.detection.metric", "=", metric)
        ):
            return metric_leaf(nodes, metric, resolve(node.si, nodes))
    return leaf


def drafted_split(tree: Tree, metric: str, actions: Sequence[str]) -> Split | None:
    nodes = index(tree)
    family = family_of(metric, nodes)
    target = metric_leaf(nodes, metric)
    leaf = nodes[target]
    excluded = tuple(sorted({*leaf.hoja.excluye, *actions}))
    if family is None or set(excluded) == set(leaf.hoja.excluye):
        return None
    prefix = f"proponer.{family}.{metric}.division_"
    number = 1 + sum(node_id.startswith(prefix) for node_id in nodes)
    new_leaf = f"hoja.estratega.proponer.{metric}.{number}"
    return Split(
        agente="estratega",
        hoja=target,
        nodo=Node(
            id=f"{prefix}{number}",
            fundamento=SPLIT_GROUND,
            predicado=Predicate(lee="estado.detection.metric", op="=", valor=metric),
            si=new_leaf,
            no=target,
            divide=target,
        ),
        nueva=Node(id=new_leaf, hoja=leaf.hoja.model_copy(update={"excluye": excluded}), sigue=leaf.sigue),
    )


def grow(tree: Tree, grounds: Grounds, growth: Growth, rejections: Iterable[Rejection], consumed: Iterable[str]) -> list[Grown]:
    needed = growth.repetitions.get("estratega")
    if needed is None:
        return []
    grown: list[Grown] = []
    for metric, rows in sorted(rejected_rows(rejections, set(consumed)).items()):
        reached = sorted(action for action, alerts in rows.items() if len(alerts) >= needed)
        move = drafted_split(tree, metric, reached) if reached else None
        if move is None:
            continue
        nodes = index(tree)
        added = set(reached) - set(nodes[metric_leaf(nodes, metric)].hoja.excluye)
        evidence = tuple(sorted(set().union(*(rows[action] for action in added))))
        found = expansion_problems(tree, move, grounds, growth.caps)
        if found:
            grown.append(Grown("estratega", move, evidence, None, tuple(found)))
            continue
        tree = apply_move(tree, move)
        grown.append(Grown("estratega", move, evidence, tree))
    return grown
