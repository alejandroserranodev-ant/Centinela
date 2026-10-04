# How the decision tree grows: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the tree grow by self-expansion held by criteria checked in code: the three moves as
data, a validator that refuses every move that breaks a fixed criterion, `Estratega`'s split of its
leaf after repeated rejections of one action row, the tree's versions stored and retirable in
`apps/api`, and the version each alert walked.

**Architecture:** `packages/agents` gains the moves (`centinela_agents/expansion.py`: `Split`,
`Branch`, `Retire`, `apply_move`, `expansion_problems`, the caps and the replay) and the drafter
(`centinela_agents/growth.py:grow`), both pure: they return moves and the trees they yield and
never write. The schema gains `divide` and `retirado` on a node and `excluye` on a leaf; the
interpreter walks a retired node's `no`, hands a split leaf its exclusions, and writes the tree's
version into each alert's state. `apps/api` stores every version as a move in
`api.arbol_versiones`, replays them over the base when the base changes, drafts at the start of
each day run from the rejections it now stores in `api.rechazos`, and serves the list and the
retirement of expansions, which `Configuración` shows.

**Tech Stack:** Python 3.12, Pydantic 2, LangGraph ≥ 1.0, pytest, uv in `packages/agents`; FastAPI
and psycopg in `apps/api`; React 18 with Arena React in `apps/web`.

**Spec:** [`2026-10-03-tree-expansion.md`](./2026-10-03-tree-expansion.md). Its section
"Amendments the code forced" wins over any decision it amends; read it first.

## Decisions pending a person

The plan writes the value in the right column so every task runs, and each value is a person's to
confirm or replace before Task 3 (D1, D2), Task 4 (D4, D5, D6) or Task 7 (D3) runs. Changing one
changes only the line the column names and the test that pins it.

| # | Decision | The plan writes | Where |
|---|---|---|---|
| D1 | how many rejections of one action row, in alerts of one metric, draft `Estratega`'s split | `3` | `packages/agents/arbol/crecimiento.yaml`, `repeticiones.estratega.valor` |
| D2 | the caps on a version: the nodes of its longest path and the nodes of one stage. Re-derive the base's own figures with the command under the table | `40` and `64` | `crecimiento.yaml`, `topes` |
| D3 | which roles retire an expansion | `analista` and `gerente`, the roles that configure | `apps/api/src/centinela_api/permisos.py:puede_retirar(persona)` |
| D4 | the registry entry `Estratega`'s split node rests on | `iso31000.6.5.2`, "stage proponer: selection of treatment options" | `packages/agents/centinela_agents/growth.py:SPLIT_GROUND` |
| D5 | which classifier targets count as a rejection of the proposal | `propuesta` only, as the spec says; `ambos` also sends the reason to `Estratega` | `growth.py:COUNTED_TARGETS` |
| D6 | whether a split may exclude every row of a metric, leaving the alert a manual review | allowed | `growth.py:drafted_split` |

```bash
cd packages/agents && uv run python -c "
from collections import Counter; from functools import cache; from pathlib import Path
from centinela_agents.schema import ROOT, Tree, branches, index
from centinela_agents.validator import capped_return
from centinela_agents.yaml_loader import load_yaml
t = Tree.model_validate(load_yaml(Path('arbol/base.yaml'))); n = index(t)
@cache
def d(x): return 0 if x not in n else 1 + max([d(g) for b, g in branches(n[x]) if not capped_return(n[x], b, g, n)] or [0])
print('longest path', d(ROOT)); print(Counter(x.id.split('.')[0] for x in t.nodos if x.hoja is None))"
```

## Global Constraints

- Hand-written source carries **no comments and no docstrings**, except one header of at most ten
  lines on a test or a SQL file (`check:docs`).
- Documentation is English, present tense; domain words stay Spanish in backticks. Text a person
  reads on screen or in the `bitácora` is Spanish.
- Prose cites code as `path/to/file.py:member(parameters)` with the parameters the member declares,
  never by line number (`check:citations`).
- A commit message is one sentence about what the tree now does and why. A message with a backtick
  goes through `git commit -q -F - <<'MSG'`. End every message with
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- No document carries a literal count of anything that grows.
- **The working tree may hold another session's uncommitted changes**, since another session
  committed on this branch while the plan was written. Stage only the paths a task names, with `git add <paths>`,
  never `git add -A` or `git commit -a`.
- An expansion is one of `dividir_hoja`, `agregar_rama` and `retirar`, and nothing else; a move
  never edits or deletes a node in place, except the `en` list of the family an `agregar_rama`
  extends and the `retirado` a `retirar` sets.
- L0 and L1 never change by a move: `centinela_agents/validator.py:base_problems(tree, base)` reads
  every reference to a split node as a reference to its leaf, and refuses anything else.
- Every path to an `Ejecutor` leaf passes `aprobar.decision` and `ejecutar.vigente`, on every version.
- No module of `packages/agents` opens a database connection or persists a version; `apps/api` is
  the only writer of `api.arbol_versiones` and `api.rechazos`.
- A refused draft is dropped and logged once; it is never retried with the criterion named.
- Run Python in `packages/agents` with `uv run pytest`; in `apps/api` with `pytest` from its
  `.venv`; in `apps/web` with `npm run typecheck` and `npm test`.
- The completion gate is `npm run check` at the root.

## Review Focus

1. **A base merged by pull request after a client has expansions**: the next day run replays every
   move over the new base, keeps the ones that still pass, drops and logs the others, and the day
   runs on the result instead of failing. Task 6 pins it.
2. **A split leaf that excludes every row of its metric**: `Estratega` calls no model and the alert
   reaches one manual-review `task`, never a second paid run of `Analista`. Task 2 pins it.
3. **A paused alert when a newer version is in use**: its approval resumes on the graph of the
   version it started on, and a new alert walks the newer one. Task 5 pins it.
4. **A second excluded row for the same metric**: it nests on the first split's leaf, the leaf
   excludes both rows, and retiring the second restores the first's exclusion alone. Task 4 pins it.
5. **A rejection the classifier never targeted** (recorded after a restart, with no paused graph)
   **or a rejected manual review**: neither counts as evidence for a row. Tasks 4 and 6 pin it.

---

## File map

| File | Change |
|---|---|
| `packages/agents/centinela_agents/schema.py` | `Leaf.excluye`, `Node.divide`, `Node.retirado`, `resolve`, `live_branches`, `live`; `expandir` leaves `AGENT_DECISIONS` |
| `packages/agents/centinela_agents/state.py` | `estado.detection.metric` in `STATE_FIELDS`; `AlertState.arbol_version` |
| `packages/agents/centinela_agents/validator.py` | `split_problems`, `exclusion_problems`, `resolved`, live coverage, `base_problems` through splits, `load_grounds` |
| `packages/agents/centinela_agents/walk.py` | a retired node takes `no`; `Context.version` |
| `packages/agents/centinela_agents/graph.py` | a retired node takes `no`; a leaf with `excluye` hands it; `arbol_version` in the initial state |
| `packages/agents/centinela_agents/agents/estratega.py` | drops the excluded rows; no model call when none is left |
| `packages/agents/centinela_agents/expansion.py` | new: the moves, `apply_move`, the criteria, the caps, `layer_hash`, `replay`, `load_growth` |
| `packages/agents/centinela_agents/growth.py` | new: `Rejection`, `Grown`, `metric_leaf`, `drafted_split`, `grow` |
| `packages/agents/centinela_agents/day.py` | `run_day` writes the version into each alert |
| `packages/agents/centinela_agents/orchestrator.py` | `use_tree`, `graph_of`; `run_day` walks the tree in use |
| `packages/agents/arbol/crecimiento.yaml` | new: the repetitions and the caps |
| `packages/agents/tests/support.py` | `split_data`, `split_tree` |
| `packages/agents/tests/test_expansion.py`, `tests/test_growth.py` | new |
| `packages/agents/tests/test_validator.py`, `test_schema.py`, `test_orq.py`, `test_agents.py`, `test_day.py`, `test_orchestrator.py` | updated |
| `apps/api/sql/01_esquema.sql` | `api.arbol_versiones`, `api.rechazos`, `api.alertas.arbol_version`, the `bitácora` type `arbol` |
| `apps/api/src/centinela_api/arboles.py`, `rechazos.py`, `routers/arbol.py` | new |
| `apps/api/src/centinela_api/agentes.py`, `alertas.py`, `modelos.py`, `permisos.py`, `main.py`, `routers/simulacion.py`, `routers/alertas.py` | updated |
| `apps/api/tests/corridas.py`, `test_avanzar.py`, `test_ciclo_orquestado.py` | updated; `test_arboles.py`, `test_arbol.py` new |
| `apps/web/src/api/openapi.json`, `src/api/schema.generated.ts` | regenerated |
| `apps/web/src/api/types.ts`, `http-client.ts`, `client.ts`, `src/logEvent.ts`, `src/screens/Bitacora.tsx`, `src/screens/Settings.tsx` | updated; `src/screens/Expansions.tsx` new |
| pages | `packages/agents/AGENTS.md`, `packages/agents/arbol/AGENTS.md`, `packages/agents/skills/AGENTS.md`, `apps/api/AGENTS.md`, `apps/web/AGENTS.md`, `evals/AGENTS.md`, `docs/guide/chapters/decision-tree.md`, `scripts/check/check-routes.ts` budgets |

---

### Task 1: The schema holds a split, an exclusion and a retirement, and the validator checks them

**Files:**
- Modify: `packages/agents/centinela_agents/schema.py`
- Modify: `packages/agents/centinela_agents/state.py:STATE_FIELDS`
- Modify: `packages/agents/centinela_agents/validator.py`
- Modify: `packages/agents/tests/support.py`
- Modify: `packages/agents/tests/test_validator.py`, `packages/agents/tests/test_schema.py`

**Interfaces:**
- Produces: `Leaf.excluye: tuple[str, ...] = ()`; `Node.divide: str | None = None`;
  `Node.retirado: str | None = None`; `schema.resolve(target: str, nodes: Mapping[str, Node]) -> str`;
  `schema.live_branches(node: Node) -> list[tuple[str, str]]`;
  `schema.live(nodes: Mapping[str, Node], starts: Iterable[str]) -> set[str]`;
  `validator.resolved(node: Node, nodes: Mapping[str, Node]) -> Node`;
  `validator.split_problems(nodes) -> list[str]`; `validator.exclusion_problems(tree, grounds) -> list[str]`;
  `support.PROPOSER = "hoja.estratega.proponer"`;
  `support.split_data(data, metric="saldo_vencido", family="cartera", excluye=("act-saldo_vencido-r1",), number=1, leaf=PROPOSER) -> dict`;
  `support.split_tree(**options) -> Tree`.

- [ ] **Step 1: Write the failing tests**

In `packages/agents/tests/support.py`, add after `node_of`:

```python
PROPOSER = "hoja.estratega.proponer"


def split_data(data: dict, metric: str = "saldo_vencido", family: str = "cartera", excluye=("act-saldo_vencido-r1",), number: int = 1, leaf: str = PROPOSER) -> dict:
    node_id, new_leaf = f"proponer.{family}.{metric}.division_{number}", f"hoja.estratega.proponer.{metric}.{number}"
    old = node_of(data, leaf)
    for node in data["nodos"]:
        for key in ("si", "no", "sigue"):
            if node.get(key) == leaf:
                node[key] = node_id
    data["nodos"] += [
        {"id": node_id, "fundamento": "iso31000.6.5.2", "predicado": {"lee": "estado.detection.metric", "op": "=", "valor": metric}, "si": new_leaf, "no": leaf, "divide": leaf},
        {"id": new_leaf, "hoja": {**old["hoja"], "excluye": list(excluye)}, "sigue": old["sigue"]},
    ]
    return data


def split_tree(**options) -> Tree:
    return Tree.model_validate(split_data(base_data(), **options))
```

In `packages/agents/tests/test_validator.py`, change the `support` import to
`from support import ARBOL, METRICAS, SKILLS, KERNEL_CATALOG, base_data, grounds, node_of, split_data`,
add after `drop_node`:

```python
def split_with(node=None, leaf=None):
    def plant(data):
        split_data(data)
        node_of(data, "proponer.cartera.saldo_vencido.division_1").update(node or {})
        node_of(data, "hoja.estratega.proponer.saldo_vencido.1")["hoja"].update(leaf or {})
    return plant
```

append these rows to `PLANTED`, before its closing bracket:

```python
    ("split that does not lead back to its leaf", split_with(node={"no": "hoja.estratega.revision_manual"}), "proponer.cartera.saldo_vencido.division_1 does not lead back to hoja.estratega.proponer on no"),
    ("split of no leaf", split_with(node={"divide": "proponer.con_acciones"}), "divides proponer.con_acciones, which is no leaf"),
    ("split into another decision", split_with(leaf={"decision": "revision_manual", "skill": "estratega/acciones.md"}), "takes no new leaf of estratega/proponer on si"),
    ("exclusion on another decision", set_leaf("hoja.estratega.revision_manual", excluye=["act-saldo_vencido-r1"]), "hoja.estratega.revision_manual excludes rows, and only a proponer leaf of estratega does"),
    ("exclusion of an unknown row", split_with(leaf={"excluye": ["act-saldo_vencido-r99"]}), "excludes act-saldo_vencido-r99, which no row of acciones.md names"),
    ("base leaf with an exclusion", set_leaf("hoja.estratega.proponer", excluye=["act-saldo_vencido-r1"]), "leaf hoja.estratega.proponer differs from the base"),
    ("retired last branch of a metric", set_key("detectar.inventario.cobertura_dias.minima", "retirado", "No aplica"), "metric cobertura_dias has no L3 branch in detectar"),
    ("retired family", set_key("detectar.inventario", "retirado", "No aplica"), "metric cobertura_dias has no L3 branch in detectar"),
    ("retired L1 node", set_key("explicar.con_evidencia", "retirado", "No aplica"), "L1 node explicar.con_evidencia differs from the base"),
```

and add after `test_the_base_passes`:

```python
def test_a_split_of_a_base_leaf_passes():
    assert problems(split_data(base_data()), grounds()) == []


def test_a_split_nested_on_the_leaf_a_split_added_passes():
    data = split_data(base_data())
    split_data(data, excluye=("act-saldo_vencido-r1", "act-saldo_vencido-r2"), number=2, leaf="hoja.estratega.proponer.saldo_vencido.1")
    assert problems(data, grounds()) == []


def test_a_retired_branch_of_a_metric_with_another_live_branch_passes():
    data = base_data()
    node_of(data, "detectar.cartera.saldo_vencido.dias")["retirado"] = "No aplica"
    assert problems(data, grounds()) == []
```

In `packages/agents/tests/test_schema.py`, change the schema import to
`from centinela_agents.schema import AGENT_DECISIONS, Tree, branches, index, level, live, reachable, resolve, stage_of`
and append:

```python
CHAIN = {
    "version": 1,
    "nodos": [
        {"id": "proponer.cartera.a", "fundamento": "x", "predicado": {"lee": "estado.actions", "op": "existe"}, "si": "hoja.estratega.n", "no": "proponer.cartera.b", "divide": "hoja.estratega.proponer"},
        {"id": "proponer.cartera.b", "fundamento": "x", "predicado": {"lee": "estado.actions", "op": "existe"}, "si": "hoja.estratega.m", "no": "hoja.estratega.proponer", "divide": "hoja.estratega.proponer", "retirado": "No ayudó"},
    ],
}


def test_a_reference_to_a_split_resolves_to_the_leaf_it_divides():
    nodes = index(Tree.model_validate(CHAIN))
    assert resolve("proponer.cartera.a", nodes) == "hoja.estratega.proponer"
    assert resolve("hoja.estratega.n", nodes) == "hoja.estratega.n"


def test_a_retired_node_lives_on_its_no_branch_alone():
    nodes = index(Tree.model_validate(CHAIN))
    assert live(nodes, ["proponer.cartera.a"]) == {"proponer.cartera.a", "hoja.estratega.n", "proponer.cartera.b", "hoja.estratega.proponer"}


def test_no_agent_decides_to_expand_at_a_leaf():
    assert all("expandir" not in decisions for decisions in AGENT_DECISIONS.values())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/agents && uv run pytest tests/test_validator.py tests/test_schema.py -q`
Expected: FAIL: `ImportError: cannot import name 'live'` in `test_schema.py`, and
`test_a_split_of_a_base_leaf_passes` failing with a `schema: nodos.….divide: Extra inputs are not permitted` problem.

- [ ] **Step 3: Write the schema**

In `packages/agents/centinela_agents/schema.py`, replace `AGENT_DECISIONS` with:

```python
AGENT_DECISIONS = {
    "vigia": ("detectar", "titular", "proponer_kpi"),
    "analista": ("explicar",),
    "estratega": ("proponer", "revision_manual"),
    "ejecutor": ("ejecutar", "nota_manual"),
    "chat": ("clasificar", "responder"),
}
```

replace `Leaf` and `Node` with:

```python
class Leaf(Strict):
    agente: str
    decision: str
    skill: str
    excluye: tuple[str, ...] = ()


class Node(Strict):
    id: str
    fundamento: str | None = None
    predicado: Predicate | None = None
    si: str | None = None
    no: str | None = None
    hoja: Leaf | None = None
    sigue: str | None = None
    divide: str | None = None
    retirado: str | None = None
```

and add after `reachable`:

```python
def resolve(target: str, nodes: Mapping[str, Node]) -> str:
    seen: set[str] = set()
    while target in nodes and nodes[target].divide is not None and target not in seen:
        seen.add(target)
        target = nodes[target].divide
    return target


def live_branches(node: Node) -> list[tuple[str, str]]:
    if node.retirado is not None:
        return [("no", node.no)] if node.no else []
    return branches(node)


def live(nodes: Mapping[str, Node], starts: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    stack = list(starts)
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        node = nodes.get(current)
        if node is not None:
            stack.extend(target for _, target in live_branches(node))
    return seen
```

In `packages/agents/centinela_agents/state.py`, add `"estado.detection.metric",` to the set of
`STATE_FIELDS`, right after `"estado.candidato.descriptivo",`.

- [ ] **Step 4: Write the validator**

In `packages/agents/centinela_agents/validator.py`:

1. Replace the schema import with
   `from .schema import AGENT_DECISIONS, AGENT_STAGE, CHAT_ROOT, ENDS, GATE, ROOT, STAGES, VIGENTE, Node, Tree, branches, index, level, live, reachable, resolve, stage_of`
   and add `from .skills import action_rows` below it.
2. In `problems`, add `*split_problems(nodes),` right after `*reference_problems(tree, nodes),` and
   `*exclusion_problems(tree, grounds),` right after `*leaf_problems(tree, grounds.skills),`.
3. Add after `reference_problems`:

```python
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
```

4. Add after `leaf_problems`:

```python
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
```

5. In `coverage_problems`, compute `alive = live(index(tree), [ROOT])` first, and add
   `and node.id in alive and node.retirado is None` as the last two conditions of `read`.
6. Replace `base_problems` and `leaf_route` with:

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd packages/agents && uv run pytest -q`
Expected: PASS, every test of the package, the new rows of `PLANTED` among them.

- [ ] **Step 6: Commit**

```bash
git add packages/agents/centinela_agents/schema.py packages/agents/centinela_agents/state.py packages/agents/centinela_agents/validator.py packages/agents/tests/support.py packages/agents/tests/test_validator.py packages/agents/tests/test_schema.py
git commit -q -F - <<'MSG'
The tree's schema now holds a split, the rows a leaf excludes and a retirement, and the validator reads a split as its leaf against the base, refuses a split that loses its leaf, and counts only live branches as a metric's coverage, because a version must keep every path of the base.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 2: The interpreter walks a retirement and hands a split leaf its exclusions

**Files:**
- Modify: `packages/agents/centinela_agents/walk.py:walk_from(start, state, row, ctx)`
- Modify: `packages/agents/centinela_agents/graph.py:predicate_node(node, ctx)`, `graph.py:leaf_node(node, function, ctx, token_cap)`
- Modify: `packages/agents/centinela_agents/agents/estratega.py:propose_actions(provider, state, cause, sources)`
- Modify: `packages/agents/tests/test_orq.py`, `packages/agents/tests/test_agents.py`

**Interfaces:**
- Consumes: `Node.retirado`, `Leaf.excluye`, `support.split_data`, `support.split_tree` (Task 1).
- Produces: a leaf function receives `state["excluye"]`, a list of action ids, when its leaf
  excludes rows; `propose_actions` returns `{"actions": None, "insufficient_cause": None}` with no
  model call when every row of the metric is excluded.

- [ ] **Step 1: Write the failing tests**

In `packages/agents/tests/test_orq.py`, add `split_data, split_tree` to the `support` import, add
`MANUAL_TASK` if absent, and append:

```python
DIVISION = "proponer.cartera.saldo_vencido.division_1"


def test_orq_a_split_leaf_whose_predicate_is_false_produces_the_unsplit_output():
    plain = start_alert(compiled(Recorder()), saldo_detection(), alert_id="A1", day=DAY)
    tree = split_tree(metric="cobertura_dias", family="inventario", excluye=("act-cobertura_dias-r1",))
    split = start_alert(compiled(Recorder(), tree=tree), saldo_detection(), alert_id="A1", day=DAY)
    assert {key: value for key, value in split.items() if key != "camino"} == {key: value for key, value in plain.items() if key != "camino"}
    assert ["proponer.inventario.cobertura_dias.division_1", "no"] in split["camino"]
    assert [step for step in split["camino"] if step[0] != "proponer.inventario.cobertura_dias.division_1"] == plain["camino"]


def test_orq_a_split_leaf_hands_estratega_the_rows_it_excludes():
    recorder = Recorder()
    state = start_alert(compiled(recorder, tree=split_tree()), saldo_detection(), alert_id="A1", day=DAY)
    assert recorder.received[("estratega", "proponer")]["excluye"] == ["act-saldo_vencido-r1"]
    assert [DIVISION, "si"] in state["camino"] and state["status"] == "propuesta"


def test_orq_a_retired_split_walks_the_leaf_it_split():
    data = split_data(base_data())
    node_of(data, DIVISION)["retirado"] = "No ayudó"
    recorder = Recorder()
    state = start_alert(compiled(recorder, tree=Tree.model_validate(data)), saldo_detection(), alert_id="A1", day=DAY)
    assert [DIVISION, "no"] in state["camino"]
    assert "excluye" not in recorder.received[("estratega", "proponer")]


def test_orq_a_split_leaf_that_excludes_every_row_reaches_one_manual_review():
    recorder = Recorder()
    nothing = {("estratega", "proponer"): lambda state: {"actions": None, "insufficient_cause": None}}
    state = start_alert(compiled(recorder, tree=split_tree(), overrides=nothing), saldo_detection(), alert_id="A1", day=DAY)
    assert state["actions"] == [MANUAL_TASK]
    assert recorder.count("analista", "explicar") == 1


def test_orq_a_retired_detectar_node_takes_its_no_branch():
    data = base_data()
    node_of(data, "detectar.cartera.saldo_vencido.dias")["retirado"] = "No aplica"
    ctx = Context.of(Tree.model_validate(data), load_metrics(METRICAS), KERNEL_CATALOG, reader_from({DAY: {"saldo_vencido": [SALDO_ROW]}}))
    assert detect(ctx, DAY) == []
```

In `packages/agents/tests/test_agents.py`, append to `class TestEstrategA`:

```python
    def test_an_excluded_row_reaches_no_model_and_no_proposal(self):
        provider = MagicMock()
        provider.generate_structured.return_value = structured(
            {"actions": [{"row": "r1", "title": "Recordatorio", "description": "Enviar."}, {"row": "r5", "title": "Revisar el cupo", "description": "Revisar."}], "insufficient_cause": False}
        )
        state = {**STATE, "excluye": ["act-saldo_vencido-r1"]}

        result = propose_actions(provider, state, {"kind": "identified", "sentence": "Paga tarde"}, sources())

        prompt = provider.generate_structured.call_args.args[0].user_prompt
        assert "r1: [" not in prompt and "r2: [" in prompt
        assert [action["id"] for action in result["actions"]] == ["act-saldo_vencido-r5"]

    def test_every_row_excluded_proposes_nothing_and_calls_no_model(self):
        provider = MagicMock()
        state = {**STATE, "excluye": [f"act-saldo_vencido-r{n}" for n in range(1, 6)]}

        result = propose_actions(provider, state, {"kind": "identified", "sentence": "Paga tarde"}, sources())

        assert result == {"actions": None, "insufficient_cause": None}
        provider.generate_structured.assert_not_called()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/agents && uv run pytest tests/test_orq.py tests/test_agents.py -q -k "split or retired or excluded or every_row"`
Expected: FAIL: `KeyError: 'excluye'` in the hand-off test, a retired node still taking `si`, and
the excluded row still in the prompt.

- [ ] **Step 3: Write the interpreter's changes**

In `packages/agents/centinela_agents/walk.py:walk_from`, replace the `if is_kpi(predicate.lee):`
branch head with a retired check first:

```python
        if node.retirado is not None:
            passed = False
        elif is_kpi(predicate.lee):
            metric, _ = kpi_column(predicate.lee)
            if metric != state["candidato"]["metrica"]:
                raise ValueError(f"{node.id} reads {metric} on a row of {state['candidato']['metrica']}")
            passed = kpi_holds(predicate, row, ctx)
        else:
            passed = state_holds(predicate, state, ctx)
```

In `packages/agents/centinela_agents/graph.py:predicate_node`, replace
`passed = state_holds(node.predicado, state, ctx)` with:

```python
        passed = node.retirado is None and state_holds(node.predicado, state, ctx)
```

In `graph.py:leaf_node`, replace the assignment of `given` with:

```python
        given = (
            {"alert_id": state["alert_id"], "action": approved_action(state), "decision": state.get("decision")}
            if leaf.agente == "ejecutor"
            else {**state, "excluye": list(leaf.excluye)} if leaf.excluye else state
        )
```

In `packages/agents/centinela_agents/agents/estratega.py:propose_actions`, replace the line
`rows = {row.ref: row for row in action_rows(metric)}` with:

```python
    excluded = set(state.get("excluye") or ())
    rows = {row.ref: row for row in action_rows(metric) if f"act-{metric}-{row.ref}" not in excluded}
    if not rows:
        return {"actions": None, "insufficient_cause": None}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd packages/agents && uv run pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/agents/centinela_agents/walk.py packages/agents/centinela_agents/graph.py packages/agents/centinela_agents/agents/estratega.py packages/agents/tests/test_orq.py packages/agents/tests/test_agents.py
git commit -q -F - <<'MSG'
A retired node now always takes its no and a split leaf hands Estratega the rows it excludes, so a split leaves every other metric's walk as it was and a leaf that excludes every row reaches a manual review without a model call.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 3: The three moves and the criteria that refuse them

**Files:**
- Create: `packages/agents/centinela_agents/expansion.py`
- Create: `packages/agents/arbol/crecimiento.yaml`
- Modify: `packages/agents/centinela_agents/validator.py` (add `load_grounds`)
- Create: `packages/agents/tests/test_expansion.py`

**Interfaces:**
- Consumes: `schema.resolve`, `validator.resolved`, `validator.problems`, `validator.capped_return`, `support.split_tree` (Task 1).
- Produces:
  - `Split(agente: str, hoja: str, nodo: Node, nueva: Node)`, `movimiento == "dividir_hoja"`;
    `Branch(agente: str, familia: str, metrica: str, nodos: tuple[Node, ...])`, `movimiento == "agregar_rama"`;
    `Retire(nodo: str, motivo: str, agente: str | None = None)`, `movimiento == "retirar"`;
    `Move` (their discriminated union) and `MOVE = TypeAdapter(Move)`.
  - `Caps(depth: int, nodes_per_stage: int)`, `Growth(repetitions: Mapping[str, int], caps: Caps)`,
    `load_growth(path: Path) -> Growth`.
  - `apply_move(tree: Tree, move) -> Tree` (keeps `tree.version`); `entry_of(move) -> str`;
    `move_problems(parent: Tree, move, grounds: Grounds) -> list[str]`;
    `cap_problems(tree: Tree, caps: Caps) -> list[str]`; `depth(nodes) -> int`;
    `expansion_problems(parent: Tree, move, grounds: Grounds, caps: Caps) -> list[str]`;
    `layer_hash(tree: Tree) -> str`;
    `replay(base: Tree, moves: Sequence, grounds: Grounds, caps: Caps) -> tuple[Tree, list[tuple[int, list[str]]]]`
    (the index of each dropped move and its problems).
  - `validator.load_grounds(arbol: Path, metricas: Path, skills: Path, catalog: Catalog) -> Grounds`.

- [ ] **Step 1: Write the failing tests**

Create `packages/agents/tests/test_expansion.py`:

```python
# The three moves of an expansion and the fixed criteria: a valid split and a valid branch pass and
# keep L0 and L1, each planted move is refused naming its criterion, the caps hold, and a replay
# drops only the moves the version refuses. Each test named test_orq_ is an ORQ- case.
from dataclasses import replace

import pytest

from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.expansion import Branch, Caps, MOVE, Retire, Split, apply_move, cap_problems, entry_of, expansion_problems, layer_hash, load_growth, replay
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Leaf, Node, Predicate, index
from centinela_agents.validator import load_grounds
from centinela_agents.walk import Context, detect
from support import ARBOL, DAY, KERNEL_CATALOG, METRICAS, SALDO_ROW, SKILLS, base_tree, grounds, reader_from, split_tree

WIDE = Caps(depth=100, nodes_per_stage=100)
DIVISION = "proponer.cartera.saldo_vencido.division_1"
NEW_LEAF = "hoja.estratega.proponer.saldo_vencido.1"
NODE = Node(id=DIVISION, fundamento="iso31000.6.5.2", predicado=Predicate(lee="estado.detection.metric", op="=", valor="saldo_vencido"), si=NEW_LEAF, no="hoja.estratega.proponer", divide="hoja.estratega.proponer")
HOJA = Leaf(agente="estratega", decision="proponer", skill="estratega/contrato.md", excluye=("act-saldo_vencido-r1",))
LEAF = Node(id=NEW_LEAF, hoja=HOJA, sigue="proponer.causa_insuficiente")
ENTRY = Node(id="detectar.cartera.retraso", fundamento="iso31000.6.4.2", predicado=Predicate(lee="estado.candidato.metrica", op="=", valor="retraso"), si="detectar.cartera.retraso.dias", no="fin.sin_alerta")
DAYS = Node(id="detectar.cartera.retraso.dias", fundamento="fin-pol-004.s4", predicado=Predicate(lee="kpi.retraso.dias_vencido", op=">", umbral="retraso"), si="hoja.vigia.titular", no="fin.sin_alerta")
WITH_RETRASO = Catalog({**KERNEL_CATALOG.kpis, "retraso": Kpi(("cliente_id",), frozenset({"cliente_id", "dias_vencido", "max_dias_vencido", "pesos_en_riesgo"}), thresholds={"dias_vencido": 1})})


def split(node=None, leaf=None, hoja=None, **changes):
    nueva = LEAF.model_copy(update={**(leaf or {}), **({"hoja": HOJA.model_copy(update=hoja)} if hoja else {})})
    return Split(**{"agente": "estratega", "hoja": "hoja.estratega.proponer", "nodo": NODE.model_copy(update=node or {}), "nueva": nueva, **changes})


def branch(**changes):
    return Branch(**{"agente": "vigia", "familia": "detectar.cartera", "metrica": "retraso", "nodos": (ENTRY, DAYS), **changes})


def test_orq_a_split_passes_keeps_l0_and_l1_and_yields_the_split_tree():
    assert expansion_problems(base_tree(), split(), grounds(), WIDE) == []
    child = apply_move(base_tree(), split())
    assert child == split_tree()
    assert layer_hash(child) == layer_hash(base_tree())
    assert entry_of(split()) == DIVISION


def test_orq_a_branch_for_a_new_kpi_passes_and_its_detection_walks_it():
    assert expansion_problems(base_tree(), branch(), grounds(catalog=WITH_RETRASO), WIDE) == []
    child = apply_move(base_tree(), branch())
    nodes = index(child)
    assert "retraso" in nodes["detectar.cartera"].predicado.valor
    assert nodes["detectar.cartera.dias_pago_prom"].no == "detectar.cartera.retraso"
    rows = {"retraso": [{"cliente_id": "CLI-009", "dias_vencido": 6, "pesos_en_riesgo": 100.0}], "saldo_vencido": [SALDO_ROW]}
    found = detect(Context.of(child, load_metrics(METRICAS), WITH_RETRASO, reader_from({DAY: rows})), DAY)
    assert {(detection.metric, detection.entry) for detection in found} == {("retraso", "hoja.vigia.titular"), ("saldo_vencido", "hoja.vigia.titular")}


PLANTED_MOVES = [
    ("split by another agent", split(agente="analista"), "analista splits hoja.estratega.proponer, a leaf of estratega"),
    ("the chat expands", split(agente="chat"), "chat expands nothing"),
    ("split node outside the stage", split(node={"id": "explicar.cartera.saldo_vencido.division_1"}), "is no L2 or L3 node of proponer"),
    ("split node at L1", split(node={"id": "proponer.division_1"}), "is no L2 or L3 node of proponer"),
    ("split leaf of another agent", split(hoja={"agente": "analista", "decision": "explicar", "skill": "analista/contrato.md"}), "is no leaf of estratega/proponer"),
    ("split leaf of another decision", split(hoja={"decision": "revision_manual"}), "is no leaf of estratega/proponer"),
    ("split that drops the old leaf", split(node={"no": "hoja.estratega.revision_manual"}), "must divide hoja.estratega.proponer, keep it on no"),
    ("split leaf that bypasses aprobar", split(leaf={"sigue": "hoja.ejecutor.ejecutar"}), "continues to hoja.ejecutor.ejecutar"),
    ("split leaf already in the tree", split(leaf={"id": "hoja.estratega.revision_manual"}, node={"si": "hoja.estratega.revision_manual"}), "hoja.estratega.revision_manual is already in the tree"),
    ("unregistered fundamento", split(node={"fundamento": "iso9999.1"}), "absent from fundamentos.yaml"),
    ("two operands", split(node={"predicado": Predicate(lee="estado.detection.metric y estado.cause.kind", op="=", valor="saldo_vencido")}), "which is not one operand"),
    ("undeclared state field", split(node={"predicado": Predicate(lee="estado.detection.humor", op="=", valor="x")}), "which the alert's state does not declare"),
    ("kpi outside detectar", split(node={"predicado": Predicate(lee="kpi.saldo_vencido.max_dias_vencido", op=">", umbral="saldo_vencido")}), "reads a KPI outside detectar"),
    ("unknown row excluded", split(hoja={"excluye": ("act-saldo_vencido-r99",)}), "which no row of acciones.md names"),
    ("branch under no family", branch(familia="aprobar.decision"), "which is no L2 family of detectar"),
    ("branch outside the agent's stage", branch(agente="estratega"), "which is no L2 family of proponer"),
    ("metric already admitted", branch(metrica="saldo_vencido"), "detectar.cartera already admits saldo_vencido"),
    ("branch entry that tests nothing", branch(nodos=(ENTRY.model_copy(update={"predicado": Predicate(lee="estado.candidato.descriptivo", op="=", valor=False)}), DAYS)), "starts at detectar.cartera.retraso, which tests estado.candidato.metrica = retraso"),
    ("branch exit around aprobar", branch(nodos=(ENTRY, DAYS.model_copy(update={"si": "hoja.ejecutor.ejecutar"}))), "exits to hoja.ejecutor.ejecutar"),
    ("branch leaf of a decision no base leaf takes", branch(nodos=(ENTRY, DAYS.model_copy(update={"si": "hoja.vigia.kpi"}), Node(id="hoja.vigia.kpi", hoja=Leaf(agente="vigia", decision="proponer_kpi", skill="vigia/contrato.md"), sigue="hoja.analista.explicar"))), "hoja.vigia.kpi is no leaf of vigia taking a decision and a route its base leaves take"),
    ("unknown umbral", branch(nodos=(ENTRY, DAYS.model_copy(update={"predicado": Predicate(lee="kpi.retraso.dias_vencido", op=">", umbral="inventada")}))), "absent from metricas.yaml and from the approved KPIs"),
    ("retire an L1 node", Retire(nodo="explicar.con_evidencia", motivo="No aplica"), "explicar.con_evidencia is an L1 node; only an L2 or L3 node retires"),
    ("retire a leaf", Retire(nodo="hoja.estratega.proponer", motivo="No aplica"), "hoja.estratega.proponer is a leaf; only an L2 or L3 node retires"),
    ("retire with no reason", Retire(nodo="detectar.cartera.saldo_vencido.dias", motivo=" "), "carries no reason"),
    ("retire outside the agent's stage", Retire(agente="estratega", nodo="detectar.cartera.saldo_vencido.dias", motivo="No aplica"), "estratega retires detectar.cartera.saldo_vencido.dias, outside its stage proponer"),
    ("retire the last branch of a metric", Retire(nodo="detectar.inventario.cobertura_dias.minima", motivo="No aplica"), "metric cobertura_dias has no L3 branch in detectar"),
    ("retire a node that is not there", Retire(nodo="detectar.nada", motivo="No aplica"), "detectar.nada, which is no node of the tree"),
]


@pytest.mark.parametrize("name, move, expected", PLANTED_MOVES, ids=[name for name, _, _ in PLANTED_MOVES])
def test_orq_the_criteria_refuse_each_planted_move(name, move, expected):
    found = expansion_problems(base_tree(), move, grounds(catalog=WITH_RETRASO), WIDE)
    assert any(expected in problem for problem in found), found


def test_orq_a_new_umbral_whose_source_quotes_no_document_is_refused():
    real = load_metrics(METRICAS)
    silent = replace(real, threshold_sources={**real.threshold_sources, "saldo_vencido": ""})
    days = DAYS.model_copy(update={"predicado": Predicate(lee="kpi.retraso.max_dias_vencido", op=">", umbral="saldo_vencido")})
    found = expansion_problems(base_tree(), branch(nodos=(ENTRY, days)), grounds(catalog=WITH_RETRASO, metrics=silent), WIDE)
    assert "detectar.cartera.retraso.dias names umbral saldo_vencido, whose fuente_umbral quotes no document" in found


def test_orq_a_move_past_a_cap_is_refused():
    assert any("past the cap of 3" in problem for problem in expansion_problems(base_tree(), split(), grounds(), Caps(depth=3, nodes_per_stage=100)))
    assert any(problem.startswith("stage proponer holds") for problem in expansion_problems(base_tree(), split(), grounds(), Caps(depth=100, nodes_per_stage=3)))


def test_the_settings_of_growth_load_and_hold_the_base_under_its_caps():
    growth = load_growth(ARBOL / "crecimiento.yaml")
    assert isinstance(growth.repetitions["estratega"], int) and growth.repetitions["estratega"] >= 1
    assert cap_problems(base_tree(), growth.caps) == []


def test_a_move_survives_its_json():
    for move in (split(), branch(), Retire(nodo=DIVISION, motivo="No ayudó")):
        assert MOVE.validate_python(move.model_dump(mode="json")) == move


def test_a_replay_applies_each_move_in_order_and_drops_the_refused_ones():
    retire = Retire(nodo=DIVISION, motivo="No ayudó")
    tree, dropped = replay(base_tree(), [split(), retire, split(agente="analista")], grounds(), WIDE)
    assert index(tree)[DIVISION].retirado == "No ayudó"
    assert [position for position, _ in dropped] == [2]


def test_load_grounds_returns_the_checked_base_and_its_registry():
    loaded = load_grounds(ARBOL, METRICAS, SKILLS, KERNEL_CATALOG)
    assert loaded.base == base_tree() and "iso31000.6.5.2" in loaded.registry
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/agents && uv run pytest tests/test_expansion.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'centinela_agents.expansion'`.

- [ ] **Step 3: Write the settings**

Create `packages/agents/arbol/crecimiento.yaml`; its values are D1 and D2:

```yaml
repeticiones:
  estratega:
    valor: 3
    fuente: "supuesto: a setting of the method, decided by a person; it decides when a split is drafted, never whether an alert fires"
topes:
  profundidad:
    valor: 40
    fuente: "supuesto: the nodes of the longest path, sized so a walk and its skill fit the context of the model the machine runs"
  nodos_por_etapa:
    valor: 64
    fuente: "supuesto: the nodes of one stage, sized as the depth is"
```

- [ ] **Step 4: Write `load_grounds`**

In `packages/agents/centinela_agents/validator.py`, add after `load_base`:

```python
def load_grounds(arbol: Path, metricas: Path, skills: Path, catalog: Catalog) -> Grounds:
    registry = load_registry(arbol / "fundamentos.yaml")
    metrics = load_metrics(metricas)
    return Grounds(checked_base(load_yaml(arbol / "base.yaml"), registry, metrics, catalog, skills), registry, metrics, catalog, skills)
```

- [ ] **Step 5: Write the moves**

Create `packages/agents/centinela_agents/expansion.py`:

```python
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


def split_move_problems(nodes: Mapping[str, Node], move: Split, stage: str) -> list[str]:
    leaf = nodes.get(move.hoja)
    if leaf is None or leaf.hoja is None:
        return [f"{move.agente} splits {move.hoja}, which is no leaf of the tree"]
    found: list[str] = []
    if leaf.hoja.agente != move.agente:
        found.append(f"{move.agente} splits {move.hoja}, a leaf of {leaf.hoja.agente}")
    found += fresh_problems(nodes, [move.nodo, move.nueva])
    if move.nodo.id.split(".")[0] != stage or level(move.nodo.id) == 1 or move.nodo.hoja is not None:
        found.append(f"{move.nodo.id} is no L2 or L3 node of {stage}, the stage of {move.agente}")
    if (move.nodo.divide, move.nodo.no, move.nodo.si) != (move.hoja, move.hoja, move.nueva.id):
        found.append(f"{move.nodo.id} must divide {move.hoja}, keep it on no and take {move.nueva.id} on si")
    new = move.nueva.hoja
    if new is None or (new.agente, new.decision) != (leaf.hoja.agente, leaf.hoja.decision):
        found.append(f"{move.nueva.id} is no leaf of {leaf.hoja.agente}/{leaf.hoja.decision}")
    if move.nueva.sigue != leaf.sigue:
        found.append(f"{move.nueva.id} continues to {move.nueva.sigue}, where {move.hoja} continues to {leaf.sigue}")
    return found


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
        return split_move_problems(nodes, move, stage)
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
    return [*problems(child.model_dump(), grounds), *cap_problems(child, caps)]


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
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd packages/agents && uv run pytest -q`
Expected: PASS. If `test_orq_a_split_passes_keeps_l0_and_l1_and_yields_the_split_tree` fails on
`child == split_tree()`, compare `child.model_dump()` with `split_tree().model_dump()`: the two
must list the same nodes in the same order, the base's first and the split's two last.

- [ ] **Step 7: Commit**

```bash
git add packages/agents/centinela_agents/expansion.py packages/agents/centinela_agents/validator.py packages/agents/arbol/crecimiento.yaml packages/agents/tests/test_expansion.py
git commit -q -F - <<'MSG'
The tree now grows only by three moves, a split, a branch and a retirement, which code applies and the validator checks against the agent's stage and label, the registry, the base's L0 and L1 and the caps of `crecimiento.yaml`, so no expansion can open a path around a person's approval.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 4: `Estratega` drafts a split from repeated rejections of one row

**Files:**
- Create: `packages/agents/centinela_agents/growth.py`
- Create: `packages/agents/tests/test_growth.py`

**Interfaces:**
- Consumes: `Split`, `Growth`, `Caps`, `Retire`, `apply_move`, `expansion_problems` (Task 3); `schema.resolve`, `Node.divide` (Task 1).
- Produces:
  - `Rejection(alert_id: str, metric: str, target: str, actions: tuple[str, ...])`.
  - `Grown(agent: str, move: Split, evidence: tuple[str, ...], tree: Tree | None, problems: tuple[str, ...] = ())`;
    `tree` is `None` when the criteria refused the draft.
  - `SPLIT_GROUND = "iso31000.6.5.2"` (D4); `COUNTED_TARGETS = ("propuesta",)` (D5).
  - `metric_leaf(nodes: Mapping[str, Node], metric: str, leaf: str = PROPOSER) -> str`.
  - `drafted_split(tree: Tree, metric: str, actions: Sequence[str]) -> Split | None`.
  - `grow(tree: Tree, grounds: Grounds, growth: Growth, rejections: Iterable[Rejection], consumed: Iterable[str]) -> list[Grown]`.

- [ ] **Step 1: Write the failing tests**

Create `packages/agents/tests/test_growth.py`:

```python
# Estratega's drafter: the count of rejections of one action row that drafts a split, the targets
# and rows that never count, the evidence a version already used, a second row that nests, a draft
# the criteria refuse, and no module of packages/agents that could persist a version. Each test
# named test_orq_ is an ORQ- case.
import re

import pytest

from centinela_agents.expansion import Caps, Growth, Retire, apply_move
from centinela_agents.growth import Rejection, grow, metric_leaf
from centinela_agents.schema import index
from support import AGENTS, base_tree, grounds

GROWTH = Growth({"estratega": 3}, Caps(depth=100, nodes_per_stage=100))
R1, R2 = "act-saldo_vencido-r1", "act-saldo_vencido-r2"
FIRST, SECOND = "proponer.cartera.saldo_vencido.division_1", "proponer.cartera.saldo_vencido.division_2"


def rejected(*alerts, actions=(R1,), metric="saldo_vencido", target="propuesta"):
    return [Rejection(alert, metric, target, tuple(actions)) for alert in alerts]


def test_orq_evidence_below_its_count_drafts_no_expansion():
    assert grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2"), ()) == []


def test_orq_rejections_of_one_row_at_its_count_split_estratega_leaf_for_that_metric():
    (grown,) = grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2", "A3"), ())
    assert (grown.agent, grown.evidence, grown.problems) == ("estratega", ("A1", "A2", "A3"), ())
    nodes = index(grown.tree)
    assert (nodes[FIRST].divide, nodes[FIRST].no, nodes[FIRST].si) == ("hoja.estratega.proponer", "hoja.estratega.proponer", "hoja.estratega.proponer.saldo_vencido.1")
    assert nodes[FIRST].fundamento == "iso31000.6.5.2"
    assert nodes["hoja.estratega.proponer.saldo_vencido.1"].hoja.excluye == (R1,)
    assert nodes["explicar.con_evidencia"].si == FIRST


@pytest.mark.parametrize(
    "rejections",
    [
        rejected("A1", "A2", "A3", target="causa"),
        rejected("A1", "A2", "A3", target="ambos"),
        rejected("A1", "A2", "A3", target="ninguno"),
        rejected("A1", "A2", "A3", actions=("act-revision-manual",)),
        rejected("A1", "A2", "A3", actions=("act-margen_pct-r1",)),
    ],
    ids=["causa", "ambos", "ninguno", "manual review", "another metric's row"],
)
def test_only_a_rejection_sent_to_the_proposal_counts_a_row_of_its_own_metric(rejections):
    assert grow(base_tree(), grounds(), GROWTH, rejections, ()) == []


def test_orq_a_retired_expansion_is_not_drafted_again_before_its_count():
    (first,) = grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2", "A3"), ())
    retired = apply_move(first.tree, Retire(nodo=FIRST, motivo="No ayudó"))
    assert grow(retired, grounds(), GROWTH, rejected("A1", "A2", "A3", "A4", "A5"), first.evidence) == []
    (again,) = grow(retired, grounds(), GROWTH, rejected("A1", "A2", "A3", "A4", "A5", "A6"), first.evidence)
    assert again.evidence == ("A4", "A5", "A6")
    assert index(again.tree)[SECOND].divide == "hoja.estratega.proponer"


def test_a_second_row_of_the_same_metric_nests_and_its_retirement_restores_the_first():
    (first,) = grow(base_tree(), grounds(), GROWTH, rejected("A1", "A2", "A3"), ())
    (second,) = grow(first.tree, grounds(), GROWTH, rejected("A4", "A5", "A6", actions=(R2,)), first.evidence)
    nodes = index(second.tree)
    assert nodes[SECOND].divide == "hoja.estratega.proponer.saldo_vencido.1"
    assert nodes["hoja.estratega.proponer.saldo_vencido.2"].hoja.excluye == (R1, R2)
    assert metric_leaf(nodes, "saldo_vencido") == "hoja.estratega.proponer.saldo_vencido.2"
    retired = index(apply_move(second.tree, Retire(nodo=SECOND, motivo="No ayudó")))
    assert metric_leaf(retired, "saldo_vencido") == "hoja.estratega.proponer.saldo_vencido.1"
    assert metric_leaf(retired, "margen_pct") == "hoja.estratega.proponer"


def test_rows_of_two_metrics_draft_two_splits_one_after_the_other():
    rejections = rejected("A1", "A2", "A3") + rejected("B1", "B2", "B3", metric="margen_pct", actions=("act-margen_pct-r3",))
    first, second = grow(base_tree(), grounds(), GROWTH, rejections, ())
    assert first.move.nodo.id == "proponer.margen.margen_pct.division_1"
    assert {"proponer.margen.margen_pct.division_1", FIRST} <= set(index(second.tree))


def test_a_draft_the_criteria_refuse_comes_back_with_its_problems_and_no_tree():
    tight = Growth({"estratega": 3}, Caps(depth=3, nodes_per_stage=100))
    (grown,) = grow(base_tree(), grounds(), tight, rejected("A1", "A2", "A3"), ())
    assert grown.tree is None and any("past the cap" in problem for problem in grown.problems)


def test_orq_no_module_of_packages_agents_opens_a_database_connection():
    sources = [path.read_text(encoding="utf-8") for path in (AGENTS / "centinela_agents").rglob("*.py")]
    assert not [text for text in sources if re.search(r"^\s*(import|from)\s+psycopg", text, re.MULTILINE)]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/agents && uv run pytest tests/test_growth.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'centinela_agents.growth'`.

- [ ] **Step 3: Write the drafter**

Create `packages/agents/centinela_agents/growth.py`:

```python
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
        evidence = tuple(sorted(set().union(*(rows[action] for action in reached))))
        found = expansion_problems(tree, move, grounds, growth.caps)
        if found:
            grown.append(Grown("estratega", move, evidence, None, tuple(found)))
            continue
        tree = apply_move(tree, move)
        grown.append(Grown("estratega", move, evidence, tree))
    return grown
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd packages/agents && uv run pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/agents/centinela_agents/growth.py packages/agents/tests/test_growth.py
git commit -q -F - <<'MSG'
Estratega now drafts, in code, a split of its leaf that stops offering an action row once a person's rejections sent to the proposal name that row in enough alerts of one metric, counting no alert an earlier version already used, so a retired expansion returns only on new evidence.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 5: Each alert carries the version of the tree it walked, and resumes on it

**Files:**
- Modify: `packages/agents/centinela_agents/walk.py:Context`
- Modify: `packages/agents/centinela_agents/state.py:AlertState`
- Modify: `packages/agents/centinela_agents/graph.py:initial_state`, `graph.py:stream_alert`, `graph.py:start_alert`
- Modify: `packages/agents/centinela_agents/day.py:run_day`
- Modify: `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator`
- Modify: `packages/agents/tests/test_day.py`, `packages/agents/tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `support.split_tree` (Task 1).
- Produces: `Context.version: int = 0`, set by `Context.of` from `tree.version`;
  `AlertState.arbol_version: int`; `stream_alert(..., tracer=None, arbol_version=None)` and
  `start_alert(..., tracer=None, arbol_version=None)`; `CentinelaOrchestrator.use_tree(tree: Tree) -> None`;
  `CentinelaOrchestrator.graph_of(alert_id: str)`; `CentinelaOrchestrator.run_day` walks the tree
  last handed to `use_tree`, whatever nodes its context carries.

- [ ] **Step 1: Write the failing tests**

Append to `packages/agents/tests/test_day.py`:

```python
def test_orq_each_alert_of_a_day_carries_the_version_of_the_tree_it_walked():
    tree = base_tree().model_copy(update={"version": 7})
    ctx = Context.of(tree, load_metrics(METRICAS), KERNEL_CATALOG, reader_from({DAY: {"saldo_vencido": [saldo("CLI-001")]}}))
    (run,) = runs(drive(run_day(compiled(Recorder(), tree=tree), ctx, DAY)))
    assert run.state["arbol_version"] == 7
```

In `packages/agents/tests/test_orchestrator.py`, add `from centinela_agents.walk import Context`
and `split_tree` to the `support` import, and append:

```python
def test_a_paused_alert_resumes_on_the_graph_of_the_version_it_started_on():
    orchestrator, action_id = paused_saldo_alert()
    first = orchestrator.graph
    orchestrator.use_tree(split_tree().model_copy(update={"version": 2}))
    assert orchestrator.graph is not first
    assert orchestrator.graph_of("A1") is first
    assert orchestrator.get_state("A1")["arbol_version"] == 1
    assert orchestrator.is_awaiting_decision("A1")
    assert ["ejecutar.vigente", "si"] in orchestrator.resume("A1", approve(action_id=action_id))["camino"]
    assert orchestrator.start(saldo_detection(), alert_id="A2", day=DAY)["arbol_version"] == 2


def test_run_day_walks_the_tree_in_use_whatever_tree_its_context_carries():
    orchestrator, _ = paused_saldo_alert()
    orchestrator.use_tree(base_tree().model_copy(update={"version": 5}))
    ctx = Context.of(base_tree(), load_metrics(METRICAS), KERNEL_CATALOG, reader_from({DAY: {"saldo_vencido": [SALDO_ROW]}}))
    run, sent, states = orchestrator.run_day(ctx, DAY), None, []
    while True:
        try:
            event = run.send(sent)
        except StopIteration:
            break
        sent = Verdict(recorded=True) if isinstance(event, AlertRun) else None
        if isinstance(event, AlertRun):
            states.append(event.state)
    assert [state["arbol_version"] for state in states] == [5]
```

and add `from centinela_agents.day import AlertRun, Verdict` to its imports.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/agents && uv run pytest tests/test_day.py tests/test_orchestrator.py -q`
Expected: FAIL: `KeyError: 'arbol_version'` and `AttributeError: ... has no attribute 'use_tree'`.

- [ ] **Step 3: Write the version into the state**

In `packages/agents/centinela_agents/walk.py`, add the field `version: int = 0` after `call` in
`Context`, and make `Context.of` return
`cls(index(tree), metrics, catalog, reader, dict(owners or {}), call, tree.version)`.

In `packages/agents/centinela_agents/state.py:AlertState`, add `arbol_version: int` after `entry: str`.

In `packages/agents/centinela_agents/graph.py`, give `initial_state` a last parameter
`arbol_version=None` and the key `"arbol_version": arbol_version` right after `"entry"`; give
`stream_alert` and `start_alert` a last keyword parameter `arbol_version=None`, passed by
`stream_alert` as the last argument of `initial_state` and by `start_alert` to `stream_alert`.

In `packages/agents/centinela_agents/day.py:run_day`, pass `arbol_version=ctx.version,` to
`stream_alert`, after `tracer=tracer,`.

- [ ] **Step 4: Write the orchestrator's versions**

In `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.__init__`, replace
`self.graph = self.compiler.graph(tree)` with:

```python
        self._graphs: dict[int, Any] = {}
        self.use_tree(tree)
```

add these methods after `use_thresholds`:

```python
    def use_tree(self, tree: Tree) -> None:
        self.tree = tree
        self.graph = self.compiler.graph(tree)
        self._graphs[tree.version] = self.graph

    def graph_of(self, alert_id: str):
        version = (self.graph.get_state(thread(alert_id)).values or {}).get("arbol_version")
        return self._graphs.get(version, self.graph)
```

then:
- in `start`, pass `arbol_version=self.tree.version,` to `start_alert`, after `tracer=self.tracer,`;
- in `is_awaiting_decision`, return `awaiting_decision(self.graph_of(alert_id), alert_id)`;
- in `resume`, call `resume(self.graph_of(alert_id), alert_id, decision, tracer=self.tracer)`;
- in `get_state`, return `self.graph_of(alert_id).get_state(thread(alert_id)).values`;
- replace `run_day` with:

```python
    def run_day(self, ctx: Context, day: str, *, earlier=(), watched=None, limit: int = 3, cause_rejections=None, proposal_rejections=None):
        ctx = replace(ctx, nodes=index(self.tree), version=self.tree.version)
        return run_day(self.graph, ctx, day, earlier=earlier, watched=watched, limit=limit, cause_rejections=cause_rejections, proposal_rejections=proposal_rejections, tracer=self.tracer)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd packages/agents && uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/agents/centinela_agents/walk.py packages/agents/centinela_agents/state.py packages/agents/centinela_agents/graph.py packages/agents/centinela_agents/day.py packages/agents/centinela_agents/orchestrator.py packages/agents/tests/test_day.py packages/agents/tests/test_orchestrator.py
git commit -q -F - <<'MSG'
Each alert now carries the version of the tree it walked, the orchestrator runs a day on the version it was last handed and resumes a paused alert on the graph of its own version, so a version written between a proposal and its decision never reroutes that decision.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 6: `apps/api` stores the tree's versions and the rejections, and grows the tree at the start of each day

**Files:**
- Modify: `apps/api/sql/01_esquema.sql`
- Create: `apps/api/src/centinela_api/arboles.py`, `apps/api/src/centinela_api/rechazos.py`
- Modify: `apps/api/src/centinela_api/agentes.py` (`_SKILLS`, `_CRECIMIENTO`, `get_grounds`, `get_growth`)
- Modify: `apps/api/src/centinela_api/alertas.py` (`fijar_version`)
- Modify: `apps/api/src/centinela_api/modelos.py` (`LogEventType`, `ExpansionEvidence`, `TreeExpansion`)
- Modify: `apps/api/src/centinela_api/routers/simulacion.py:avanzar(dias, persona, conn)`, `routers/simulacion.py:_registrar(conn, corrida, dia, day_str, nota)`
- Modify: `apps/api/src/centinela_api/routers/alertas.py:_decidir(alerta, decision, persona, conn)`
- Modify: `apps/api/tests/corridas.py`, `apps/api/tests/test_avanzar.py`, `apps/api/tests/test_ciclo_orquestado.py`
- Create: `apps/api/tests/test_arboles.py`
- Modify: `apps/web/src/api/openapi.json`, `apps/web/src/api/schema.generated.ts` (regenerated), `apps/web/src/logEvent.ts`, `apps/web/src/screens/Bitacora.tsx`

**Interfaces:**
- Consumes: `MOVE`, `Split`, `Branch`, `Retire`, `apply_move`, `entry_of`, `expansion_problems`,
  `layer_hash`, `replay`, `load_growth`, `Growth` (Task 3); `Rejection`, `grow` (Task 4);
  `load_grounds` (Task 3); `use_tree` (Task 5).
- Produces:
  - `arboles.CLIENTE`, `arboles.Version` (`id, padre, origen, agente, autor, movimiento, evidencia, retira, base_hash, arbol, dia_simulado, creado_en`);
  - `arboles.versiones(conn) -> list[Version]`; `arboles.insertar(conn, *, padre, origen, arbol, base, dia, agente=None, autor=None, movimiento=None, evidencia=(), retira=None) -> int`;
  - `arboles.huella(base) -> str`; `arboles.vigente(conn, grounds, growth, dia) -> Tree`;
    `arboles.del_dia(conn, dia) -> Tree`; `arboles.describir(movimiento) -> str`;
    `arboles.expansiones(filas, titulos) -> list[TreeExpansion]`;
    `arboles.retirar(conn, id, motivo, persona, dia, titulos) -> TreeExpansion`, raising
    `ExpansionDesconocida`, `YaRetirada` or `RetiroRechazado(problemas)`;
  - `rechazos.registrar(conn, alerta_id, metrica, destino, acciones, motivo, dia) -> None`;
    `rechazos.listar(conn) -> list[Rejection]`;
  - `alertas.fijar_version(conn, id, version) -> None`;
  - `agentes.get_grounds() -> Grounds`, `agentes.get_growth() -> Growth`;
  - models `ExpansionEvidence(alert_id, title: Sentence)` and `TreeExpansion(id, agent, simulated_date, created_at, description, evidence, status, retired_by, retire_reason)`;
    `LogEventType` gains `"arbol"`.

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/test_arboles.py`:

```python
# The tree's versions in apps/api over an in-memory store: the base row a first day writes, the
# expansion three rejections draft, the evidence a version already used, the replay a merged base
# forces, and the retirement of an expansion and its refusals.
import datetime as dt
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from centinela_agents.expansion import Caps, Growth
from centinela_agents.growth import Rejection
from centinela_agents.validator import load_grounds

from centinela_api import agentes, arboles
from centinela_api.modelos import Persona
from corridas import ARBOL, CONTEXTO

DIA = dt.date(2026, 1, 15)
GERENTE = Persona(email="gerente@andina.test", name="Ana", role="gerente")
GROUNDS = load_grounds(agentes._ARBOL.parent, agentes.METRICAS, agentes._SKILLS, CONTEXTO.catalog)
GROWTH = Growth({"estratega": 3}, Caps(depth=100, nodes_per_stage=100))
DIVISION = "proponer.cartera.saldo_vencido.division_1"


class Almacen:
    def __init__(self):
        self.filas: list[arboles.Version] = []

    def versiones(self, conn):
        return list(self.filas)

    def insertar(self, conn, *, padre, origen, arbol, base, dia, agente=None, autor=None, movimiento=None, evidencia=(), retira=None):
        fila = arboles.Version(len(self.filas) + 1, padre, origen, agente, autor, movimiento, list(evidencia), retira, arboles.huella(base), arbol.model_dump(mode="json"), dia, dt.datetime(2026, 10, 4, 12, tzinfo=dt.UTC))
        self.filas.append(fila)
        return fila.id


@pytest.fixture
def almacen(monkeypatch):
    almacen = Almacen()
    monkeypatch.setattr(arboles, "versiones", almacen.versiones)
    monkeypatch.setattr(arboles, "insertar", almacen.insertar)
    monkeypatch.setattr(arboles.agentes, "get_grounds", lambda: GROUNDS)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: GROWTH)
    monkeypatch.setattr(arboles.rechazos, "listar", lambda conn: [])
    monkeypatch.setattr(arboles.bitacora, "registrar", MagicMock())
    return almacen


def tres_rechazos(monkeypatch):
    rechazos = [Rejection(f"alerta_{n}", "saldo_vencido", "propuesta", ("act-saldo_vencido-r1",)) for n in range(3)]
    monkeypatch.setattr(arboles.rechazos, "listar", lambda conn: rechazos)


def test_el_primer_dia_guarda_el_arbol_base_y_lo_entrega_con_su_version(almacen):
    arbol = arboles.del_dia(MagicMock(), DIA)
    (fila,) = almacen.filas
    assert (fila.origen, fila.padre) == ("base", None)
    assert arbol.version == fila.id and arbol.nodos == ARBOL.nodos


def test_otro_dia_sobre_la_misma_base_no_escribe_otra_version(almacen):
    arboles.del_dia(MagicMock(), DIA)
    arboles.del_dia(MagicMock(), DIA)
    assert len(almacen.filas) == 1


def test_tres_rechazos_de_una_fila_dividen_la_hoja_de_estratega(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arbol = arboles.del_dia(MagicMock(), DIA)
    base, expansion = almacen.filas
    assert (expansion.origen, expansion.agente, expansion.padre) == ("expansion", "estratega", base.id)
    assert expansion.evidencia == ["alerta_0", "alerta_1", "alerta_2"]
    assert arbol.version == expansion.id and DIVISION in {nodo.id for nodo in arbol.nodos}
    registro = arboles.bitacora.registrar.call_args.args
    assert registro[2] == "arbol" and registro[3].agent == "estratega"
    assert registro[4].startswith("Cambió el árbol de decisión: Deja de proponer en Cartera vencida: Borrador de correo")


def test_la_evidencia_de_una_version_no_cuenta_otra_vez(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    arboles.del_dia(MagicMock(), DIA)
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion"]


def test_una_base_nueva_reaplica_las_expansiones_que_aun_pasan(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    nueva = GROUNDS.base.model_copy(update={"version": 2})
    monkeypatch.setattr(arboles.agentes, "get_grounds", lambda: replace(GROUNDS, base=nueva))
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion", "base"]
    assert DIVISION in {nodo.id for nodo in arbol.nodos} and arbol.version == almacen.filas[-1].id


def test_una_base_nueva_descarta_y_registra_la_expansion_que_ya_no_pasa(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    nueva = GROUNDS.base.model_copy(update={"version": 2})
    monkeypatch.setattr(arboles.agentes, "get_grounds", lambda: replace(GROUNDS, base=nueva))
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: Growth({"estratega": 3}, Caps(depth=3, nodes_per_stage=100)))
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert DIVISION not in {nodo.id for nodo in arbol.nodos}
    detalle = arboles.bitacora.registrar.call_args_list[-1].args[4]
    assert detalle.startswith("Un cambio del árbol no se aplicó sobre la base nueva y se descartó")


def test_un_fallo_al_crecer_deja_correr_el_dia_sobre_la_version_vigente(almacen, monkeypatch, caplog):
    monkeypatch.setattr(arboles, "grow", MagicMock(side_effect=RuntimeError("roto")))
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert arbol.version == almacen.filas[-1].id
    assert "Growing the tree failed" in caplog.text


def test_retirar_una_expansion_la_marca_y_su_evidencia_no_vuelve_a_contar(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    expansion = arboles.retirar(MagicMock(), 2, " No ayudó ", GERENTE, DIA, {})
    assert (expansion.status, expansion.retired_by, expansion.retire_reason) == ("retired", "Ana", "No ayudó")
    retiro = almacen.filas[-1]
    assert (retiro.origen, retiro.retira, retiro.autor) == ("retiro", 2, {"name": "Ana", "role": "gerente"})
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert next(nodo for nodo in arbol.nodos if nodo.id == DIVISION).retirado == "No ayudó"
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion", "retiro"]


@pytest.mark.parametrize(
    "id, motivo, error",
    [(9, "No ayudó", arboles.ExpansionDesconocida), (1, "No ayudó", arboles.ExpansionDesconocida), (2, "   ", arboles.RetiroRechazado)],
    ids=["unknown", "a base row", "no reason"],
)
def test_retirar_rechaza_lo_que_no_es_una_expansion_retirable(almacen, monkeypatch, id, motivo, error):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    with pytest.raises(error):
        arboles.retirar(MagicMock(), id, motivo, GERENTE, DIA, {})


def test_retirar_dos_veces_es_un_error(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    arboles.retirar(MagicMock(), 2, "No ayudó", GERENTE, DIA, {})
    with pytest.raises(arboles.YaRetirada):
        arboles.retirar(MagicMock(), 2, "Otra vez", GERENTE, DIA, {})


def test_la_lista_trae_las_expansiones_mas_nuevas_primero_con_el_titulo_de_su_evidencia(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    titulo = arboles.Sentence(text="Cartera vencida de CLI-001", figures=[])
    (expansion,) = arboles.expansiones(almacen.filas, {"alerta_0": titulo})
    assert (expansion.id, expansion.agent, expansion.status) == ("2", "estratega", "active")
    assert [evidencia.title.text for evidencia in expansion.evidence] == ["Cartera vencida de CLI-001", "alerta_1", "alerta_2"]
```

In `apps/api/tests/corridas.py`, replace the construction of `CONTEXTO` with:

```python
ARBOL = Tree.model_validate(load_yaml(agentes._ARBOL))
CONTEXTO = Context.of(
    ARBOL,
    load_metrics(agentes.METRICAS),
    catalog_from_kernel({"kpis": kpi_catalogo(catalogue_of(load_entries(agentes.METRICAS), load_sources()))}),
    lambda metric, day: [],
)
```

and add to `dia_con`, beside the other `monkeypatch.setattr` calls:

```python
    monkeypatch.setattr(simulacion_router.arboles, "del_dia", lambda conn, dia: ARBOL)
    monkeypatch.setattr(simulacion_router.alertas_repo, "fijar_version", MagicMock())
```

Append to `apps/api/tests/test_avanzar.py` (and add `from unittest.mock import ANY` to its imports):

```python
def test_el_dia_corre_sobre_la_version_que_crecio_y_guarda_la_de_cada_alerta(cliente, monkeypatch):
    from corridas import ARBOL
    arbol = ARBOL.model_copy(update={"version": 9})
    dia_con(monkeypatch, corrida("alerta_a", deteccion(), "nueva", "en análisis", "propuesta", arbol_version=9))
    monkeypatch.setattr(simulacion_router.arboles, "del_dia", lambda conn, dia: arbol)
    cliente.post("/simulacion/avanzar?dias=1")
    simulacion_router.get_orchestrator().use_tree.assert_called_once_with(arbol)
    simulacion_router.alertas_repo.fijar_version.assert_called_once_with(ANY, "alerta_a", 9)
```

Append to `apps/api/tests/test_ciclo_orquestado.py`:

```python
def test_un_rechazo_guarda_su_destino_y_las_acciones_que_rechazo(monkeypatch, guardadas):
    _con_orquestador(monkeypatch, return_value={"rejection_target": "propuesta"})
    registrar = MagicMock()
    monkeypatch.setattr(alertas_router.rechazos, "registrar", registrar)
    TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "reject", "reason": " No aplica "})
    registrar.assert_called_once_with(ANY, "alerta_1", "saldo_vencido", "propuesta", ["accion_1"], "No aplica", DIA)


@pytest.mark.parametrize("en_pausa, estado", [(True, {}), (False, {"rejection_target": "propuesta"})], ids=["no target", "no paused graph"])
def test_un_rechazo_que_el_clasificador_no_dirigio_no_guarda_evidencia(monkeypatch, guardadas, en_pausa, estado):
    orquestador = _con_orquestador(monkeypatch, return_value=estado)
    orquestador.is_awaiting_decision.return_value = en_pausa
    registrar = MagicMock()
    monkeypatch.setattr(alertas_router.rechazos, "registrar", registrar)
    TestClient(app).post("/alertas/alerta_1/decision", json={"kind": "reject", "reason": "No aplica"})
    registrar.assert_not_called()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd apps/api && pytest -q tests/test_arboles.py tests/test_avanzar.py tests/test_ciclo_orquestado.py`
Expected: FAIL with `ImportError: cannot import name 'arboles' from 'centinela_api'`.

- [ ] **Step 3: Write the schema**

Append to `apps/api/sql/01_esquema.sql`, and add `'arbol'` to the list of
`bitacora_tipo_check`, after `'costo'`:

```sql
ALTER TABLE api.alertas ADD COLUMN IF NOT EXISTS arbol_version bigint;

CREATE TABLE IF NOT EXISTS api.arbol_versiones (
  id bigserial PRIMARY KEY,
  cliente text NOT NULL,
  padre bigint REFERENCES api.arbol_versiones (id),
  origen text NOT NULL CHECK (origen IN ('base', 'expansion', 'retiro')),
  agente text,
  autor jsonb,
  movimiento jsonb,
  evidencia jsonb NOT NULL DEFAULT '[]'::jsonb,
  retira bigint REFERENCES api.arbol_versiones (id),
  base_version int NOT NULL,
  base_hash text NOT NULL,
  hash_l01 text NOT NULL,
  arbol jsonb NOT NULL,
  dia_simulado date,
  creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_arbol_versiones_cliente ON api.arbol_versiones (cliente, id);

CREATE TABLE IF NOT EXISTS api.rechazos (
  alerta_id text PRIMARY KEY REFERENCES api.alertas (id),
  metrica text NOT NULL,
  destino text NOT NULL CHECK (destino IN ('causa', 'propuesta', 'ambos', 'ninguno')),
  acciones jsonb NOT NULL,
  motivo text NOT NULL,
  dia_simulado date NOT NULL,
  creado_en timestamptz NOT NULL DEFAULT now()
);
```

- [ ] **Step 4: Write the models and the bridge**

In `apps/api/src/centinela_api/modelos.py`, add `"arbol"` at the end of `LogEventType`, add
`, arbol` to the end of the `LogEvent.type` description's list, and add after `class Settings`:

```python
class ExpansionEvidence(Esquema):
    """An alert whose rejection counted toward an expansion of the decision tree."""
    alert_id: str = Field(..., description="The rejected alert")
    title: Sentence = Field(..., description="The alert's title with its figures, or its id when the alert is gone")


class TreeExpansion(Esquema):
    """A change an agent made to the decision tree, and whether it still holds."""
    id: str = Field(..., description="The version the change wrote")
    agent: Agent = Field(..., description="The agent whose stage the change grew")
    simulated_date: str | None = Field(..., description="The simulated day the change was drafted on")
    created_at: str = Field(..., description="When it was written, real time")
    description: str = Field(..., description="What the change does, in Spanish")
    evidence: list[ExpansionEvidence] = Field(..., description="The alerts whose rejections drafted it")
    status: Literal["active", "retired"] = Field(..., description="Whether the change still holds")
    retired_by: str | None = Field(None, description="Who retired it")
    retire_reason: str | None = Field(None, description="Why it was retired")
```

In `apps/api/src/centinela_api/agentes.py`, add the imports
`from centinela_agents.expansion import Growth, load_growth` and
`from centinela_agents.validator import Grounds, load_grounds`, add after `METRICAS`:

```python
_SKILLS = _ROOT / "packages" / "agents" / "skills"
_CRECIMIENTO = _ARBOL.parent / "crecimiento.yaml"
```

add `_grounds: Grounds | None = None` after `_context`, and after `get_context`:

```python
def get_grounds() -> Grounds:
    global _grounds
    if _grounds is None:
        _grounds = load_grounds(_ARBOL.parent, METRICAS, _SKILLS, get_kernel().catalog)
    return _grounds


@cache
def get_growth() -> Growth:
    return load_growth(_CRECIMIENTO)
```

In `apps/api/src/centinela_api/alertas.py`, add after `fijar_costo`:

```python
def fijar_version(conn: psycopg.Connection, id: str, version: int | None) -> None:
    conn.execute("UPDATE api.alertas SET arbol_version = %s WHERE id = %s", (version, id))
```

Create `apps/api/src/centinela_api/rechazos.py`:

```python
import datetime
from collections.abc import Sequence

import psycopg
from psycopg.types.json import Jsonb

from centinela_agents.growth import Rejection


def registrar(conn: psycopg.Connection, alerta_id: str, metrica: str, destino: str, acciones: Sequence[str], motivo: str, dia: datetime.date) -> None:
    conn.execute(
        "INSERT INTO api.rechazos (alerta_id, metrica, destino, acciones, motivo, dia_simulado) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (alerta_id) DO NOTHING",
        (alerta_id, metrica, destino, Jsonb(list(acciones)), motivo, dia),
    )


def listar(conn: psycopg.Connection) -> list[Rejection]:
    filas = conn.execute("SELECT alerta_id, metrica, destino, acciones FROM api.rechazos ORDER BY creado_en").fetchall()
    return [Rejection(alerta_id, metrica, destino, tuple(acciones)) for alerta_id, metrica, destino, acciones in filas]
```

- [ ] **Step 5: Write the store of versions**

Create `apps/api/src/centinela_api/arboles.py`:

```python
import datetime
import hashlib
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from centinela_agents.agents.estratega import POLICY
from centinela_agents.expansion import MOVE, Branch, Retire, Split, apply_move, entry_of, expansion_problems, layer_hash, replay
from centinela_agents.growth import grow
from centinela_agents.schema import Tree
from centinela_agents.skills import action_rows

from . import agentes, bitacora, configuracion, rechazos
from .modelos import ActorAgent, ActorPerson, ExpansionEvidence, Persona, Sentence, TreeExpansion

logger = logging.getLogger(__name__)

CLIENTE = "distribuidora_andina"
CERROJO = "SELECT pg_advisory_xact_lock(hashtext('api.arbol_versiones'))"
COLUMNAS = "id, padre, origen, agente, autor, movimiento, evidencia, retira, base_hash, arbol, dia_simulado, creado_en"


@dataclass(frozen=True)
class Version:
    id: int
    padre: int | None
    origen: str
    agente: str | None
    autor: Mapping[str, Any] | None
    movimiento: Mapping[str, Any] | None
    evidencia: list[str]
    retira: int | None
    base_hash: str
    arbol: Mapping[str, Any]
    dia_simulado: datetime.date | None
    creado_en: datetime.datetime


class ExpansionDesconocida(Exception):
    pass


class YaRetirada(Exception):
    pass


class RetiroRechazado(Exception):
    def __init__(self, problemas: list[str]):
        super().__init__("; ".join(problemas))
        self.problemas = problemas


def huella(base: Tree) -> str:
    return hashlib.sha256(base.model_dump_json().encode()).hexdigest()


def versiones(conn: psycopg.Connection) -> list[Version]:
    filas = conn.execute(f"SELECT {COLUMNAS} FROM api.arbol_versiones WHERE cliente = %s ORDER BY id", (CLIENTE,)).fetchall()
    return [Version(*fila) for fila in filas]


def insertar(conn: psycopg.Connection, *, padre, origen, arbol: Tree, base: Tree, dia, agente=None, autor=None, movimiento=None, evidencia=(), retira=None) -> int:
    return conn.execute(
        "INSERT INTO api.arbol_versiones (cliente, padre, origen, agente, autor, movimiento, evidencia, retira, "
        "base_version, base_hash, hash_l01, arbol, dia_simulado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            CLIENTE, padre, origen, agente,
            None if autor is None else Jsonb(dict(autor)),
            None if movimiento is None else Jsonb(movimiento),
            Jsonb(list(evidencia)), retira, base.version, huella(base), layer_hash(arbol),
            Jsonb(arbol.model_dump(mode="json")), dia,
        ),
    ).fetchone()[0]


def con_version(arbol: Tree, id: int) -> Tree:
    return arbol.model_copy(update={"version": id})


def actor(fila: Version):
    return ActorAgent(agent=fila.agente) if fila.agente else ActorPerson(**fila.autor)


def accion(metrica: str, id: str) -> str:
    fila = {f"act-{metrica}-{fila.ref}": fila for fila in action_rows(metrica)}.get(id)
    if fila is None:
        return id
    dueno = next((parametro.split(":", 1)[1].strip() for parametro in fila.parameters if parametro.startswith("owner:")), None)
    nombre = configuracion.TIPOS.get(fila.type, fila.type) + (f" para {dueno}" if dueno else "")
    return f"{nombre} ({fila.policy})" if POLICY.match(fila.policy) else nombre


def describir(movimiento) -> str:
    if isinstance(movimiento, Split):
        metrica = movimiento.nodo.predicado.valor
        return f"Deja de proponer en {agentes.etiqueta(metrica)}: {'; '.join(accion(metrica, id) for id in movimiento.nueva.hoja.excluye)}"
    if isinstance(movimiento, Branch):
        return f"Vigila {agentes.etiqueta(movimiento.metrica)} en {movimiento.familia}"
    return f"Retira {movimiento.nodo}: {movimiento.motivo}"


def vigente(conn: psycopg.Connection, grounds, growth, dia: datetime.date) -> Tree:
    filas = versiones(conn)
    cabeza = filas[-1] if filas else None
    if cabeza is not None and cabeza.base_hash == huella(grounds.base):
        return con_version(Tree.model_validate(cabeza.arbol), cabeza.id)
    cambios = [fila for fila in filas if fila.movimiento is not None]
    arbol, descartados = replay(grounds.base, [MOVE.validate_python(fila.movimiento) for fila in cambios], grounds, growth.caps)
    for posicion, problemas in descartados:
        fila = cambios[posicion]
        logger.warning("Version %s does not apply over the new base: %s", fila.id, problemas)
        bitacora.registrar(conn, None, "arbol", actor(fila), f"Un cambio del árbol no se aplicó sobre la base nueva y se descartó: {describir(MOVE.validate_python(fila.movimiento))}", dia)
    return con_version(arbol, insertar(conn, padre=cabeza.id if cabeza else None, origen="base", arbol=arbol, base=grounds.base, dia=dia))


def consumidas(filas: list[Version]) -> set[str]:
    return {alerta for fila in filas for alerta in fila.evidencia}


def del_dia(conn: psycopg.Connection, dia: datetime.date) -> Tree:
    grounds, growth = agentes.get_grounds(), agentes.get_growth()
    with conn.transaction():
        conn.execute(CERROJO)
        arbol = vigente(conn, grounds, growth, dia)
        try:
            crecidos = grow(arbol, grounds, growth, rechazos.listar(conn), consumidas(versiones(conn)))
        except Exception as error:
            logger.error("Growing the tree failed: %s", error, exc_info=True)
            crecidos = []
        for crecido in crecidos:
            quien = ActorAgent(agent=crecido.agent)
            if crecido.tree is None:
                logger.warning("A draft of %s was refused: %s", crecido.agent, crecido.problems)
                bitacora.registrar(conn, None, "arbol", quien, f"Un cambio del árbol no pasó el validador y se descartó: {describir(crecido.move)}", dia)
                continue
            id = insertar(conn, padre=arbol.version, origen="expansion", arbol=crecido.tree, base=grounds.base, dia=dia, agente=crecido.agent, movimiento=crecido.move.model_dump(mode="json"), evidencia=crecido.evidence)
            arbol = con_version(crecido.tree, id)
            bitacora.registrar(conn, None, "arbol", quien, f"Cambió el árbol de decisión: {describir(crecido.move)}. Lo sostienen {len(crecido.evidence)} alertas rechazadas.", dia)
    return arbol


def expansion(fila: Version, retiro: Version | None, titulos: Mapping[str, Sentence]) -> TreeExpansion:
    return TreeExpansion(
        id=str(fila.id),
        agent=fila.agente,
        simulated_date=fila.dia_simulado.isoformat() if fila.dia_simulado else None,
        created_at=fila.creado_en.isoformat(),
        description=describir(MOVE.validate_python(fila.movimiento)),
        evidence=[ExpansionEvidence(alert_id=id, title=titulos.get(id) or Sentence(text=id, figures=[])) for id in fila.evidencia],
        status="retired" if retiro else "active",
        retired_by=retiro.autor["name"] if retiro and retiro.autor else None,
        retire_reason=MOVE.validate_python(retiro.movimiento).motivo if retiro else None,
    )


def expansiones(filas: list[Version], titulos: Mapping[str, Sentence]) -> list[TreeExpansion]:
    retiros = {fila.retira: fila for fila in filas if fila.retira is not None}
    return [expansion(fila, retiros.get(fila.id), titulos) for fila in reversed(filas) if fila.origen == "expansion"]


def retirar(conn: psycopg.Connection, id: int, motivo: str, persona: Persona, dia: datetime.date, titulos: Mapping[str, Sentence]) -> TreeExpansion:
    grounds, growth = agentes.get_grounds(), agentes.get_growth()
    with conn.transaction():
        conn.execute(CERROJO)
        filas = versiones(conn)
        fila = next((fila for fila in filas if fila.id == id and fila.origen == "expansion"), None)
        if fila is None:
            raise ExpansionDesconocida(id)
        if any(otra.retira == id for otra in filas):
            raise YaRetirada(id)
        arbol = vigente(conn, grounds, growth, dia)
        cambio = MOVE.validate_python(fila.movimiento)
        movimiento = Retire(nodo=entry_of(cambio), motivo=motivo.strip())
        problemas = expansion_problems(arbol, movimiento, grounds, growth.caps)
        if problemas:
            raise RetiroRechazado(problemas)
        autor = {"name": persona.name, "role": persona.role}
        retiro = insertar(conn, padre=arbol.version, origen="retiro", arbol=apply_move(arbol, movimiento), base=grounds.base, dia=dia, autor=autor, movimiento=movimiento.model_dump(mode="json"), retira=id)
        bitacora.registrar(conn, None, "arbol", ActorPerson(**autor), f"Retiró el cambio del árbol «{describir(cambio)}»: {motivo.strip()}", dia)
    return expansion(fila, next(otra for otra in versiones(conn) if otra.id == retiro), titulos)
```

- [ ] **Step 6: Wire the day run and the rejection**

In `apps/api/src/centinela_api/routers/simulacion.py`:
- add `arboles` to `from .. import bitacora, ciclo_vida, configuracion, consultas, permisos, simulacion`;
- in `avanzar`'s `corrida`, right after `umbrales = configuracion.umbrales(ajustes)`, add
  `arbol = arboles.del_dia(conn, nuevo_dia)`, and after `orq.use_thresholds(umbrales)` add
  `orq.use_tree(arbol)`;
- in `_registrar`, after `alertas_repo.fijar_costo(conn, alert_id, state.get("cost") or {})`, add
  `alertas_repo.fijar_version(conn, alert_id, state.get("arbol_version"))`.

In `apps/api/src/centinela_api/routers/alertas.py`, add `rechazos` to
`from .. import bitacora, ciclo_vida, configuracion, consultas, decisiones, permisos, simulacion`,
and in `_decidir`'s `DecisionReject` branch replace `await asyncio.to_thread(orq.resume, id, {`
… `})` with:

```python
                estado = await asyncio.to_thread(orq.resume, id, {
                    "id": f"dec_{uuid.uuid4().hex[:8]}",
                    "kind": "reject",
                    "reason": decision.reason,
                    "simulated_day": dia.isoformat(),
                })
                destino = (estado or {}).get("rejection_target")
                if destino:
                    with conn.transaction():
                        rechazos.registrar(conn, id, nueva.metric, destino, [accion.id for accion in nueva.actions], decision.reason.strip(), dia)
```

- [ ] **Step 7: Give the web the log type**

In `apps/web/src/logEvent.ts`, add `arbol: 'Árbol de decisión',` to `WITHOUT_ALERT`; in
`apps/web/src/screens/Bitacora.tsx`, add `arbol: 'Árbol de decisión',` to `EVENT`. Then export the
contract and generate its types:

Run: `cd apps/api && python -m centinela_api.contrato && cd ../web && npm run contract`
Expected: `apps/web/src/api/openapi.json` and `apps/web/src/api/schema.generated.ts` change, with
`"arbol"` in `LogEvent.type` and the two new schemas.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd apps/api && pytest -q`, then `cd apps/web && npm run typecheck && npm test`
Expected: PASS. `tests/test_contrato.py` passes because the document was exported in Step 7.

- [ ] **Step 9: Run the schema on a scratch database**

Run: `psql "$DSN_ADMIN" -f apps/api/sql/01_esquema.sql && psql "$DSN_ADMIN" -f apps/api/sql/01_esquema.sql && cd apps/api && pytest -q -m integracion`
Expected: both runs of the file succeed, because every statement is `IF NOT EXISTS` or replaces its
constraint, and the integration tests pass or skip when `DSN_ADMIN` reaches no database.

- [ ] **Step 10: Commit**

```bash
git add apps/api/sql/01_esquema.sql apps/api/src/centinela_api/arboles.py apps/api/src/centinela_api/rechazos.py apps/api/src/centinela_api/agentes.py apps/api/src/centinela_api/alertas.py apps/api/src/centinela_api/modelos.py apps/api/src/centinela_api/routers/simulacion.py apps/api/src/centinela_api/routers/alertas.py apps/api/tests/corridas.py apps/api/tests/test_arboles.py apps/api/tests/test_avanzar.py apps/api/tests/test_ciclo_orquestado.py apps/web/src/api/openapi.json apps/web/src/api/schema.generated.ts apps/web/src/logEvent.ts apps/web/src/screens/Bitacora.tsx
git commit -q -F - <<'MSG'
`apps/api` now stores every version of the tree as a move replayed over the base, keeps each rejection the classifier targeted, and at the start of each day run lets Estratega's drafter grow the tree under a lock before the day walks the newest version, so an expansion is persisted only by the API and only after the validator passed it.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 7: The API lists the expansions and lets a person retire one

**Files:**
- Create: `apps/api/src/centinela_api/routers/arbol.py`
- Modify: `apps/api/src/centinela_api/main.py`, `apps/api/src/centinela_api/permisos.py`, `apps/api/src/centinela_api/modelos.py` (`RetireExpansion`)
- Create: `apps/api/tests/test_arbol.py`
- Modify: `apps/web/src/api/openapi.json`, `apps/web/src/api/schema.generated.ts` (regenerated)

**Interfaces:**
- Consumes: `arboles.versiones`, `arboles.expansiones`, `arboles.retirar` and its errors (Task 6).
- Produces: `GET /arbol/expansiones` → `list[TreeExpansion]`; `POST /arbol/expansiones/{id}/retiro`
  with `RetireExpansion(reason: str)` → `TreeExpansion`; `permisos.puede_retirar(persona) -> bool` (D3).

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/test_arbol.py`:

```python
# The endpoints of the tree's expansions: the list, newest first, and the retirement with each of
# its refusals, over a mocked store and connection.
import datetime as dt
from unittest.mock import ANY, MagicMock

import pytest
from fastapi.testclient import TestClient

from centinela_api import db
from centinela_api.auth import persona_actual
from centinela_api.main import app
from centinela_api.modelos import Persona, TreeExpansion
from centinela_api.routers import arbol as arbol_router

GERENTE = Persona(email="gerente@andina.test", name="Ana", role="gerente")
AUDITOR = Persona(email="auditoria@andina.test", name="Jorge", role="auditor")
EXPANSION = TreeExpansion(id="2", agent="estratega", simulated_date="2026-01-15", created_at="2026-10-04T12:00:00+00:00", description="Deja de proponer", evidence=[], status="active")


@pytest.fixture
def con(monkeypatch):
    monkeypatch.setattr(arbol_router.arboles, "versiones", lambda conn: [])
    monkeypatch.setattr(arbol_router.arboles, "expansiones", lambda filas, titulos: [EXPANSION])
    monkeypatch.setattr(arbol_router.alertas_repo, "listar", lambda conn, status: [])
    monkeypatch.setattr(arbol_router.simulacion, "dia_actual", lambda conn: dt.date(2026, 1, 15))

    def conexion():
        yield MagicMock()

    def como(persona):
        app.dependency_overrides[persona_actual] = lambda: persona
        return TestClient(app)

    app.dependency_overrides[db.obtener_conexion] = conexion
    yield como
    app.dependency_overrides.clear()


def test_la_lista_sirve_las_expansiones(con):
    assert con(AUDITOR).get("/arbol/expansiones").json()[0]["id"] == "2"


def test_retirar_devuelve_la_expansion_retirada(con, monkeypatch):
    retirar = MagicMock(return_value=EXPANSION.model_copy(update={"status": "retired", "retired_by": "Ana", "retire_reason": "No ayudó"}))
    monkeypatch.setattr(arbol_router.arboles, "retirar", retirar)
    respuesta = con(GERENTE).post("/arbol/expansiones/2/retiro", json={"reason": "No ayudó"})
    assert respuesta.status_code == 200 and respuesta.json()["status"] == "retired"
    retirar.assert_called_once_with(ANY, 2, "No ayudó", GERENTE, dt.date(2026, 1, 15), {})


@pytest.mark.parametrize(
    "persona, cuerpo, error, estado",
    [
        (AUDITOR, {"reason": "No ayudó"}, None, 403),
        (GERENTE, {"reason": "  "}, None, 422),
        (GERENTE, {"reason": "No ayudó"}, arbol_router.arboles.ExpansionDesconocida(2), 404),
        (GERENTE, {"reason": "No ayudó"}, arbol_router.arboles.YaRetirada(2), 409),
        (GERENTE, {"reason": "No ayudó"}, arbol_router.arboles.RetiroRechazado(["metric x has no L3 branch in detectar"]), 422),
    ],
    ids=["auditor", "no reason", "unknown", "already retired", "refused"],
)
def test_retirar_rechaza(con, monkeypatch, persona, cuerpo, error, estado):
    monkeypatch.setattr(arbol_router.arboles, "retirar", MagicMock(side_effect=error))
    assert con(persona).post("/arbol/expansiones/2/retiro", json=cuerpo).status_code == estado
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd apps/api && pytest -q tests/test_arbol.py`
Expected: FAIL with `ImportError: cannot import name 'arbol' from 'centinela_api.routers'`.

- [ ] **Step 3: Write the endpoints**

In `apps/api/src/centinela_api/modelos.py`, add after `TreeExpansion`:

```python
class RetireExpansion(Esquema):
    """Why a person retires an expansion of the decision tree."""
    reason: str = Field(..., max_length=500, description="Why the expansion is retired")
```

In `apps/api/src/centinela_api/permisos.py`, add after `puede_configurar` (its roles are D3):

```python
def puede_retirar(persona: Persona) -> bool:
    return persona.role in ("analista", "gerente")
```

Create `apps/api/src/centinela_api/routers/arbol.py`:

```python
import psycopg
from fastapi import APIRouter, Depends, HTTPException

from .. import alertas as alertas_repo
from .. import arboles, permisos, simulacion
from ..auth import persona_actual
from ..db import obtener_conexion
from ..modelos import Persona, RetireExpansion, TreeExpansion

router = APIRouter(tags=["tree"], dependencies=[Depends(persona_actual)])

SOLO_QUIEN_RETIRA = "Los cambios del árbol los retiran la analista o la gerencia"
SIN_MOTIVO = "Para retirar un cambio del árbol hace falta un motivo"


def _titulos(conn: psycopg.Connection) -> dict:
    return {alerta.id: alerta.title for alerta in alertas_repo.listar(conn, None)}


@router.get("/arbol/expansiones", response_model=list[TreeExpansion])
async def listar(conn: psycopg.Connection = Depends(obtener_conexion)) -> list[TreeExpansion]:
    return arboles.expansiones(arboles.versiones(conn), _titulos(conn))


@router.post("/arbol/expansiones/{id}/retiro", response_model=TreeExpansion)
async def retirar(
    id: int,
    retiro: RetireExpansion,
    persona: Persona = Depends(persona_actual),
    conn: psycopg.Connection = Depends(obtener_conexion),
) -> TreeExpansion:
    if not permisos.puede_retirar(persona):
        raise HTTPException(403, SOLO_QUIEN_RETIRA)
    if not retiro.reason.strip():
        raise HTTPException(422, SIN_MOTIVO)
    try:
        return arboles.retirar(conn, id, retiro.reason, persona, simulacion.dia_actual(conn), _titulos(conn))
    except arboles.ExpansionDesconocida as e:
        raise HTTPException(404, "No existe ese cambio del árbol") from e
    except arboles.YaRetirada as e:
        raise HTTPException(409, "Ese cambio del árbol ya está retirado") from e
    except arboles.RetiroRechazado as e:
        raise HTTPException(422, f"El árbol no admite ese retiro: {e}") from e
```

In `apps/api/src/centinela_api/main.py`, add `arbol` to the routers import and
`app.include_router(arbol.router)` after `app.include_router(configuracion.router)`.

- [ ] **Step 4: Export the contract and run the tests**

Run: `cd apps/api && python -m centinela_api.contrato && cd ../web && npm run contract && cd ../api && pytest -q`
Expected: PASS, `tests/test_arbol.py` and `tests/test_contrato.py` among them.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/centinela_api/routers/arbol.py apps/api/src/centinela_api/main.py apps/api/src/centinela_api/permisos.py apps/api/src/centinela_api/modelos.py apps/api/tests/test_arbol.py apps/web/src/api/openapi.json apps/web/src/api/schema.generated.ts
git commit -q -F - <<'MSG'
The API now lists the tree's expansions, newest first with the alerts that drafted them, and lets the analista or the gerencia retire one with a reason, which the validator checks before the retirement is written.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 8: `Configuración` lists the expansions and retires one

Load the `arena:design` skill before writing the screen.

**Files:**
- Modify: `apps/web/src/api/types.ts`, `apps/web/src/api/http-client.ts`, `apps/web/src/api/client.ts`
- Create: `apps/web/src/screens/Expansions.tsx`
- Modify: `apps/web/src/screens/Settings.tsx`

**Interfaces:**
- Consumes: `GET /arbol/expansiones`, `POST /arbol/expansiones/{id}/retiro` (Task 7);
  `src/screens/ReasonDialog.tsx:ReasonDialog()`.
- Produces: `listExpansions(): Promise<TreeExpansion[]>`,
  `retireExpansion(id: string, reason: string): Promise<TreeExpansion>`; the types
  `TreeExpansion`, `ExpansionEvidence`.

- [ ] **Step 1: Write the client**

In `apps/web/src/api/types.ts`, add after `Threshold`:

```ts
export type TreeExpansion = Schemas['TreeExpansion'];
export type ExpansionEvidence = Schemas['ExpansionEvidence'];
```

In `apps/web/src/api/http-client.ts`, add `TreeExpansion` to its type import and add after
`saveSettings`:

```ts
export async function listExpansions(): Promise<TreeExpansion[]> {
  return fetchJson<TreeExpansion[]>(`${API_BASE_URL}/arbol/expansiones`);
}

export async function retireExpansion(id: string, reason: string): Promise<TreeExpansion> {
  return fetchJson<TreeExpansion>(`${API_BASE_URL}/arbol/expansiones/${encodeURIComponent(id)}/retiro`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}
```

In `apps/web/src/api/client.ts`, add `listExpansions,` and `retireExpansion,` to the re-exported
names, in alphabetical order.

- [ ] **Step 2: Write the screen**

Create `apps/web/src/screens/Expansions.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArenaButton,
  ArenaErrorState,
  ArenaSkeleton,
  ArenaTable,
  ArenaTableCell,
  ArenaTableRow,
  ArenaTag,
  type ArenaTableColumn,
} from '@dravensoft/arena-react';
import { ApiError, listExpansions, retireExpansion } from '../api/client';
import type { Agent, TreeExpansion } from '../api/types';
import { fillSentence, formatShortDate } from '../format';
import { useSimulation } from '../state/Simulation';
import { ReasonDialog } from './ReasonDialog';

const AGENT: Record<Agent, string> = {
  vigia: 'Vigía',
  analista: 'Analista',
  estratega: 'Estratega',
  ejecutor: 'Ejecutor',
  chat: 'Chat',
};

const COLUMNS: ArenaTableColumn[] = [
  { header: 'Día de la operación', mono: true, width: 'calc(var(--sp-1) * 28)' },
  { header: 'Quién' },
  { header: 'Cambio' },
  { header: 'Alertas que lo sostienen' },
  { header: 'Estado' },
];

export function Expansions({ allowed }: { allowed: boolean }) {
  const { notify } = useSimulation();
  const navigate = useNavigate();
  const [expansions, setExpansions] = useState<TreeExpansion[] | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [retiring, setRetiring] = useState<TreeExpansion | null>(null);

  useEffect(() => {
    setFailure(null);
    listExpansions().then(setExpansions, (e: unknown) => {
      if (!(e instanceof ApiError && e.status === 401)) {
        setFailure(e instanceof Error ? e.message : 'No se pudieron cargar los cambios del árbol.');
      }
    });
  }, [attempt]);

  if (failure !== null) {
    return (
      <ArenaErrorState
        headingLevel="h2"
        title="No pudimos cargar los cambios del árbol"
        message={failure}
        retryLabel="Reintentar"
        onRetry={() => setAttempt((n) => n + 1)}
      />
    );
  }
  if (expansions === null) {
    return <ArenaSkeleton variant="text" lines={4} />;
  }

  const retire = async (reason: string) => {
    if (retiring === null) {
      return;
    }
    const retired = await retireExpansion(retiring.id, reason);
    setExpansions(expansions.map((e) => (e.id === retired.id ? retired : e)));
    setRetiring(null);
    notify({ tone: 'success', title: 'Cambio retirado', message: 'Aplica desde el próximo día.' });
  };

  return (
    <div className="arena-stack arena-stack--group">
      <p className="text-muted">
        Los cambios que los agentes hicieron a su parte del árbol de decisión, el más reciente primero. Cada uno aplica desde el
        día siguiente y puede retirarse; retirarlo no espera a «Guardar cambios».
      </p>
      <ArenaTable label="Cambios del árbol de decisión" columns={COLUMNS} empty="Los agentes aún no han cambiado el árbol.">
        {expansions.map((e) => (
          <ArenaTableRow key={e.id}>
            <ArenaTableCell>{e.simulatedDate ? formatShortDate(e.simulatedDate) : 'Sin día'}</ArenaTableCell>
            <ArenaTableCell>{AGENT[e.agent]}</ArenaTableCell>
            <ArenaTableCell>{e.description}</ArenaTableCell>
            <ArenaTableCell>
              <span className="arena-stack">
                {e.evidence.map((evidence) => (
                  <ArenaButton key={evidence.alertId} variant="ghost" onClick={() => navigate(`/alertas/${evidence.alertId}`)}>
                    {fillSentence(evidence.title.text, evidence.title.figures)}
                  </ArenaButton>
                ))}
              </span>
            </ArenaTableCell>
            <ArenaTableCell>
              {e.status === 'retired' ? (
                <span className="text-muted">
                  Retirado por {e.retiredBy ?? 'alguien'}: {e.retireReason}
                </span>
              ) : (
                <span className="arena-stack">
                  <ArenaTag>Activo</ArenaTag>
                  {allowed ? (
                    <ArenaButton variant="ghost" icon="ph-bold ph-arrow-counter-clockwise" onClick={() => setRetiring(e)}>
                      Retirar
                    </ArenaButton>
                  ) : null}
                </span>
              )}
            </ArenaTableCell>
          </ArenaTableRow>
        ))}
      </ArenaTable>
      <ReasonDialog
        open={retiring !== null}
        eyebrow="Árbol de decisión"
        title="Retirar este cambio"
        hint="El árbol vuelve a decidir como antes de este cambio desde el próximo día. Las alertas que lo sostuvieron no vuelven a contar."
        label="Por qué lo retiras"
        missing="Escribe por qué lo retiras"
        failure="No se pudo retirar el cambio. Inténtalo de nuevo."
        confirm="Retirar"
        variant="danger"
        icon="ph-bold ph-arrow-counter-clockwise"
        onClose={() => setRetiring(null)}
        onSend={retire}
      />
    </div>
  );
}
```

In `apps/web/src/screens/Settings.tsx`, import `{ Expansions } from './Expansions'` and add, as
the last tab inside `ArenaTabs`:

```tsx
        <ArenaTab value="tree" label="Árbol de decisión">
          <Expansions allowed={allowed} />
        </ArenaTab>
```

- [ ] **Step 3: Check the screen**

Run: `cd apps/web && npm run typecheck && npm test && npm run arena:audit`
Expected: the typecheck and the tests PASS, and the audit names no finding in
`src/screens/Expansions.tsx` or `src/screens/Settings.tsx`; the findings it reports in
`src/app.css` are there before this task and are not its own. Then run the person-run check of `apps/web/AGENTS.md` on `Configuración` → "Árbol
de decisión" at phone width, by keyboard, in both themes, against an API with one expansion
(Task 6's test data, or three rejections of one row on a scratch database).

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/api/types.ts apps/web/src/api/http-client.ts apps/web/src/api/client.ts apps/web/src/screens/Expansions.tsx apps/web/src/screens/Settings.tsx
git commit -q -F - <<'MSG'
`Configuración` now lists the changes the agents made to the decision tree, newest first with the alerts behind each, and lets the analista or the gerencia retire one with a reason that applies from the next day.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 9: The pages state how the tree grows, and the spec and this plan are deleted

**Files:**
- Modify: `packages/agents/arbol/AGENTS.md`, `packages/agents/AGENTS.md`, `packages/agents/skills/AGENTS.md`
- Modify: `apps/api/AGENTS.md`, `apps/web/AGENTS.md`, `evals/AGENTS.md`
- Modify: `docs/guide/chapters/decision-tree.md`
- Modify: `scripts/check/check-routes.ts` (budgets only, when the gate asks)
- Delete: `docs/superpowers/2026-10-03-tree-expansion.md`, `docs/superpowers/2026-10-04-tree-expansion-plan.md`

Read each file before editing it, and write every citation with the parameters the member declares.

- [ ] **Step 1: `packages/agents/arbol/AGENTS.md`**

1. In the opening paragraph, replace "What is decided, not built: a client's own version of the
   tree, its growth by self-expansion, the caps on that growth, and the impact formulas" with
   "What runs too: the three moves of self-expansion, their criteria and caps, and `Estratega`'s
   draft. What is decided, not built: the drafts of `Vigía` and `Analista`, the cap on approved
   KPIs, and the impact formulas".
2. In "Why each file exists", add the row
   `| crecimiento.yaml | the settings of growth: how many repetitions draft each agent's expansion, and the caps on a version's longest path and on the nodes of one stage, each with its fuente |`.
3. Replace the "Decided, not built" box under "The tree" with: "**A client's version of the tree
   is not a file**: `apps/api` keeps it as the moves of its expansions replayed over this base and
   hands it to each run, because no agent writes anywhere ([`../../../apps/api/AGENTS.md`](../../../apps/api/AGENTS.md#the-trees-versions)).
   `centinela_agents/graph.py:Compiler` caches a graph per version and content."
4. In the node table, add three rows after `sigue`:
   `| divide | on a split node only: the leaf it splits; its no leads back to that leaf and its si to a new leaf of the same agent and decision, and the validator reads every reference to the node as one to the leaf |`,
   `| retirado | the reason a node was retired; a retired node always takes no, and stays so the bitácora of past alerts still names it |`,
   `| hoja.excluye | on a proponer leaf of Estratega only: the action ids, act-<metric>-r<k>, of rows of skills/estratega/acciones.md the leaf does not offer |`
   (each code word in backticks).
5. In "The validator", add the family "a split node that does not lead back to its leaf on `no`
   or takes no new leaf of its kind on `si`; an `excluye` outside a `proponer` leaf of `Estratega`,
   or one that names no row of `skills/estratega/acciones.md`", change the coverage family to
   "a metric of `data/metricas.yaml` with no live L3 branch in `detectar`, one no retired node
   hides, …", and change the last family to "L0, an L1 node or a leaf of the base that differs from
   the base, reading every reference to a split node as one to its leaf, or an L1 node the base
   lacks".
6. Replace the section "How the tree grows" with:

```markdown
## How the tree grows

| What grows | By | Who | Bound | Before it takes effect |
|---|---|---|---|---|
| L2 and L3 | self-expansion | the stage's own agent, drafted in code | the registry, the laws, the validator, the caps | nothing; it is recorded, versioned and retirable |
| any level | a pull request against `base.yaml` | a person | the validator and `uv run pytest` | review |
| the registry | a new clause or policy section | a person, by pull request | the clause exists in its standard or in `data/policies/` | review |

**What never grows at runtime**: L0, L1, the registry, the kernel's language, the list of tools,
the closed decisions of each agent, and the dataset. Each bounds what does grow, and a bound that
moves with what it bounds is no bound.

- **An agent expands the tree only inside its own stage**, with leaves of its own label: `Vigía` in
  `detectar` and `medir`, `Analista` in `explicar`, `Estratega` in `proponer`, `Ejecutor` in
  `ejecutar`. `aprobar` and `cerrar` have no agent and grow by pull request only, because each stage
  has one owner and an agent that rewrites another's stage would decide what that one does.
  `conversar` holds L1 nodes alone, so `Chat` expands nothing.
- **An expansion rests only on what the tree already holds**: its `fundamento` is a registry entry,
  its operand a KPI of the catalogue or a declared state field, its threshold an `umbral`. An agent
  cannot introduce a standard, a policy section or a threshold, which is why only a person grows
  the registry. An expansion that needs a measure the catalogue lacks is refused.
- **No person approves an expansion before it runs**, because every path to an `Ejecutor` leaf
  still passes `aprobar.decision` and `ejecutar.vigente`, which the validator holds: an expansion
  changes which leaf decides and on what, never what reaches the world.
- **An expansion is drafted in code and is an output, never a write.**
  `centinela_agents/growth.py:grow(tree, grounds, growth, rejections, consumed)` returns each move
  with the version it yields; `apps/api` persists it, writes it to the `bitácora`, and lets a
  person retire it. Code drafts it, never a model, because the counted evidence fixes every field
  of the move, and a model would only add a way to break the criteria.

**An expansion is one of three moves**, `centinela_agents/expansion.py:Move`, which
`centinela_agents/expansion.py:apply_move(tree, move)` applies. A move never edits or deletes a
node in place, because an edit is a delete plus an add with no record that the old path existed.

| Move | What it does | Why it is safe |
|---|---|---|
| `dividir_hoja` | an L2 or L3 node of the agent's stage, carrying `divide`, takes the place of a leaf of the agent's label: the old leaf on `no`, a new leaf of the same agent and decision on `si`, and every reference to the leaf now names the node | the old behaviour survives on `no`, and the validator reads the references through the node, so L1 is unchanged |
| `agregar_rama` | new L3 nodes at the end of an L2 family of the agent's stage, and the new metric in the family's `en` list; a new family is a pull request, because `centinela_agents/schema.py:FAMILIES` is code | only the new metric's candidate reaches the new nodes |
| `retirar` | an L2 or L3 node gains `retirado`, with its reason, and always takes `no` | the node stays, so the `bitácora` of past alerts still names it |

**The fixed criteria.**
`centinela_agents/expansion.py:expansion_problems(parent, move, grounds, caps)` refuses a move
that breaks any row below, and nothing of a refused move is persisted:

| Criterion | Held by |
|---|---|
| the move is one of the three, inside the agent's stage, and each new leaf is of its label, taking a decision and a route a base leaf of that agent takes, so it keeps its tools | `centinela_agents/expansion.py:move_problems(parent, move, grounds)` |
| a new `umbral` names a `data/metricas.yaml` entry whose `fuente_umbral` quotes a document | `move_problems` |
| each new node's `fundamento`, atomicity, operand and `umbral`; every path to `Ejecutor` through `aprobar.decision` and `ejecutar.vigente`; L0 and L1 as the base holds them | `centinela_agents/validator.py:problems(data, grounds)`, on the version the move yields |
| the version's longest path and the nodes of each stage stay under the caps of `crecimiento.yaml` | `centinela_agents/expansion.py:cap_problems(tree, caps)` |
| the evidence reached its count | `centinela_agents/growth.py:grow(tree, grounds, growth, rejections, consumed)` |

A refused draft is dropped and logged at once, because a drafter handed the same evidence drafts
the same move.

**`Estratega` drafts a split when one action row keeps being rejected.** When the alerts of one
metric whose rejection the classifier sent to `propuesta` name the same row, `act-<metric>-r<k>`,
as many times as `crecimiento.yaml` sets for `estratega`, the drafter splits the leaf an alert of
that metric reaches with a node reading `estado.detection.metric`, which rests on
`iso31000.6.5.2`, and gives the new leaf that row in its `excluye`. A second row of the same metric
splits that new leaf, so the exclusions accumulate and retiring the second restores the first. An
alert counts once: the drafter skips every alert a version already names, so a retired expansion
is drafted again only when new rejections reach the count.

> **Decided, not built.** `Vigía`'s `agregar_rama` for an approved KPI no `detectar` node reads,
> which waits for approved KPIs and for an operator per threshold in their catalogue;
> `Analista`'s split for a hypothesis confirmed across alerts, which waits for a cause that records
> its hypothesis; and a count of an action type ending in `nota_manual`, which no alert reaches
> while `ejecutar.automatizable` lists every action type. The cap on the active approved KPIs per
> client waits for approved KPIs too.

**The caps are settings sized to the machine**, as the model is, because a walk and its skill must
fit the context of a 4 to 8 billion parameter model, and a tree no model can read is a tree no
agent uses.

**Each version records** its parent, the client, the move, the agent or the person, the alerts
that drafted it, the hash of L0 and L1, `centinela_agents/expansion.py:layer_hash(tree)`, and the
simulated and real dates; `apps/api` keeps it ([`../../../apps/api/AGENTS.md`](../../../apps/api/AGENTS.md#the-trees-versions)).
```

7. In "Adding to the tree", "A node or a predicate.", add: "A node a move may add rests on the
   same rules, and a move's own rule changes `centinela_agents/expansion.py:move_problems(parent, move, grounds)`
   and its planted case in `tests/test_expansion.py:PLANTED_MOVES`."

- [ ] **Step 2: `packages/agents/AGENTS.md`**

1. In the opening paragraph, replace "and self-expansion" in the decided list with "and the drafts
   of self-expansion other than `Estratega`'s", and add, before "Each section that states one":
   "Before each day run, the drafter of self-expansion grows the tree in code, and `apps/api`
   persists each version."
2. In "Why each file exists", add after `centinela_agents/day.py`:
   `| centinela_agents/expansion.py | the three moves of self-expansion, their criteria, the caps and the replay of a client's moves over the base |` and
   `| centinela_agents/growth.py | the drafter of self-expansion: Estratega's split from repeated rejections of one action row |`
   (paths in backticks).
3. In "`Estratega` proposes", add to the ceiling: "A leaf a split gave `excluye` offers no row it
   names; one that excludes every row of the metric proposes nothing and calls no model, so the
   alert reaches `revision_manual`."
4. In "The orchestrator", replace "The version of the tree comes through
   `centinela_agents/graph.py:Compiler`." with "The version of the tree is the one
   `centinela_agents/orchestrator.py:CentinelaOrchestrator.use_tree(tree)` last received: `run_day`
   walks it whatever nodes its context carries, and a decision resumes on the graph of the version
   the alert started on, `centinela_agents/orchestrator.py:CentinelaOrchestrator.graph_of(alert_id)`,
   because the checkpoint is that graph's."
5. In "The state of an alert", add the row
   `| arbol_version | start_alert, from the version run_day walks | apps/api, which stores it |`
   (code words in backticks) after the `alert_id` row.
6. Add after "### The day run":

```markdown
### The growth of a day

**Before each day run, `apps/api` hands the drafter the version in use, the rejections it stored
and the alerts earlier versions already used**, and
`centinela_agents/growth.py:grow(tree, grounds, growth, rejections, consumed)` returns each move it
drafted, with the version it yields or the problems that refused it. It writes nothing, because no
agent writes anywhere. How a move is written, checked and capped is
[`arbol/AGENTS.md`](./arbol/AGENTS.md#how-the-tree-grows).
```

7. In "What is not the orchestrator's", add "persists the tree's versions and the rejections"
   after "persists cost".

- [ ] **Step 3: `packages/agents/skills/AGENTS.md`**

In the "Decided, not built" box, replace "A pending spec adds a file per decision for `expandir`
and `proponer_kpi`, loaded only when the walk reaches that decision's leaf." with "A pending spec
adds a file for `proponer_kpi`, loaded only when the walk reaches that decision's leaf; an
expansion is drafted in code and loads none."

- [ ] **Step 4: `apps/api/AGENTS.md`**

1. In "Why each file exists": in the `sql/01_esquema.sql` row add `api.arbol_versiones` and
   `api.rechazos` to the tables and `arbol_version` to what `api.alertas` holds; add the rows
   `| src/centinela_api/arboles.py | the tree's versions: the store, the replay over a new base, the growth of a day and the retirement of an expansion |` and
   `| src/centinela_api/rechazos.py | records each rejection the classifier targeted, with its metric and the actions it rejected, and lists them as evidence |`;
   add `arbol` to the routers; add `tests/test_arboles.py` and `tests/test_arbol.py` to the tests
   that mock the database.
2. Add two rows to the endpoints table, after `PUT /configuracion`:
   `| GET | /arbol/expansiones | the expansions of the tree, newest first, as TreeExpansion: the agent, the change in Spanish, the alerts behind it and whether it was retired | | listExpansions |` and
   `| POST | /arbol/expansiones/{id}/retiro | retires an expansion with a RetireExpansion reason and returns it | 403 unless analista or gerente; 404 for an unknown expansion; 409 for one already retired; 422 for a blank reason or one the validator refuses | retireExpansion |`
   (code words in backticks).
3. In "The agents run in this process", add to the `avanzar` bullet: "Before the run it takes the
   newest version of the tree from `src/centinela_api/arboles.py:del_dia(conn, dia)` and hands it
   to `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.use_tree(tree)`, and
   `_registrar` stores each alert's `arbol_version`."
4. Add after "The settings":

```markdown
## The tree's versions

**`api.arbol_versiones` holds every version of the client's tree as the move that made it**, keyed
by the client, `src/centinela_api/arboles.py:CLIENTE`, each with its parent, the agent or the
person, the alerts that drafted it, the base's `version` and hash, the hash of L0 and L1 and the
tree it yields. A version's id is the `Tree.version` the run walks and each alert stores.

- **A merged base replays the client's moves.** `src/centinela_api/arboles.py:vigente(conn, grounds, growth, dia)`
  returns the newest version while the base it was built on is the base in the tree; otherwise it
  replays every move in order over the new base, writes a `base` row, and logs each move the new
  base refuses. Who merged a base is in the commit log, not in the row.
- **The tree grows at the start of each day run.** `src/centinela_api/arboles.py:del_dia(conn, dia)`
  takes an advisory lock, reads the newest version, hands the drafter the rejections of
  `api.rechazos` and the alerts earlier versions name, writes each move that passed as an
  `expansion` row with an `arbol` row of the `bitácora` under its agent, logs each refused one,
  and returns the newest version. A failure of the drafter is logged and the day runs on the
  version in force.
- **`api.rechazos` keeps each rejection the classifier targeted**, with the alert's metric, the
  ids of the actions it rejected and the reason, written by the decision route after the resume;
  a rejection recorded with no paused graph has no target and keeps nothing.
- **A person retires an expansion**, `src/centinela_api/arboles.py:retirar(conn, id, motivo, persona, dia, titulos)`:
  under the same lock, the retirement of the expansion's first node passes the validator, then a
  `retiro` row and an `arbol` row of the `bitácora` under the person are written. It applies from
  the next day run; an alert already paused keeps the version it started on. The roles are
  `src/centinela_api/permisos.py:puede_retirar(persona)`'s, because a retirement changes what the
  agents decide, as a setting does.
```

5. In the `bitácora` type table, add `| arbol | the growth of a day, under the agent whose move it is, and a retirement, under the person |`.
6. Replace the "Decided, not built" box under "The clock" with: "> **Decided, not built.** The API
   hands the day run the rejection reasons kept for each metric, each with the target the
   orchestrator classified it to. `api.rechazos` keeps them, and `avanzar` hands none."

- [ ] **Step 5: `apps/web/AGENTS.md`, `evals/AGENTS.md`, the guide**

1. In `apps/web/AGENTS.md`, change the settings bullet's first sentence to: "**The settings screen
   has one save action for all its tabs but the tree's.** A change in any other tab is a draft
   until "Guardar cambios", so no tab saves half a configuration; the tab "Árbol de decisión",
   `src/screens/Expansions.tsx:Expansions({ allowed })`, retires an expansion at once, through
   `src/screens/ReasonDialog.tsx:ReasonDialog()`, because a retirement is a decision with its
   reason, not a setting."
2. In `evals/AGENTS.md`, add to the orchestrator's list in "What checks behaviour"
   `[../packages/agents/tests/test_expansion.py](../packages/agents/tests/test_expansion.py)` and
   `[../packages/agents/tests/test_growth.py](../packages/agents/tests/test_growth.py)` (as links,
   like the others), and append to the orchestrator row of the cases table: "; an expansion outside
   its agent's stage, a `fundamento` absent from the registry, a move that bypasses `aprobar` and a
   change to an L1 node (each refused); a split leaf whose predicate is false (the output the
   unsplit tree produced); evidence below its count (no expansion); a retired expansion (not drafted
   again before new evidence reaches its count)".
3. In `docs/guide/chapters/decision-tree.md`: drop ", and the part of its growth no level page
   states" from the opening; replace "The dashed arrows are self-expansion, decided and not built."
   with "The dashed arrows are self-expansion, which `Estratega` drafts today."; and replace the
   body of "How the tree grows" with: "How an expansion is drafted, checked, capped, recorded and
   retired is [the tree's page](../../../packages/agents/arbol/AGENTS.md), *How the tree grows*;
   where a client's versions live is [the API's page](../../../apps/api/AGENTS.md), *The tree's
   versions*." Keep every diagram and its `Draws:` caption.

- [ ] **Step 6: Delete the spec and this plan**

```bash
git rm -q docs/superpowers/2026-10-03-tree-expansion.md docs/superpowers/2026-10-04-tree-expansion-plan.md
```

Then `grep -rn "2026-10-03-tree-expansion\|tree-expansion-plan" --include=*.md --include=*.ts .`
must print nothing outside `node_modules`.

- [ ] **Step 7: Run every gate**

Run: `npm run check`
Expected: PASS. When `check:routes` reports a route over its budget or more than 15% under it,
set that row's number in `scripts/check/check-routes.ts:ROUTES` to the cost it reports rounded up
to the next hundred, keeping its reason; when `check:docs` reports a page past its cap, shorten the
page, never add an allowance. Run `npm run check` again until it passes, then
`cd packages/agents && uv run pytest -q`, `cd apps/api && pytest -q`, and
`git status --short` against `GENERATED.md`.

- [ ] **Step 8: Read every page the change touched**

Read end to end each page of Steps 1 to 5, for present tense and for a fact stated in two places,
and publish the guide's chapter with the steps of `docs/guide/AGENTS.md`.

- [ ] **Step 9: Commit**

```bash
git add packages/agents/arbol/AGENTS.md packages/agents/AGENTS.md packages/agents/skills/AGENTS.md apps/api/AGENTS.md apps/web/AGENTS.md evals/AGENTS.md docs/guide/chapters/decision-tree.md scripts/check/check-routes.ts
git commit -q -F - <<'MSG'
The pages now state how the tree grows as the code holds it: the three moves and their criteria on the tree's page, the growth of a day on the agents page, the versions and the retirement on the API's page and the tree's tab of `Configuración`, and the spec and its plan are deleted because the branch executes them.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```
