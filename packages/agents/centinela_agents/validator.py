import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pydantic import ValidationError

from .catalog import Catalog, thresholds_named
from .metrics import Metrics, load_metrics, threshold_shape_problem
from .predicate import KPI_PATH, STATE_PATH
from .graph import BOUND_NODES
from .severity import severity_problems
from .schema import AGENT_DECISIONS, AGENT_STAGE, CHAT_ROOT, ENDS, GATE, ROOT, STAGES, VIGENTE, Node, Tree, branches, index, level, live, reachable, resolve, stage_of
from .skills import action_rows
from .state import STATE_FIELDS
from .yaml_loader import load_yaml

CAPPED_RETURNS = (
    ("proponer.retorno_disponible", "explicar", "estado.analyst_returns"),
    ("aprobar.recarga_disponible", "proponer", "estado.proposal_returns"),
)
BOOLEAN_SPELLINGS = frozenset({"y", "yes", "n", "no", "true", "false", "on", "off"})


@dataclass(frozen=True)
class Grounds:
    base: Tree
    registry: frozenset[str]
    metrics: Metrics
    catalog: Catalog
    skills: Path


class InvalidTree(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


def load_registry(path: Path) -> frozenset[str]:
    return frozenset(entry["id"] for entry in load_yaml(path)["fundamentos"])


def schema_problems(error: ValidationError) -> list[str]:
    return [f"schema: {'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors()]


def problems(data: Mapping[str, Any], grounds: Grounds) -> list[str]:
    try:
        tree = Tree.model_validate(data)
    except ValidationError as error:
        return schema_problems(error)
    nodes = index(tree)
    return [
        *shape_problems(tree),
        *atomicity_problems(tree),
        *fundamento_problems(tree, grounds.registry),
        *reference_problems(tree, nodes),
        *split_problems(nodes),
        *approval_problems(nodes),
        *cycle_problems(nodes),
        *end_problems(nodes),
        *reach_problems(nodes),
        *chat_problems(nodes),
        *operand_problems(tree, grounds.catalog),
        *candidate_problems(nodes, grounds.catalog),
        *threshold_problems(tree, grounds),
        *leaf_problems(tree, grounds.skills),
        *exclusion_problems(tree, grounds),
        *coverage_problems(tree, grounds),
        *severity_problems(grounds.metrics, grounds.catalog),
        *base_problems(tree, grounds.base),
    ]


def checked_base(data: Mapping[str, Any], registry: frozenset[str], metrics: Metrics, catalog: Catalog, skills: Path) -> Tree:
    try:
        base = Tree.model_validate(data)
    except ValidationError as error:
        raise InvalidTree(schema_problems(error)) from error
    found = problems(data, Grounds(base, registry, metrics, catalog, skills))
    if found:
        raise InvalidTree(found)
    return base


def load_base(arbol: Path, metricas: Path, skills: Path, catalog: Catalog) -> Tree:
    return checked_base(
        load_yaml(arbol / "base.yaml"),
        load_registry(arbol / "fundamentos.yaml"),
        load_metrics(metricas),
        catalog,
        skills,
    )


def shape_problems(tree: Tree) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for node in tree.nodos:
        if node.id in seen:
            found.append(f"{node.id} is declared twice")
        seen.add(node.id)
        head = node.id.split(".")[0]
        if node.hoja is not None:
            if head != "hoja":
                found.append(f"{node.id} is a leaf, so its id starts with hoja")
            if node.fundamento is not None:
                found.append(f"{node.id} is a leaf, which inherits its parent's fundamento")
            if node.predicado is not None or node.si is not None or node.no is not None:
                found.append(f"{node.id} is a leaf and holds a predicate or a branch")
            if node.sigue is None:
                found.append(f"{node.id} lacks its sigue")
            continue
        if head not in STAGES:
            found.append(f"{node.id} names no stage")
        if node.sigue is not None:
            found.append(f"{node.id} is a node, and only a leaf has sigue")
        for key in ("predicado", "fundamento", "si", "no"):
            if getattr(node, key) is None:
                found.append(f"{node.id} lacks its {key}")
    return found


def atomicity_problems(tree: Tree) -> list[str]:
    found: list[str] = []
    for node in tree.nodos:
        predicate = node.predicado
        if predicate is None:
            continue
        kpi = KPI_PATH.match(predicate.lee) is not None
        if not kpi and STATE_PATH.match(predicate.lee) is None:
            found.append(f"{node.id} reads {predicate.lee}, which is not one operand")
            continue
        if predicate.op == "existe":
            if predicate.umbral is not None or predicate.valor is not None:
                found.append(f"{node.id} tests existe and compares a value too")
        elif predicate.umbral is not None and predicate.valor is not None:
            found.append(f"{node.id} compares with an umbral and a valor at once")
        elif predicate.umbral is None and predicate.valor is None:
            found.append(f"{node.id} compares {predicate.lee} with nothing")
        elif predicate.op == "en" and not (isinstance(predicate.valor, list) and predicate.valor):
            found.append(f"{node.id} tests en without a closed list")
        elif predicate.op != "en" and isinstance(predicate.valor, list):
            found.append(f"{node.id} compares with a list without en")
        if kpi and predicate.valor is not None:
            found.append(f"{node.id} compares a KPI with a valor; a KPI takes an umbral")
        if not kpi and predicate.umbral is not None:
            found.append(f"{node.id} bounds a state field with an umbral; a state field takes a valor")
        values = predicate.valor if isinstance(predicate.valor, list) else [predicate.valor]
        found += [
            f"{node.id} writes a boolean as {value}; write true or false"
            for value in values
            if isinstance(value, str) and value.lower() in BOOLEAN_SPELLINGS
        ]
    return found


def fundamento_problems(tree: Tree, registry: frozenset[str]) -> list[str]:
    found = [
        f"{node.id} rests on {node.fundamento}, absent from fundamentos.yaml"
        for node in tree.nodos
        if node.fundamento is not None and node.fundamento not in registry
    ]
    found += [
        f"law {law.id} rests on {law.fundamento}, absent from fundamentos.yaml"
        for law in tree.leyes
        if law.fundamento not in registry
    ]
    return found


def reference_problems(tree: Tree, nodes: Mapping[str, Node]) -> list[str]:
    return [
        f"{node.id} {name} names {target}, which is no node, leaf or end"
        for node in tree.nodos
        for name, target in branches(node)
        if target not in nodes and target not in ENDS
    ]


def split_problems(nodes: Mapping[str, Node]) -> list[str]:
    found: list[str] = []
    for node_id, node in sorted(nodes.items()):
        if node.divide is None:
            continue
        leaf = nodes.get(node.divide)
        if leaf is None or leaf.hoja is None:
            found.append(f"{node_id} divides {node.divide}, which is no leaf")
            continue
        stage = AGENT_STAGE.get(leaf.hoja.agente)
        if node.hoja is not None or level(node_id) == 1 or node_id.split(".")[0] != stage:
            found.append(f"{node_id} divides a leaf of {leaf.hoja.agente}, and only an L2 or L3 node of {stage} does")
        if node.no is None or resolve(node.no, nodes) != node.divide:
            found.append(f"{node_id} does not lead back to {node.divide} on no")
        taken = nodes.get(resolve(node.si, nodes)) if node.si is not None else None
        kind = (leaf.hoja.agente, leaf.hoja.decision)
        if taken is None or taken.hoja is None or taken.id == node.divide or (taken.hoja.agente, taken.hoja.decision) != kind:
            found.append(f"{node_id} takes no new leaf of {leaf.hoja.agente}/{leaf.hoja.decision} on si")
    return found


def approval_problems(nodes: Mapping[str, Node]) -> list[str]:
    found: list[str] = []
    executors = sorted(node_id for node_id, node in nodes.items() if node.hoja is not None and node.hoja.agente == "ejecutor")
    for required in (GATE, VIGENTE):
        if required not in nodes:
            found.append(f"the tree lacks {required}")
        bypass = reachable(nodes, [ROOT], without=frozenset({required}))
        found += [f"{leaf} is reached without passing {required}" for leaf in executors if leaf in bypass]
    return found


def capped_return(node: Node, branch: str, target: str, nodes: Mapping[str, Node]) -> bool:
    predicate = node.predicado
    if branch != "si" or predicate is None:
        return False
    goal = stage_of(target, nodes)
    return any(
        node.id == bound and goal == end and predicate.lee == counter and predicate.op == "=" and predicate.valor == 0
        for bound, end, counter in CAPPED_RETURNS
    )


def cycle_problems(nodes: Mapping[str, Node]) -> list[str]:
    edges = {
        node_id: [target for branch, target in branches(node) if target in nodes and not capped_return(node, branch, target, nodes)]
        for node_id, node in nodes.items()
    }
    found: list[str] = []
    marks: dict[str, str] = {}

    def visit(node_id: str, trail: list[str]) -> None:
        marks[node_id] = "open"
        for target in edges[node_id]:
            if marks.get(target) == "open":
                found.append("cycle " + " -> ".join([*trail[trail.index(target):], target]))
            elif target not in marks:
                visit(target, [*trail, target])
        marks[node_id] = "done"

    for node_id in sorted(nodes):
        if node_id not in marks:
            visit(node_id, [node_id])
    return found


def end_problems(nodes: Mapping[str, Node]) -> list[str]:
    if ROOT not in nodes:
        return [f"the tree lacks its root {ROOT}"]
    finishing: set[str] = set()
    grown = True
    while grown:
        grown = False
        for node_id, node in nodes.items():
            if node_id not in finishing and any(target in ENDS or target in finishing for _, target in branches(node)):
                finishing.add(node_id)
                grown = True
    return [f"{node_id} reaches no fin" for node_id in sorted(reachable(nodes, [ROOT, CHAT_ROOT])) if node_id in nodes and node_id not in finishing]


def reach_problems(nodes: Mapping[str, Node]) -> list[str]:
    if ROOT not in nodes:
        return []
    reached = reachable(nodes, [ROOT, CHAT_ROOT])
    return [f"{node_id} is unreachable from {ROOT} and {CHAT_ROOT}" for node_id in sorted(nodes) if node_id not in reached]


def chat_problems(nodes: Mapping[str, Node]) -> list[str]:
    root = nodes.get(CHAT_ROOT)
    if root is None:
        return [f"the tree lacks its root {CHAT_ROOT}"]
    found: list[str] = []
    if root.predicado is None or root.predicado.lee != "estado.chat.sospechosa":
        read = root.predicado.lee if root.predicado is not None else "nothing"
        found.append(f"{CHAT_ROOT} reads {read}; the chat's first node reads estado.chat.sospechosa")
    alert, chat = reachable(nodes, [ROOT]), reachable(nodes, [CHAT_ROOT])
    for node_id in sorted(chat):
        node = nodes.get(node_id)
        if node_id == GATE:
            found.append(f"{CHAT_ROOT} reaches {GATE}")
        elif node_id in BOUND_NODES:
            found.append(f"{CHAT_ROOT} reaches {node_id}, an orchestrator write")
        elif node is not None and node.hoja is not None and node.hoja.agente != "chat":
            found.append(f"{CHAT_ROOT} reaches the leaf {node_id} of {node.hoja.agente}")
    for node_id in sorted(alert):
        node = nodes.get(node_id)
        if node is not None and node.hoja is not None and node.hoja.agente == "chat":
            found.append(f"{ROOT} reaches the leaf {node_id} of chat")
    found += [f"{ROOT} and {CHAT_ROOT} both reach {node_id}" for node_id in sorted(alert & chat)]
    return found


def operand_problems(tree: Tree, catalog: Catalog) -> list[str]:
    found: list[str] = []
    for node in tree.nodos:
        predicate = node.predicado
        if predicate is None:
            continue
        match = KPI_PATH.match(predicate.lee)
        if match is not None:
            metric, column = match.groups()
            kpi = catalog.kpis.get(metric)
            if kpi is None or column not in kpi.columns:
                found.append(f"{node.id} reads {predicate.lee}, which the kernel does not build")
            if node.id.split(".")[0] != "detectar":
                found.append(f"{node.id} reads a KPI outside detectar; an alert reads its measure through {VIGENTE}")
        elif STATE_PATH.match(predicate.lee) and predicate.lee not in STATE_FIELDS:
            found.append(f"{node.id} reads {predicate.lee}, which the alert's state does not declare")
    return found


def candidate_problems(nodes: Mapping[str, Node], catalog: Catalog) -> list[str]:
    found: set[str] = set()
    seen: set[tuple[str, frozenset[str]]] = set()
    stack = [(ROOT, frozenset(catalog.kpis))]
    while stack:
        node_id, candidates = stack.pop()
        node = nodes.get(node_id)
        if not candidates or node is None or node.predicado is None or (node_id, candidates) in seen:
            continue
        seen.add((node_id, candidates))
        predicate = node.predicado
        admitted, refused = candidates, candidates
        match = KPI_PATH.match(predicate.lee)
        if match is not None and candidates != {match.group(1)}:
            found.add(f"{node_id} reads {match.group(1)} where the candidate may be {', '.join(sorted(candidates - {match.group(1)}))}")
        if predicate.lee == "estado.candidato.metrica" and predicate.op in ("=", "en"):
            named = frozenset(predicate.valor if predicate.op == "en" else [predicate.valor])
            admitted, refused = candidates & named, candidates - named
        stack += [(node.si, admitted), (node.no, refused)]
    return sorted(found)


def threshold_problems(tree: Tree, grounds: Grounds) -> list[str]:
    found: list[str] = []
    for node in tree.nodos:
        predicate = node.predicado
        if predicate is None or predicate.umbral is None:
            continue
        match = KPI_PATH.match(predicate.lee)
        if match is None:
            continue
        metric, column = match.groups()
        named = thresholds_named(predicate.umbral, grounds.metrics, grounds.catalog)
        if named is None:
            found.append(f"{node.id} names umbral {predicate.umbral}, absent from metricas.yaml and from the approved KPIs")
            continue
        if column not in named:
            found.append(f"{node.id} names umbral {predicate.umbral}, which sets no threshold for {column}")
            continue
        spec = named[column]
        shape = threshold_shape_problem(spec)
        if shape is not None:
            found.append(f"{node.id}: the threshold of {predicate.umbral} for {column} {shape}")
            continue
        referenced = (spec.get("columna") or spec.get("por")) if isinstance(spec, dict) else None
        kpi = grounds.catalog.kpis.get(metric)
        if referenced is not None and (kpi is None or referenced not in kpi.columns):
            found.append(f"{node.id}: the threshold of {predicate.umbral} for {column} reads {referenced}, which kpi.{metric} does not build")
    return found


def leaf_problems(tree: Tree, skills: Path) -> list[str]:
    found: list[str] = []
    root = skills.resolve()
    for node in tree.nodos:
        leaf = node.hoja
        if leaf is None:
            continue
        allowed = AGENT_DECISIONS.get(leaf.agente)
        if allowed is None:
            found.append(f"{node.id} names agent {leaf.agente}, outside vigia, analista, estratega, ejecutor and chat")
        elif leaf.decision not in allowed:
            found.append(f"{node.id} takes {leaf.decision}, outside the decisions of {leaf.agente}")
        path = (skills / leaf.skill).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            found.append(f"{node.id} loads {leaf.skill}, which is no file under packages/agents/skills")
    return found


def exclusion_problems(tree: Tree, grounds: Grounds) -> list[str]:
    known = {f"act-{metric}-{row.ref}" for metric in grounds.metrics.names for row in action_rows(metric)}
    found: list[str] = []
    for node in tree.nodos:
        leaf = node.hoja
        if leaf is None or not leaf.excluye:
            continue
        if (leaf.agente, leaf.decision) != ("estratega", "proponer"):
            found.append(f"{node.id} excludes rows, and only a proponer leaf of estratega does")
        found += [f"{node.id} excludes {action}, which no row of acciones.md names" for action in leaf.excluye if action not in known]
    return found


def coverage_problems(tree: Tree, grounds: Grounds) -> list[str]:
    alive = live(index(tree), [ROOT])
    read = {
        KPI_PATH.match(node.predicado.lee).group(1)
        for node in tree.nodos
        if node.predicado is not None
        and KPI_PATH.match(node.predicado.lee)
        and node.id.split(".")[0] == "detectar"
        and level(node.id) == 3
        and node.id in alive
        and node.retirado is None
    }
    listed = (grounds.skills / "estratega" / "acciones.md").read_text(encoding="utf-8").split("\n## ")[0]
    found: list[str] = []
    for metric in grounds.metrics.names:
        if metric not in read:
            found.append(f"metric {metric} has no L3 branch in detectar")
        if not (grounds.skills / "analista" / f"{metric}.md").is_file():
            found.append(f"metric {metric} has no skills/analista/{metric}.md")
        if re.search(rf"^\| `{re.escape(metric)}` \|", listed, re.MULTILINE) is None:
            found.append(f"metric {metric} has no row in skills/estratega/acciones.md")
    return found


def resolved(node: Node, nodes: Mapping[str, Node]) -> Node:
    return node.model_copy(update={key: resolve(getattr(node, key), nodes) for key in ("si", "no", "sigue") if getattr(node, key) is not None})


def base_problems(tree: Tree, base: Tree) -> list[str]:
    nodes = index(tree)
    found = [] if tree.leyes == base.leyes else ["L0 differs from the base"]
    mine = {node.id: resolved(node, nodes) for node in tree.nodos if node.hoja is None and level(node.id) == 1}
    theirs = {node.id: node for node in base.nodos if node.hoja is None and level(node.id) == 1}
    found += [f"L1 node {node_id} differs from the base" for node_id in sorted(theirs) if mine.get(node_id) != theirs[node_id]]
    found += [f"L1 node {node_id} is absent from the base" for node_id in sorted(set(mine) - set(theirs))]
    leaves = {node.id: leaf_route(resolved(node, nodes)) for node in tree.nodos if node.hoja is not None}
    found += [
        f"leaf {node.id} differs from the base"
        for node in sorted(base.nodos, key=lambda node: node.id)
        if node.hoja is not None and leaves.get(node.id) != leaf_route(node)
    ]
    return found


def leaf_route(node: Node) -> tuple[str, str, tuple[str, ...], str | None]:
    return node.hoja.agente, node.hoja.decision, node.hoja.excluye, node.sigue
