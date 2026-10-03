# Decision tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the routing spread over `packages/agents/AGENTS.md` with one decision tree that is data (`packages/agents/arbol/base.yaml`), validated by code, compiled to the LangGraph graph and walked by a deterministic interpreter, and add the decision `request_changes` from the API contract to the screen.

**Architecture:** A Python package, `packages/agents/centinela_agents/`, holds a schema (pydantic) for the tree, a validator that returns problem strings, the walk of the stage `detectar` (code, no LangGraph), and a compiler that turns the alert part of the tree into a LangGraph `StateGraph`: one graph node per leaf, per predicate node and per end, with the approval as an `interrupt()` inside the gate `aprobar.decision`. Leaves (the agents), the KPI reader (the kernel) and the rejection classifier are injected callables, so every routing case runs in pytest with stubs and no model, no database and no `apps/api`. Thresholds stay in `data/metricas.yaml`, in a new `umbrales` block keyed by the KPI column each one bounds.

**Tech Stack:** Python ≥ 3.12, uv, pydantic 2, PyYAML, LangGraph ≥ 1.0, pytest; TypeScript and React for the one screen change; Markdown and YAML for the pages.

**Spec:** `docs/superpowers/2026-10-03-decision-tree.md`. Read it whole before Task 2. It depends on `docs/superpowers/2026-10-03-normative-foundations.md` (spec 1) for the vocabulary, the laws and the registry; read its "Vocabulary" and "The laws (level L0)" sections. Specs 3 to 6 are not planned here; the "Decisions taken while planning" section says where they constrain this plan.

## Global Constraints

- Code is English; the words the data and the spec name keep their Spanish: the YAML keys of the tree exactly as the spec writes them (`version`, `leyes`, `nodos`, `id`, `fundamento`, `predicado`, `lee`, `op`, `umbral`, `valor`, `si`, `no`, `hoja`, `agente`, `decision`, `skill`, `sigue`), the stages, the agents, the metrics, the lifecycle states (`nueva`, `en análisis`, `propuesta`, `aprobada`, `rechazada`, `ejecutada`, `unida`).
- Text a person reads is Spanish (the fallback reasons, every string on screen). Error messages to `apps/api` are English.
- **Hand-written source carries no comments**, except one header of at most ten lines on a test file. Knowledge a name cannot carry goes in that header or on the level's page.
- **No code opens a database connection.** The KPI reader is a callable handed in; the tests hand a dict.
- **Every operator in YAML is quoted except `en` and `existe`** (`op: ">"`, `op: "="`), because PyYAML reads a bare `=` as the YAML value tag and refuses it.
- Documentation is English, present tense, and states each fact on one page. **No permanent page cites a spec or a plan**, by path, number or name; only `docs/superpowers/` files may.
- No literal count of anything that grows. Prose cites code as `path/to/file.py:member(parameters)`, never by line number, and never describes a file its writer has not read.
- Commit messages are short sentences that carry the reason, written through `git commit -q -F - <<'MSG'` when they contain a backtick, and end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. **No commit is made without asking the user first.**
- **The branch does not merge to `main` while the registry debt in `DOUBTS.md` stands**: spec 1 requires a person with the licensed texts to confirm every ISO entry before the first node cites one, and this plan writes those nodes. Task 11 asks.
- All Python commands run from `packages/agents/`; all web commands from `apps/web/`.

## Decisions taken while planning

Each one is written onto the page that owns it by Task 10, with its reason.

1. **The kernel is an interface, not a dependency** (decided with the user). Specs 4 and 5, which build the kernel, are pending. The validator receives a `Catalog` (the columns each KPI returns) and the interpreter a `KpiReader` callable `(metric, day) -> rows`. The base's `detectar` nodes read the columns of each metric's `v_*` view, which spec 5's parity makes the kernel's output, plus the columns no view has and the kernel must build (`caida_pts`, `margen_minimo_pct`, `concentracion_vencida_pct`, `aumento_pct`, `dias_habiles_sin_traslado`). The tests declare that catalogue in `tests/support.py:VIEW_CATALOG`; the gap is filed in `DOUBTS.md`, and spec 5 wires `kpi_catalogo` and `kpi_consultar`.
2. **A threshold is looked up by column** (decided with the user). Each entry of `metricas.yaml` gains `umbrales:`, keyed by the KPI column it bounds. A node keeps the spec's syntax, `umbral: saldo_vencido`, and the value compared is `umbrales[<metric of umbral>][<column of lee>]`. A value is a number, a boolean, `{ columna: <c> }` (a threshold another column of the same row holds, as `cupo_credito` or `margen_minimo_pct`), or `{ por: <c>, valores: {...} }` (one that varies by a dimension, as the class of a SKU). A compound `umbral_alerta` becomes one node per condition.
3. **The `ORQ-` cases are pytest tests with stub leaves** (decided with the user), in `packages/agents/tests/test_orq.py`, one test per case, each named for it. Cases that need `apps/api` (a second `/simulacion/avanzar`, the order of a day's alerts, a reason handed to the next run, three alerts of one cause) stay rows of `evals/AGENTS.md` and are not in that file.
4. **uv is the toolchain.** The machine has Python 3.13 without `ensurepip`, so `python -m venv` cannot install pip; uv builds the environment without it, and its `uv.lock` pins every version. `uv.lock` enters `GENERATED.md`.
5. **A predicate node is a graph node, not only the function of an edge.** The spec says "each predicate becomes the function of a conditional edge". The compiler gives each predicate node a graph node that evaluates it, records `[id, branch]` in the state's `camino`, applies the orchestrator's own write bound to that branch, and stores the target in `next_node`; a conditional edge reads `next_node`. Reasons: the path an alert walked is then in its state (spec 3 needs each step to name its node), the gate is the place the graph pauses, and a branch can carry a write (a merge, a return count) that an edge function cannot make.
6. **The approval is an `interrupt()` inside the gate `aprobar.decision`**, which every path to `Ejecutor` passes, and a resume is `graph.invoke(Command(resume=decision))`. `interrupt_before` with `update_state` is rejected, because `update_state` re-applies the writes of the node before the gate and is easy to get wrong across the `request_changes` loop.
7. **L1 is every node whose id names no metric family**, not one node per stage: the stage entries, the gates, the capped returns, and the nodes of `explicar`, `proponer`, `aprobar` and `ejecutar`. They are the same for every metric and must never move by self-expansion. L2 is `<stage>.<family>`, L3 is `<stage>.<family>.<...>`. `cerrar` has no node: it is the set of `fin.*` ends, which `apps/api` closes. `medir` has no node in the base, because its only decision, `proponer_kpi`, has no leaf in it.
8. **The ends are a closed list in code**, `centinela_agents/schema.py:ENDS`, each with what the interpreter does on reaching it. A `si`, `no` or `sigue` naming any other `fin.*` is refused.
9. **The orchestrator's own writes are bound to L1 node ids**, in `centinela_agents/graph.py:effects(node_id, branch, state)`, because L1 changes only by pull request: absorbing a smaller alert, dropping a `same_cause_as`, counting a return to `Analista`, counting a `request_changes`.
10. **`ejecutar.vigente` reads a derived state field, `estado.detection.vigente`.** On read, the interpreter re-reads the KPI row of the alert's entity on the simulated day of the decision and re-applies every `detectar` KPI node the detection passed on `si`, with the same `umbral`. No row for the entity is "no longer holds".
11. **The validator refuses a KPI read outside `detectar`**, a rule the spec does not list: the alert graph reads its measure only through `ejecutar.vigente`, and the interpreter has no row to compare a KPI node against there.
12. **The day run's order, the retry of a model call and the token cap are not built here.** They decide how a step runs, they need the model layer and `apps/api`, and they stay on `packages/agents/AGENTS.md` as settings. The fallback of a failed step is built: it writes a value, and the tree routes it.
13. **The interpreter refuses a resume** with no recorded decision id, an unknown kind, a reject or `request_changes` with no reason, or a second `request_changes`, in `centinela_agents/graph.py:resume(graph, alert_id, decision)`, so the graph never passes the gate on a decision `apps/api` did not record. `apps/api` checks the same before calling it.

## Today's "Nodes and edges", row by row

Acceptance requires this checklist. Each row of the table in `packages/agents/AGENTS.md` maps to a node, a leaf, an end, or a setting of the interpreter; Task 8's tests name the row they prove.

- [ ] start → `titular`, always, proposes `nueva` → the walk of `detectar` reaches the leaf `hoja.vigia.titular`; `centinela_agents/graph.py:start_alert(...)` proposes `nueva`.
- [ ] `titular` → `analizar`, always; title fallback → leaf `hoja.vigia.titular`, `sigue: hoja.analista.explicar`; the fallback of `vigia`/`titular` writes the metric's `descripcion` and the entity; entering an `analista` leaf from `nueva` proposes `en análisis`.
- [ ] `analizar` → `unir` → `explicar.misma_causa` (`estado.same_cause_as`, `existe`) then `explicar.destino_analizado` (`estado.same_cause_as.status`, `en`, `[en análisis, propuesta]`) `si` → `fin.unida`. "That is not this one": `start_alert` removes the alert's own id from `earlier_alerts`, so a self-reference has no status and is dropped below.
- [ ] `analizar` → `absorber` → `explicar.destino_nuevo` (`estado.same_cause_as.status`, `=`, `nueva`) `si`; its effect adds the named alert to `merged_alerts` and proposes `unida` for it.
- [ ] `analizar` → `proponer` otherwise; a `same_cause_as` failing both checks is dropped and logged → `explicar.destino_nuevo` `no` (effect: `same_cause_as` cleared, an `events` entry `same_cause_dropped`), and `explicar.misma_causa` `no`; both reach `explicar.con_evidencia` (`estado.cause.kind`, `=`, `identified`) `si` → `hoja.estratega.proponer`.
- [ ] `analizar` → `revision_manual` when the step fails → the fallback of `analista`/`explicar` writes `no_evidence` with the reason of its failure; `explicar.con_evidencia` `no` → `hoja.estratega.revision_manual`.
- [ ] `unir` → end, proposes `unida` → `fin.unida` writes `merged_into` and proposes `unida`.
- [ ] `absorber` → `proponer`; when the day run reaches the named alert it is `unida` and its graph does not run → the effect of `explicar.destino_nuevo` `si`; skipping the named alert's graph is the day run's, a setting not built here (decision 12).
- [ ] `proponer` → `analizar` when `insufficient_cause` and `analyst_returns` is 0 → `proponer.causa_insuficiente` (`existe`) `si` → `proponer.retorno_disponible` (`estado.analyst_returns`, `=`, 0) `si` → `hoja.analista.explicar`; its effect counts the return.
- [ ] `proponer` → `revision_manual` when `insufficient_cause` and `analyst_returns` is 1, or the step fails → `proponer.retorno_disponible` `no`; a failed step's fallback writes no actions, and `proponer.con_acciones` (`estado.actions`, `existe`) `no` → `hoja.estratega.revision_manual`.
- [ ] `proponer` → `esperar_decision` otherwise, proposes `propuesta` → `proponer.con_acciones` `si` → `aprobar.decision`; entering the gate proposes `propuesta` once. "One to three actions whose type is in the metric's rows" is the output schema of `Estratega`'s leaf, not a route.
- [ ] `revision_manual` → `esperar_decision`, always → leaf `hoja.estratega.revision_manual`, `sigue: aprobar.decision`.
- [ ] `esperar_decision` → itself on a resume with no recorded decision id → a setting: `resume` raises `ResumeRefused`, and the graph stays paused at the gate.
- [ ] `esperar_decision` → `ejecutar` on `approve` or `edit`; `edit`'s `parameters` replace the action's → gate `aprobar.decision` (`estado.decision.kind`, `en`, `[approve, edit]`) `si` → `ejecutar.vigente` → `ejecutar.automatizable` → `hoja.ejecutor.ejecutar`; `centinela_agents/state.py:approved_action(state)` applies the edit.
- [ ] `esperar_decision` → `clasificar_rechazo` on `reject` → `aprobar.decision` `no` → `aprobar.recargar` (`=`, `request_changes`) `no` → `fin.rechazada`.
- [ ] `clasificar_rechazo` → end; a failed classifier targets `ninguno` → `fin.rechazada` runs the injected classifier; an exception or a target outside the closed list is `ninguno`.
- [ ] `ejecutar` → end, `ExecutedAction`, proposes `ejecutada` → `ejecutar.resultado` (`estado.executed_action`, `existe`) `si` → `fin.ejecutada`.
- [ ] `ejecutar` → end when the step fails; the alert stays `aprobada` → the fallback writes no executed action; `ejecutar.resultado` `no` → `fin.fallo_ejecucion`. A later attempt is a new run `apps/api` starts, which does not exist yet; this plan builds none.

New in the tree: `aprobar.recargar` `si` → `aprobar.recarga_disponible` (`estado.proposal_returns`, `=`, 0) `si` → `hoja.estratega.proponer`, `no` → `fin.recarga_agotada`; `ejecutar.vigente` `no` → `fin.ya_no_aplica`; `ejecutar.automatizable` `no` → `hoja.ejecutor.nota_manual`.

## Review Focus

1. **YAML 1.1 reads the key `no:` as the boolean `False`.** PyYAML's `safe_load` turns every `no:` branch into a `False` key, and the schema then sees a node with no `no`. Expected: `no` stays the string `"no"`, `true`/`false` stay booleans. Task 2 pins it with `test_a_no_key_stays_a_string_and_true_stays_a_boolean`.
2. **A `request_changes` reuses the old decision.** After the re-proposal the walk reaches `aprobar.decision` again; if the decision were still in the state it would pass the gate with no person. Expected: it pauses again, a second `request_changes` is refused, and an approval after it executes. Task 8 pins it with `test_orq_request_changes_reproposes_once_and_refuses_a_second`.
3. **A KPI value is null.** A customer with no open invoice has `max_dias_vencido` null, a class C SKU has no coverage threshold, a SKU with no demand has `cobertura_dias` null. Expected: no alert, no exception. Task 3 pins `compare` with null, Task 6 pins the walk with `test_a_null_value_or_a_class_without_threshold_fires_nothing`.
4. **The entity has no KPI row on the day of execution** (the invoice was paid, the order arrived). Expected: `fin.ya_no_aplica`, `Ejecutor` not called, no exception. Task 6 pins `still_breaks`, Task 8 pins the graph with `test_orq_an_action_whose_kpi_no_longer_breaks_ends_at_ya_no_aplica`.
5. **A leaf of the tree has no function handed to the compiler.** Expected: compiling refuses with the leaf named, never a `KeyError` in the middle of an alert's walk. Task 7 pins it with `test_a_leaf_with_no_function_is_refused_at_compile`.

## File structure

| Path | Responsibility | Task |
|---|---|---|
| `packages/agents/pyproject.toml`, `packages/agents/uv.lock` | the package and its pinned dependencies | 2 |
| `packages/agents/centinela_agents/__init__.py` | empty | 2 |
| `packages/agents/centinela_agents/yaml_loader.py` | YAML that keeps `no` a string | 2 |
| `packages/agents/centinela_agents/schema.py` | the tree's models, the closed lists, levels, stages, reachability | 2 |
| `packages/agents/centinela_agents/metrics.py` | `metricas.yaml`: descriptions and `umbrales` | 3 |
| `packages/agents/centinela_agents/catalog.py` | the KPI catalogue handed in, and the threshold lookup | 3 |
| `packages/agents/centinela_agents/predicate.py` | comparing one operand with one value | 3 |
| `packages/agents/centinela_agents/state.py` | the alert's state, the fields a node may read, the approved action | 4 |
| `packages/agents/arbol/base.yaml` | the base tree | 4 |
| `packages/agents/centinela_agents/validator.py` | the validator and `load_base` | 5 |
| `packages/agents/centinela_agents/walk.py` | the walk of `detectar`, derived fields, `still_breaks` | 6 |
| `packages/agents/centinela_agents/failures.py` | the failures a leaf raises | 7 |
| `packages/agents/centinela_agents/graph.py` | the compiler, the interpreter's writes, start and resume | 7 |
| `packages/agents/tests/support.py` | the catalogue fixture, the base, stub leaves, the stub reader | 5, 7 |
| `packages/agents/tests/test_*.py` | one file per module, and `test_orq.py` for the cases | 2 to 8 |
| `data/metricas.yaml`, `packages/agents/arbol/fundamentos.yaml` | `umbrales`; the policy entries the base cites | 3, 4 |
| `apps/web/src/api/types.ts`, `apps/web/src/api/client.ts`, `apps/web/src/screens/ProposedActions.tsx`, `apps/web/src/screens/ReasonDialog.tsx` | `request_changes` | 9 |
| the pages | listed in Tasks 10 and 11 | 10, 11 |

---

### Task 1: Rename the spec now that its plan exists

**Files:**
- Rename: `docs/superpowers/2026-10-03-decision-tree-pending-2.md` → `docs/superpowers/2026-10-03-decision-tree.md`

**Interfaces:**
- Consumes: this plan, at `docs/superpowers/2026-10-03-decision-tree-plan.md`.
- Produces: the spec at the path this plan's header names.

`docs_guide.md` §3: a spec written ahead of its plan carries a `-pending-N` suffix until the plan exists.

- [ ] **Step 1: Find every citation of the old path**

Run: `grep -rn "decision-tree-pending-2" --include='*.md' . | grep -v node_modules`
Expected: only lines of this plan. Any other hit is a file to update in Step 3.

- [ ] **Step 2: Rename**

Run: `git mv docs/superpowers/2026-10-03-decision-tree-pending-2.md docs/superpowers/2026-10-03-decision-tree.md`

- [ ] **Step 3: Update the spec's status line**

In `docs/superpowers/2026-10-03-decision-tree.md`, replace

```
**Status:** pending its plan. **Depends on:**
```

with

```
**Status:** planned in `2026-10-03-decision-tree-plan.md`. **Depends on:**
```

- [ ] **Step 4: Point this plan's header at the new path**

In this plan's `**Spec:**` line, delete the parenthesis `(at ... until Task 1 renames it)`.

- [ ] **Step 5: Verify**

Run: `git status --short`
Expected: `R  docs/superpowers/2026-10-03-decision-tree-pending-2.md -> docs/superpowers/2026-10-03-decision-tree.md`, `M` on it, and `?? docs/superpowers/2026-10-03-decision-tree-plan.md`. Nothing else.

- [ ] **Step 6: Ask the user, then commit**

```bash
git add docs/superpowers/
git commit -q -F - <<'MSG'
Plan the decision tree and rename its spec, so its execution starts from a fixed mapping of every route

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 2: The Python package, the YAML loader and the tree's schema

**Files:**
- Create: `packages/agents/pyproject.toml`, `packages/agents/centinela_agents/__init__.py` (empty), `packages/agents/centinela_agents/yaml_loader.py`, `packages/agents/centinela_agents/schema.py`, `packages/agents/tests/test_schema.py`
- Generated: `packages/agents/uv.lock`
- Modify: `GENERATED.md`, table "What writes today"

**Interfaces:**
- Produces:
  - `yaml_loader.parse_yaml(text: str) -> Any`, `yaml_loader.load_yaml(path: Path) -> Any`
  - `schema.STAGES`, `schema.FAMILIES`, `schema.AGENT_DECISIONS: dict[str, tuple[str, ...]]`, `schema.AGENT_STAGE: dict[str, str]`, `schema.ENDS: frozenset[str]`, `schema.ROOT = "detectar.raiz"`, `schema.GATE = "aprobar.decision"`, `schema.VIGENTE = "ejecutar.vigente"`
  - models `Predicate(lee, op, umbral, valor)`, `Leaf(agente, decision, skill)`, `Node(id, fundamento, predicado, si, no, hoja, sigue)`, `Law(id, fundamento)`, `Tree(version, leyes, nodos)`, all frozen, unknown keys refused
  - `index(tree) -> dict[str, Node]`, `branches(node) -> list[tuple[str, str]]`, `level(node_id) -> int`, `stage_of(target, nodes) -> str`, `reachable(nodes, starts, without=frozenset()) -> set[str]`

- [ ] **Step 1: Check uv**

Run: `uv --version`
Expected: a version. If the command is not found, stop and ask the user to run `! curl -LsSf https://astral.sh/uv/install.sh | sh` in this session, then open a new shell.

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "centinela-agents"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "langgraph>=1.0",
  "pydantic>=2.8",
  "pyyaml>=6.0",
]

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["centinela_agents"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Create `centinela_agents/__init__.py` empty. Run: `uv sync`
Expected: `.venv/` created, `uv.lock` written, the packages installed. Run `uv run python -c "import langgraph, pydantic, yaml; print('ok')"`; expected `ok`.

- [ ] **Step 3: Write the failing tests**

`packages/agents/tests/test_schema.py`:

```python
import pytest
from pydantic import ValidationError

from centinela_agents.schema import Tree, branches, index, level, reachable, stage_of
from centinela_agents.yaml_loader import parse_yaml

TREE = {
    "version": 1,
    "leyes": [{"id": "todo_paso_en_bitacora", "fundamento": "iso31000.6.7"}],
    "nodos": [
        {"id": "hoja.vigia.titular", "hoja": {"agente": "vigia", "decision": "titular", "skill": "vigia/contrato.md"}, "sigue": "explicar.x"},
        {"id": "explicar.x", "fundamento": "iso9001.10.2.1.b.3", "predicado": {"lee": "estado.same_cause_as", "op": "existe"}, "si": "fin.unida", "no": "fin.rechazada"},
    ],
}


def test_a_no_key_stays_a_string_and_true_stays_a_boolean():
    assert parse_yaml("si: a\nno: b\nvalor: true\nyes: c\nop: \"=\"\n") == {"si": "a", "no": "b", "valor": True, "yes": "c", "op": "="}


def test_a_tree_parses_into_nodes_leaves_and_laws():
    tree = Tree.model_validate(TREE)
    nodes = index(tree)
    assert nodes["explicar.x"].no == "fin.rechazada"
    assert branches(nodes["hoja.vigia.titular"]) == [("sigue", "explicar.x")]
    assert branches(nodes["explicar.x"]) == [("si", "fin.unida"), ("no", "fin.rechazada")]
    assert tree.leyes[0].fundamento == "iso31000.6.7"


def test_an_unknown_key_fails_the_schema():
    broken = {**TREE, "nodos": [{**TREE["nodos"][1], "color": "rojo"}]}
    with pytest.raises(ValidationError):
        Tree.model_validate(broken)


def test_an_operator_outside_the_closed_list_fails_the_schema():
    node = {**TREE["nodos"][1], "predicado": {"lee": "estado.same_cause_as", "op": "and"}}
    with pytest.raises(ValidationError):
        Tree.model_validate({**TREE, "nodos": [node]})


@pytest.mark.parametrize(
    "node_id, expected",
    [
        ("detectar.raiz", 1),
        ("aprobar.decision", 1),
        ("hoja.vigia.titular", 1),
        ("detectar.cartera", 2),
        ("detectar.cartera.saldo_vencido", 3),
        ("detectar.cartera.saldo_vencido.dias", 3),
    ],
)
def test_the_level_is_read_from_the_family_in_the_id(node_id, expected):
    assert level(node_id) == expected


def test_a_leaf_takes_its_agents_stage_and_an_end_is_cerrar():
    nodes = index(Tree.model_validate(TREE))
    assert stage_of("hoja.vigia.titular", nodes) == "detectar"
    assert stage_of("explicar.x", nodes) == "explicar"
    assert stage_of("fin.unida", nodes) == "cerrar"


def test_reachable_skips_the_nodes_it_is_told_to_avoid():
    nodes = index(Tree.model_validate(TREE))
    assert reachable(nodes, ["hoja.vigia.titular"]) == {"hoja.vigia.titular", "explicar.x", "fin.unida", "fin.rechazada"}
    assert reachable(nodes, ["hoja.vigia.titular"], without=frozenset({"explicar.x"})) == {"hoja.vigia.titular"}
```

- [ ] **Step 4: Run them to see them fail**

Run: `uv run pytest tests/test_schema.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'centinela_agents.schema'`.

- [ ] **Step 5: Write `yaml_loader.py`**

```python
import re
from pathlib import Path
from typing import Any

import yaml

BOOL_TAG = "tag:yaml.org,2002:bool"


class StrictBoolLoader(yaml.SafeLoader):
    pass


StrictBoolLoader.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers if tag != BOOL_TAG]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
StrictBoolLoader.add_implicit_resolver(BOOL_TAG, re.compile(r"^(?:true|false)$"), list("tf"))


def parse_yaml(text: str) -> Any:
    return yaml.load(text, Loader=StrictBoolLoader)


def load_yaml(path: Path) -> Any:
    return parse_yaml(path.read_text(encoding="utf-8"))
```

- [ ] **Step 6: Write `schema.py`**

```python
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
```

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/test_schema.py -v`
Expected: all pass.

- [ ] **Step 8: Record `uv.lock` in `GENERATED.md`**

In the table "What writes today", add this row after the `arena-to-prod` row:

```
| `uv sync` and `uv lock`, run in `packages/agents` | `packages/agents/uv.lock`, from `packages/agents/pyproject.toml` | uv writes the file whole and owns its format; the defect is in `pyproject.toml`, and `uv lock` writes the file again |
```

- [ ] **Step 9: Check what the run wrote**

Run: `git status --short`
Expected: `?? packages/agents/pyproject.toml`, `?? packages/agents/uv.lock`, `?? packages/agents/centinela_agents/`, `?? packages/agents/tests/`, ` M GENERATED.md`. `.venv/` and `__pycache__/` do not appear, because `.gitignore` covers them; if they do, stop.

- [ ] **Step 10: Ask the user, then commit**

```bash
git add packages/agents/pyproject.toml packages/agents/uv.lock packages/agents/centinela_agents packages/agents/tests GENERATED.md
git commit -q -F - <<'MSG'
Give the decision tree a schema that refuses unknown keys and operators, and read its YAML so that a `no` branch stays a string

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 3: Thresholds by column, the catalogue and the predicate

**Files:**
- Modify: `data/metricas.yaml` (one `umbrales:` line per metric), `data/AGENTS.md` (the `metricas.yaml` row and one rule)
- Create: `packages/agents/centinela_agents/metrics.py`, `packages/agents/centinela_agents/catalog.py`, `packages/agents/centinela_agents/predicate.py`, `packages/agents/tests/test_predicate.py`

**Interfaces:**
- Consumes: `yaml_loader.load_yaml`.
- Produces:
  - `metrics.Metrics(descriptions: Mapping[str, str], thresholds: Mapping[str, Mapping[str, Any]])` with property `names: tuple[str, ...]`; `metrics.load_metrics(path: Path) -> Metrics`; `metrics.threshold_shape_problem(spec: Any) -> str | None`
  - `catalog.Kpi(entity: tuple[str, ...], columns: frozenset[str], descriptive: bool = False, thresholds: Mapping[str, Any] = {})`; `catalog.Catalog(kpis: Mapping[str, Kpi])`; `catalog.KpiReader = Callable[[str, str], list[Mapping[str, Any]]]`; `catalog.thresholds_named(name, metrics, catalog) -> Mapping[str, Any] | None`
  - `predicate.KPI_PATH`, `predicate.STATE_PATH` (compiled regexes), `predicate.is_kpi(lee) -> bool`, `predicate.kpi_column(lee) -> tuple[str, str]`, `predicate.compare(op, left, right) -> bool`, `predicate.threshold_value(spec, row) -> Any`

- [ ] **Step 1: Add `umbrales` to `data/metricas.yaml`**

Insert one line directly after each metric's `umbral_alerta:` line, indented four spaces like it:

| Metric | Line |
|---|---|
| `margen_pct` | `    umbrales: { caida_pts: 3, margen_pct: { columna: margen_minimo_pct } }` |
| `saldo_vencido` | `    umbrales: { max_dias_vencido: 15, saldo_abierto: { columna: cupo_credito } }` |
| `concentracion_vencida_pct` | `    umbrales: { concentracion_vencida_pct: 10 }` |
| `dias_pago_prom` | `    umbrales: { aumento_pct: 50 }` |
| `cobertura_dias` | `    umbrales: { cobertura_dias: { por: clase_abc, valores: { A: 10, B: 7 } } }` |
| `variacion_costo_pct` | `    umbrales: { variacion_pct: 5, dias_habiles_sin_traslado: 10 }` |
| `dias_retraso` | `    umbrales: { dias_retraso: 0, recibida: false }` |
| `descuento_en_exceso` | `    umbrales: { descuento_en_exceso: 0 }` |
| `margen_bruto_negativo` | `    umbrales: { margen_bruto: 0 }` |
| `veces_intervalo_habitual` | `    umbrales: { pedidos: 10, veces_intervalo_habitual: 3 }` |

Each value restates its `umbral_alerta` and nothing more: read each pair side by side before going on. The severity tier of `cobertura_dias` (critical under 5 days with pending orders) is not a firing threshold and gets no entry. Run: `grep -c '^    umbrales:' data/metricas.yaml` and `grep -oP '^  \K[a-z_]+(?=:)' data/metricas.yaml | wc -l`; expected: the same number.

- [ ] **Step 2: Write the rule into `data/AGENTS.md`**

In "Why each file exists", replace the `metricas.yaml` row's cell

```
the single definition of each metric: formula, view, dimensions, alert threshold, the policy section the threshold comes from, and how its pesos at risk are computed
```

with

```
the single definition of each metric: formula, view, dimensions, alert threshold as text (`umbral_alerta`) and per KPI column (`umbrales`), the policy section the threshold comes from, and how its pesos at risk are computed
```

In "Rules of this level", after the bullet that starts `- **Every threshold quotes a document.**`, add:

```
- **`umbrales` is the threshold a node of the decision tree applies, and `umbral_alerta` is the
  text a person reads.** Each entry of `umbrales` is keyed by the KPI column it bounds and holds a
  number, a boolean, `{ columna: <c> }` for a threshold another column of the same row holds, or
  `{ por: <c>, valores: {...} }` for one that varies by a dimension. A node names the metric in its
  `umbral` and supplies the operator, so a condition of `umbral_alerta` with two parts is two
  nodes. Both forms say the same thing, because the kit's text stays as delivered and a tree needs
  a value it can compare; a change to one is a change to both. *No gate holds this.*
```

- [ ] **Step 3: Write the failing tests**

`packages/agents/tests/test_predicate.py`:

```python
from pathlib import Path

import pytest

from centinela_agents.catalog import Catalog, Kpi, thresholds_named
from centinela_agents.metrics import load_metrics, threshold_shape_problem
from centinela_agents.predicate import compare, is_kpi, kpi_column, threshold_value

METRICAS = Path(__file__).resolve().parents[3] / "data" / "metricas.yaml"


@pytest.mark.parametrize(
    "op, left, right, expected",
    [
        (">", 16, 15, True),
        (">", 15, 15, False),
        (">=", 10, 10, True),
        ("<", 9.5, 10, True),
        ("<=", 11, 10, False),
        ("=", False, False, True),
        ("!=", "a", "b", True),
        ("en", "edit", ["approve", "edit"], True),
        ("en", None, ["approve", "edit"], False),
        ("existe", None, None, False),
        ("existe", [], None, False),
        ("existe", "A0", None, True),
    ],
)
def test_compare_applies_one_operator(op, left, right, expected):
    assert compare(op, left, right) is expected


@pytest.mark.parametrize("op", [">", ">=", "<", "<=", "=", "!="])
def test_a_null_on_either_side_is_false(op):
    assert compare(op, None, 10) is False
    assert compare(op, 10, None) is False


def test_a_threshold_is_a_value_a_column_or_a_value_by_dimension():
    row = {"cupo_credito": 5000, "clase_abc": "B"}
    assert threshold_value(15, row) == 15
    assert threshold_value({"columna": "cupo_credito"}, row) == 5000
    assert threshold_value({"por": "clase_abc", "valores": {"A": 10, "B": 7}}, row) == 7
    assert threshold_value({"por": "clase_abc", "valores": {"A": 10, "B": 7}}, {"clase_abc": "C"}) is None


def test_a_kpi_path_names_one_metric_and_one_column():
    assert is_kpi("kpi.saldo_vencido.max_dias_vencido")
    assert not is_kpi("estado.cause.kind")
    assert kpi_column("kpi.saldo_vencido.max_dias_vencido") == ("saldo_vencido", "max_dias_vencido")


def test_metricas_holds_a_threshold_per_column_for_every_metric():
    metrics = load_metrics(METRICAS)
    assert metrics.thresholds["saldo_vencido"] == {"max_dias_vencido": 15, "saldo_abierto": {"columna": "cupo_credito"}}
    assert metrics.thresholds["dias_retraso"]["recibida"] is False
    assert all(metrics.thresholds[name] for name in metrics.names)
    assert all(threshold_shape_problem(spec) is None for columns in metrics.thresholds.values() for spec in columns.values())


@pytest.mark.parametrize("spec", ["15", {"columna": 3}, {"por": "clase_abc"}, {"por": "c", "valores": {"A": "diez"}}])
def test_a_threshold_of_another_shape_is_a_problem(spec):
    assert threshold_shape_problem(spec) is not None


def test_an_umbral_names_a_metric_or_an_approved_kpi():
    metrics = load_metrics(METRICAS)
    catalog = Catalog({"retraso_habito": Kpi(("cliente_id",), frozenset({"cliente_id", "dias_sobre_habito"}), thresholds={"dias_sobre_habito": 0})})
    assert thresholds_named("saldo_vencido", metrics, catalog)["max_dias_vencido"] == 15
    assert thresholds_named("retraso_habito", metrics, catalog) == {"dias_sobre_habito": 0}
    assert thresholds_named("inventada", metrics, catalog) is None
```

- [ ] **Step 4: Run them to see them fail**

Run: `uv run pytest tests/test_predicate.py -v`
Expected: collection error, `No module named 'centinela_agents.catalog'`.

- [ ] **Step 5: Write `metrics.py`**

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .yaml_loader import load_yaml


@dataclass(frozen=True)
class Metrics:
    descriptions: Mapping[str, str]
    thresholds: Mapping[str, Mapping[str, Any]]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self.descriptions)


def load_metrics(path: Path) -> Metrics:
    entries = load_yaml(path)["metricas"]
    return Metrics(
        descriptions={name: entry["descripcion"] for name, entry in entries.items()},
        thresholds={name: entry.get("umbrales", {}) for name, entry in entries.items()},
    )


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def threshold_shape_problem(spec: Any) -> str | None:
    if isinstance(spec, bool) or is_number(spec):
        return None
    if isinstance(spec, dict) and set(spec) == {"columna"} and isinstance(spec["columna"], str):
        return None
    if (
        isinstance(spec, dict)
        and set(spec) == {"por", "valores"}
        and isinstance(spec["por"], str)
        and isinstance(spec["valores"], dict)
        and all(is_number(value) for value in spec["valores"].values())
    ):
        return None
    return f"is {spec!r}, which is no number, boolean, columna or por with valores"
```

- [ ] **Step 6: Write `catalog.py`**

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .metrics import Metrics

KpiReader = Callable[[str, str], list[Mapping[str, Any]]]


@dataclass(frozen=True)
class Kpi:
    entity: tuple[str, ...]
    columns: frozenset[str]
    descriptive: bool = False
    thresholds: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Catalog:
    kpis: Mapping[str, Kpi]


def thresholds_named(name: str, metrics: Metrics, catalog: Catalog) -> Mapping[str, Any] | None:
    if name in metrics.thresholds:
        return metrics.thresholds[name]
    kpi = catalog.kpis.get(name)
    return kpi.thresholds if kpi is not None and kpi.thresholds else None
```

- [ ] **Step 7: Write `predicate.py`**

```python
import operator
import re
from typing import Any, Mapping

KPI_PATH = re.compile(r"^kpi\.([a-z0-9_]+)\.([a-z0-9_]+)$")
STATE_PATH = re.compile(r"^estado(\.[a-z_]+)+$")
ORDER = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "!=": operator.ne,
}


def is_kpi(lee: str) -> bool:
    return KPI_PATH.match(lee) is not None


def kpi_column(lee: str) -> tuple[str, str]:
    match = KPI_PATH.match(lee)
    if match is None:
        raise ValueError(f"{lee} names no KPI column")
    return match.group(1), match.group(2)


def compare(op: str, left: Any, right: Any) -> bool:
    if op == "existe":
        return left is not None and left != [] and left != {}
    if op == "en":
        return left in right
    if left is None or right is None:
        return False
    return ORDER[op](left, right)


def threshold_value(spec: Any, row: Mapping[str, Any]) -> Any:
    if isinstance(spec, dict) and "columna" in spec:
        return row.get(spec["columna"])
    if isinstance(spec, dict) and "por" in spec:
        key = row.get(spec["por"])
        return None if key is None else spec["valores"].get(str(key))
    return spec
```

- [ ] **Step 8: Run the tests**

Run: `uv run pytest -v`
Expected: all pass.

- [ ] **Step 9: Ask the user, then commit**

```bash
git add data/metricas.yaml data/AGENTS.md packages/agents/centinela_agents packages/agents/tests
git commit -q -F - <<'MSG'
Write each metric's threshold per KPI column, so a node of the tree names its metric and never holds a literal threshold

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 4: The base tree, its policy `fundamentos`, and the fields it reads

**Files:**
- Modify: `packages/agents/arbol/fundamentos.yaml` (append entries)
- Create: `packages/agents/centinela_agents/state.py`, `packages/agents/arbol/base.yaml`, `packages/agents/tests/test_base.py`

**Interfaces:**
- Consumes: `schema.Tree`, `schema.index`, `yaml_loader.load_yaml`, `metrics.load_metrics`.
- Produces:
  - `state.DERIVED_FIELDS`, `state.STATE_FIELDS: frozenset[str]`
  - `state.AlertState` (TypedDict for LangGraph; `camino`, `transitions`, `failures`, `events` accumulate by `operator.add`)
  - `state.field_value(state, path) -> Any`, `state.approved_action(state) -> dict | None`
  - `arbol/base.yaml`, whose node ids later tasks name: `detectar.raiz`, `explicar.misma_causa`, `explicar.destino_analizado`, `explicar.destino_nuevo`, `explicar.con_evidencia`, `proponer.causa_insuficiente`, `proponer.retorno_disponible`, `proponer.con_acciones`, `aprobar.decision`, `aprobar.recargar`, `aprobar.recarga_disponible`, `ejecutar.vigente`, `ejecutar.automatizable`, `ejecutar.resultado`, and the leaves `hoja.vigia.titular`, `hoja.analista.explicar`, `hoja.estratega.proponer`, `hoja.estratega.revision_manual`, `hoja.ejecutor.ejecutar`, `hoja.ejecutor.nota_manual`

- [ ] **Step 1: Check each policy section against its PDF**

Run: `for f in data/policies/*.pdf; do pdftotext -layout "$f" - | grep -nE "^\s*[0-9]\. |POL-"; done`
Expected, among the lines: `FIN-POL-004` with `3. Cupo de crédito`, `4. Seguimiento y escalamiento`, `5. Señales de alerta temprana`; `COM-POL-002` with `2. Topes de descuento por segmento`, `4. Prohibiciones`; `OPE-POL-007` with `2. Cobertura mínima`, `3. Proveedores`, `4. Revisión de precios`. A title that differs is copied as the PDF writes it into Step 2.

- [ ] **Step 2: Append the entries the base cites to `fundamentos.yaml`**

At the end of the list, no comments:

```yaml
  - id: fin-pol-004.s3
    cita: "FIN-POL-004 §3, Cupo de crédito"
    funda: "the threshold that a customer's open balance stays within its cupo_credito"
  - id: fin-pol-004.s4
    cita: "FIN-POL-004 §4, Seguimiento y escalamiento"
    funda: "the threshold on the days an invoice is past due, and the tramos of escalation"
  - id: fin-pol-004.s5
    cita: "FIN-POL-004 §5, Señales de alerta temprana"
    funda: "the thresholds on a customer's share of the past-due receivables and on the rise of its days to pay"
  - id: com-pol-002.s2
    cita: "COM-POL-002 §2, Topes de descuento por segmento"
    funda: "the threshold that a discount stays within its segment's cap"
  - id: com-pol-002.s4
    cita: "COM-POL-002 §4, Prohibiciones"
    funda: "the threshold that no line is sold below cost"
  - id: ope-pol-007.s2
    cita: "OPE-POL-007 §2, Cobertura mínima"
    funda: "the thresholds on the days of stock a class A or B SKU covers"
  - id: ope-pol-007.s3
    cita: "OPE-POL-007 §3, Proveedores"
    funda: "the threshold that a purchase order arrives by its expected date"
  - id: ope-pol-007.s4
    cita: "OPE-POL-007 §4, Revisión de precios"
    funda: "the thresholds on a cost increase the list price does not pass on, and on a line below its minimum margin"
  - id: kit.umbrales
    cita: "the challenge kit's metricas.yaml, where fuente_umbral is kit"
    funda: "the thresholds the kit sets with no policy behind them: the drop of a line's margin, and the inactivity of a customer"
```

No `cita` or `funda` contains the string `ISO`, so the debt's command in `DOUBTS.md` still lists only ISO clauses. Run: `grep -o 'ISO[^"]*' packages/agents/arbol/fundamentos.yaml | sort -u | wc -l` before and after; expected: the same number.

- [ ] **Step 3: Write `state.py`**

```python
import operator
from typing import Annotated, Any, Mapping, TypedDict

DERIVED_FIELDS = frozenset({"estado.detection.vigente", "estado.action.type", "estado.same_cause_as.status"})
STATE_FIELDS = DERIVED_FIELDS | frozenset(
    {
        "estado.candidato.metrica",
        "estado.candidato.descriptivo",
        "estado.cause.kind",
        "estado.same_cause_as",
        "estado.insufficient_cause",
        "estado.analyst_returns",
        "estado.proposal_returns",
        "estado.actions",
        "estado.decision.kind",
        "estado.executed_action",
    }
)


class AlertState(TypedDict, total=False):
    alert_id: str
    simulated_day: str
    entry: str
    earlier_alerts: dict[str, str]
    detection: dict[str, Any]
    title: dict[str, Any]
    cause: dict[str, Any] | None
    cause_rejections: list[Any]
    proposal_rejections: list[Any]
    same_cause_as: str | None
    analyst_returns: int
    proposal_returns: int
    insufficient_cause: Any
    actions: list[dict[str, Any]] | None
    decision: dict[str, Any] | None
    rejection_target: str | None
    executed_action: dict[str, Any] | None
    merged_into: str | None
    merged_alerts: list[str]
    queries: list[Any]
    status: str
    next_node: str
    fin: str
    camino: Annotated[list, operator.add]
    transitions: Annotated[list, operator.add]
    failures: Annotated[list, operator.add]
    events: Annotated[list, operator.add]


def field_value(state: Mapping[str, Any], path: str) -> Any:
    value: Any = state
    for key in path.split(".")[1:]:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value


def approved_action(state: Mapping[str, Any]) -> dict[str, Any] | None:
    decision = state.get("decision") or {}
    if decision.get("kind") not in ("approve", "edit"):
        return None
    for action in state.get("actions") or []:
        if action["id"] == decision.get("actionId"):
            if decision["kind"] == "edit":
                return {**action, "parameters": dict(decision["parameters"])}
            return dict(action)
    return None
```

- [ ] **Step 4: Write `arbol/base.yaml`**

Exactly this content, no comments:

```yaml
version: 1
leyes:
  - id: cifra_de_consulta
    fundamento: iso9001.7.5
  - id: accion_aprobada
    fundamento: iso42001.anexo-a.supervision-humana
  - id: ningun_agente_cambia_una_base
    fundamento: iso42001.8
  - id: datos_no_ordenes
    fundamento: iso42001.6.1
  - id: sin_evidencia_es_respuesta
    fundamento: iso31000.6.4.3
  - id: herramientas_de_su_hoja
    fundamento: iso42001.8
  - id: todo_paso_en_bitacora
    fundamento: iso31000.6.7
nodos:
  - id: detectar.raiz
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.descriptivo, op: "=", valor: false }
    si: detectar.cartera
    no: fin.sin_alerta
  - id: detectar.cartera
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: en, valor: [saldo_vencido, concentracion_vencida_pct, dias_pago_prom] }
    si: detectar.cartera.saldo_vencido
    no: detectar.margen
  - id: detectar.cartera.saldo_vencido
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: saldo_vencido }
    si: detectar.cartera.saldo_vencido.dias
    no: detectar.cartera.concentracion_vencida_pct
  - id: detectar.cartera.saldo_vencido.dias
    fundamento: fin-pol-004.s4
    predicado: { lee: kpi.saldo_vencido.max_dias_vencido, op: ">", umbral: saldo_vencido }
    si: hoja.vigia.titular
    no: detectar.cartera.saldo_vencido.cupo
  - id: detectar.cartera.saldo_vencido.cupo
    fundamento: fin-pol-004.s3
    predicado: { lee: kpi.saldo_vencido.saldo_abierto, op: ">", umbral: saldo_vencido }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.cartera.concentracion_vencida_pct
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: concentracion_vencida_pct }
    si: detectar.cartera.concentracion_vencida_pct.participacion
    no: detectar.cartera.dias_pago_prom
  - id: detectar.cartera.concentracion_vencida_pct.participacion
    fundamento: fin-pol-004.s5
    predicado: { lee: kpi.concentracion_vencida_pct.concentracion_vencida_pct, op: ">", umbral: concentracion_vencida_pct }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.cartera.dias_pago_prom
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: dias_pago_prom }
    si: detectar.cartera.dias_pago_prom.aumento
    no: fin.sin_alerta
  - id: detectar.cartera.dias_pago_prom.aumento
    fundamento: fin-pol-004.s5
    predicado: { lee: kpi.dias_pago_prom.aumento_pct, op: ">", umbral: dias_pago_prom }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.margen
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: en, valor: [margen_pct] }
    si: detectar.margen.margen_pct
    no: detectar.inventario
  - id: detectar.margen.margen_pct
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: margen_pct }
    si: detectar.margen.margen_pct.caida
    no: fin.sin_alerta
  - id: detectar.margen.margen_pct.caida
    fundamento: kit.umbrales
    predicado: { lee: kpi.margen_pct.caida_pts, op: ">", umbral: margen_pct }
    si: hoja.vigia.titular
    no: detectar.margen.margen_pct.minimo
  - id: detectar.margen.margen_pct.minimo
    fundamento: ope-pol-007.s4
    predicado: { lee: kpi.margen_pct.margen_pct, op: "<", umbral: margen_pct }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.inventario
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: en, valor: [cobertura_dias] }
    si: detectar.inventario.cobertura_dias
    no: detectar.comercial
  - id: detectar.inventario.cobertura_dias
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: cobertura_dias }
    si: detectar.inventario.cobertura_dias.minima
    no: fin.sin_alerta
  - id: detectar.inventario.cobertura_dias.minima
    fundamento: ope-pol-007.s2
    predicado: { lee: kpi.cobertura_dias.cobertura_dias, op: "<", umbral: cobertura_dias }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.comercial
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: en, valor: [descuento_en_exceso, margen_bruto_negativo] }
    si: detectar.comercial.descuento_en_exceso
    no: detectar.abastecimiento
  - id: detectar.comercial.descuento_en_exceso
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: descuento_en_exceso }
    si: detectar.comercial.descuento_en_exceso.tope
    no: detectar.comercial.margen_bruto_negativo
  - id: detectar.comercial.descuento_en_exceso.tope
    fundamento: com-pol-002.s2
    predicado: { lee: kpi.descuento_en_exceso.descuento_en_exceso, op: ">", umbral: descuento_en_exceso }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.comercial.margen_bruto_negativo
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: margen_bruto_negativo }
    si: detectar.comercial.margen_bruto_negativo.bajo_costo
    no: fin.sin_alerta
  - id: detectar.comercial.margen_bruto_negativo.bajo_costo
    fundamento: com-pol-002.s4
    predicado: { lee: kpi.margen_bruto_negativo.margen_bruto, op: "<", umbral: margen_bruto_negativo }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.abastecimiento
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: en, valor: [variacion_costo_pct, dias_retraso] }
    si: detectar.abastecimiento.variacion_costo_pct
    no: detectar.clientes
  - id: detectar.abastecimiento.variacion_costo_pct
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: variacion_costo_pct }
    si: detectar.abastecimiento.variacion_costo_pct.alza
    no: detectar.abastecimiento.dias_retraso
  - id: detectar.abastecimiento.variacion_costo_pct.alza
    fundamento: ope-pol-007.s4
    predicado: { lee: kpi.variacion_costo_pct.variacion_pct, op: ">", umbral: variacion_costo_pct }
    si: detectar.abastecimiento.variacion_costo_pct.sin_traslado
    no: fin.sin_alerta
  - id: detectar.abastecimiento.variacion_costo_pct.sin_traslado
    fundamento: ope-pol-007.s4
    predicado: { lee: kpi.variacion_costo_pct.dias_habiles_sin_traslado, op: ">", umbral: variacion_costo_pct }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.abastecimiento.dias_retraso
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: dias_retraso }
    si: detectar.abastecimiento.dias_retraso.atraso
    no: fin.sin_alerta
  - id: detectar.abastecimiento.dias_retraso.atraso
    fundamento: ope-pol-007.s3
    predicado: { lee: kpi.dias_retraso.dias_retraso, op: ">", umbral: dias_retraso }
    si: detectar.abastecimiento.dias_retraso.pendiente
    no: fin.sin_alerta
  - id: detectar.abastecimiento.dias_retraso.pendiente
    fundamento: ope-pol-007.s3
    predicado: { lee: kpi.dias_retraso.recibida, op: "=", umbral: dias_retraso }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: detectar.clientes
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: en, valor: [veces_intervalo_habitual] }
    si: detectar.clientes.veces_intervalo_habitual
    no: fin.sin_alerta
  - id: detectar.clientes.veces_intervalo_habitual
    fundamento: iso31000.6.4.2
    predicado: { lee: estado.candidato.metrica, op: "=", valor: veces_intervalo_habitual }
    si: detectar.clientes.veces_intervalo_habitual.historial
    no: fin.sin_alerta
  - id: detectar.clientes.veces_intervalo_habitual.historial
    fundamento: kit.umbrales
    predicado: { lee: kpi.veces_intervalo_habitual.pedidos, op: ">=", umbral: veces_intervalo_habitual }
    si: detectar.clientes.veces_intervalo_habitual.inactividad
    no: fin.sin_alerta
  - id: detectar.clientes.veces_intervalo_habitual.inactividad
    fundamento: kit.umbrales
    predicado: { lee: kpi.veces_intervalo_habitual.veces_intervalo_habitual, op: ">", umbral: veces_intervalo_habitual }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: hoja.vigia.titular
    hoja: { agente: vigia, decision: titular, skill: vigia/contrato.md }
    sigue: hoja.analista.explicar
  - id: hoja.analista.explicar
    hoja: { agente: analista, decision: explicar, skill: analista/contrato.md }
    sigue: explicar.misma_causa
  - id: explicar.misma_causa
    fundamento: iso9001.10.2.1.b.3
    predicado: { lee: estado.same_cause_as, op: existe }
    si: explicar.destino_analizado
    no: explicar.con_evidencia
  - id: explicar.destino_analizado
    fundamento: iso9001.10.2.1.b.3
    predicado: { lee: estado.same_cause_as.status, op: en, valor: [en análisis, propuesta] }
    si: fin.unida
    no: explicar.destino_nuevo
  - id: explicar.destino_nuevo
    fundamento: iso9001.10.2.1.b.3
    predicado: { lee: estado.same_cause_as.status, op: "=", valor: nueva }
    si: explicar.con_evidencia
    no: explicar.con_evidencia
  - id: explicar.con_evidencia
    fundamento: iso9001.10.2.1.b.2
    predicado: { lee: estado.cause.kind, op: "=", valor: identified }
    si: hoja.estratega.proponer
    no: hoja.estratega.revision_manual
  - id: hoja.estratega.proponer
    hoja: { agente: estratega, decision: proponer, skill: estratega/contrato.md }
    sigue: proponer.causa_insuficiente
  - id: proponer.causa_insuficiente
    fundamento: iso31000.6.4.4
    predicado: { lee: estado.insufficient_cause, op: existe }
    si: proponer.retorno_disponible
    no: proponer.con_acciones
  - id: proponer.retorno_disponible
    fundamento: iso9001.10.2.1.b.2
    predicado: { lee: estado.analyst_returns, op: "=", valor: 0 }
    si: hoja.analista.explicar
    no: hoja.estratega.revision_manual
  - id: proponer.con_acciones
    fundamento: iso31000.6.5.2
    predicado: { lee: estado.actions, op: existe }
    si: aprobar.decision
    no: hoja.estratega.revision_manual
  - id: hoja.estratega.revision_manual
    hoja: { agente: estratega, decision: revision_manual, skill: estratega/acciones.md }
    sigue: aprobar.decision
  - id: aprobar.decision
    fundamento: iso42001.anexo-a.supervision-humana
    predicado: { lee: estado.decision.kind, op: en, valor: [approve, edit] }
    si: ejecutar.vigente
    no: aprobar.recargar
  - id: aprobar.recargar
    fundamento: iso31000.6.5.3
    predicado: { lee: estado.decision.kind, op: "=", valor: request_changes }
    si: aprobar.recarga_disponible
    no: fin.rechazada
  - id: aprobar.recarga_disponible
    fundamento: iso31000.6.5.3
    predicado: { lee: estado.proposal_returns, op: "=", valor: 0 }
    si: hoja.estratega.proponer
    no: fin.recarga_agotada
  - id: ejecutar.vigente
    fundamento: iso9001.10.2.1.c
    predicado: { lee: estado.detection.vigente, op: "=", valor: true }
    si: ejecutar.automatizable
    no: fin.ya_no_aplica
  - id: ejecutar.automatizable
    fundamento: iso9001.10.2.1.c
    predicado: { lee: estado.action.type, op: en, valor: [email_draft, task, purchase_order_draft, price_change_draft] }
    si: hoja.ejecutor.ejecutar
    no: hoja.ejecutor.nota_manual
  - id: hoja.ejecutor.ejecutar
    hoja: { agente: ejecutor, decision: ejecutar, skill: ejecutor/contrato.md }
    sigue: ejecutar.resultado
  - id: hoja.ejecutor.nota_manual
    hoja: { agente: ejecutor, decision: nota_manual, skill: ejecutor/contrato.md }
    sigue: ejecutar.resultado
  - id: ejecutar.resultado
    fundamento: iso9001.10.2.1.c
    predicado: { lee: estado.executed_action, op: existe }
    si: fin.ejecutada
    no: fin.fallo_ejecucion
```

`ejecutar.automatizable` lists the action types `packages/tools/AGENTS.md` gives a tool, read from its "Decisions" list (`email_draft`, `task`, `purchase_order_draft`, `price_change_draft`); re-read that list before writing the line.

- [ ] **Step 5: Write the tests**

`packages/agents/tests/test_base.py`:

```python
from pathlib import Path

from centinela_agents.metrics import load_metrics
from centinela_agents.predicate import is_kpi, kpi_column
from centinela_agents.schema import Tree, index
from centinela_agents.state import STATE_FIELDS, approved_action, field_value
from centinela_agents.yaml_loader import load_yaml

AGENTS = Path(__file__).resolve().parents[1]
METRICAS = AGENTS.parents[1] / "data" / "metricas.yaml"


def base() -> Tree:
    return Tree.model_validate(load_yaml(AGENTS / "arbol" / "base.yaml"))


def test_the_base_parses_and_every_fundamento_is_registered():
    registry = {entry["id"] for entry in load_yaml(AGENTS / "arbol" / "fundamentos.yaml")["fundamentos"]}
    tree = base()
    assert {node.fundamento for node in tree.nodos if node.fundamento} <= registry
    assert {law.fundamento for law in tree.leyes} <= registry


def test_every_state_field_the_base_reads_is_declared():
    read = {node.predicado.lee for node in base().nodos if node.predicado and not is_kpi(node.predicado.lee)}
    assert read <= STATE_FIELDS


def test_every_metric_has_a_kpi_node_in_detectar():
    read = {kpi_column(node.predicado.lee)[0] for node in base().nodos if node.predicado and is_kpi(node.predicado.lee)}
    assert read == set(load_metrics(METRICAS).names)


def test_an_operator_stays_a_string_in_the_base():
    assert index(base())["explicar.con_evidencia"].predicado.op == "="
    assert index(base())["explicar.con_evidencia"].no == "hoja.estratega.revision_manual"


def test_field_value_walks_a_dotted_path():
    assert field_value({"cause": {"kind": "identified"}}, "estado.cause.kind") == "identified"
    assert field_value({"cause": None}, "estado.cause.kind") is None


def test_the_approved_action_carries_the_edited_parameters():
    actions = [{"id": "a1", "type": "email_draft", "parameters": {"vendedor_id": "VEN-01"}}]
    edit = {"kind": "edit", "actionId": "a1", "parameters": {"vendedor_id": "VEN-02"}}
    assert approved_action({"actions": actions, "decision": edit})["parameters"] == {"vendedor_id": "VEN-02"}
    assert approved_action({"actions": actions, "decision": {"kind": "approve", "actionId": "a1"}})["type"] == "email_draft"
    assert approved_action({"actions": actions, "decision": {"kind": "reject", "reason": "no"}}) is None
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -v`
Expected: all pass. A failure of `test_every_metric_has_a_kpi_node_in_detectar` means a metric lacks a branch or a node reads a misspelled metric.

- [ ] **Step 7: Ask the user, then commit**

```bash
git add packages/agents
git commit -q -F - <<'MSG'
Write the base of the decision tree, every route of today's graph as a node on one entry of the registry, and register the policy sections its thresholds rest on

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 5: The validator

**Files:**
- Create: `packages/agents/centinela_agents/validator.py`, `packages/agents/tests/support.py`, `packages/agents/tests/test_validator.py`

**Interfaces:**
- Consumes: everything from Tasks 2 to 4.
- Produces:
  - `validator.Grounds(base: Tree, registry: frozenset[str], metrics: Metrics, catalog: Catalog, skills: Path)`
  - `validator.InvalidTree(problems: list[str])`, an exception carrying `.problems`
  - `validator.problems(data: Mapping, grounds: Grounds) -> list[str]`
  - `validator.load_registry(path: Path) -> frozenset[str]`
  - `validator.checked_base(data, registry, metrics, catalog, skills) -> Tree`, raising `InvalidTree`
  - `validator.load_base(arbol: Path, metricas: Path, skills: Path, catalog: Catalog) -> Tree`, raising `InvalidTree`
  - `tests/support.py`: `AGENTS`, `ARBOL`, `METRICAS`, `SKILLS`, `VIEW_CATALOG`, `base_data()`, `base_tree()`, `node_of(data, node_id)`, `grounds(catalog=VIEW_CATALOG, metrics=None)`

- [ ] **Step 1: Write `tests/support.py`**

```python
# The catalogue the tests hand the validator and the walk. Each metric's columns are its
# v_* view's, plus the ones the base reads that no view has and the kernel builds:
# caida_pts, margen_minimo_pct, concentracion_vencida_pct, aumento_pct, dias_habiles_sin_traslado.
# The real catalogue comes from kpi_catalogo; DOUBTS.md files the gap.
import copy
from pathlib import Path

from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Tree
from centinela_agents.validator import Grounds, load_registry
from centinela_agents.yaml_loader import load_yaml

AGENTS = Path(__file__).resolve().parents[1]
ARBOL = AGENTS / "arbol"
METRICAS = AGENTS.parents[1] / "data" / "metricas.yaml"
SKILLS = AGENTS / "skills"


def kpi(entity, *columns):
    return Kpi(entity=tuple(entity), columns=frozenset({*entity, *columns}))


VIEW_CATALOG = Catalog(
    {
        "margen_pct": kpi(["semana", "linea"], "ventas", "costo", "margen_pct", "caida_pts", "margen_minimo_pct"),
        "saldo_vencido": kpi(["cliente_id"], "segmento", "cupo_credito", "plazo_dias", "saldo_abierto", "saldo_vencido", "max_dias_vencido", "dias_pago_prom_120d"),
        "concentracion_vencida_pct": kpi(["cliente_id"], "saldo_vencido", "concentracion_vencida_pct"),
        "dias_pago_prom": kpi(["cliente_id", "mes_factura"], "dias_pago_prom", "facturas_pagadas", "aumento_pct"),
        "cobertura_dias": kpi(["sku", "bodega_id"], "linea", "clase_abc", "existencia", "demanda_prom_30d", "cobertura_dias", "unidades_pendientes"),
        "variacion_costo_pct": kpi(["sku"], "linea", "clase_abc", "proveedor_id", "costo_unitario", "costo_anterior", "variacion_pct", "fecha_vigencia", "dias_habiles_sin_traslado"),
        "dias_retraso": kpi(["oc_id"], "proveedor_id", "sku", "bodega_id", "fecha_esperada", "cantidad", "costo_unitario", "recibida", "dias_retraso"),
        "descuento_en_exceso": kpi(["vendedor_id", "semana"], "descuento_en_exceso"),
        "margen_bruto_negativo": kpi(["pedido_id", "linea_n"], "sku", "margen_bruto"),
        "veces_intervalo_habitual": kpi(["cliente_id"], "pedidos", "ultima_compra", "intervalo_prom_dias", "dias_sin_comprar", "veces_intervalo_habitual"),
    }
)


def base_data() -> dict:
    return copy.deepcopy(load_yaml(ARBOL / "base.yaml"))


def base_tree() -> Tree:
    return Tree.model_validate(base_data())


def node_of(data: dict, node_id: str) -> dict:
    return next(node for node in data["nodos"] if node["id"] == node_id)


def grounds(catalog: Catalog = VIEW_CATALOG, metrics=None) -> Grounds:
    return Grounds(
        base=base_tree(),
        registry=load_registry(ARBOL / "fundamentos.yaml"),
        metrics=metrics or load_metrics(METRICAS),
        catalog=catalog,
        skills=SKILLS,
    )
```

- [ ] **Step 2: Write the failing tests**

`packages/agents/tests/test_validator.py`:

```python
# One planted violation per rule of the validator, each on a copy of the base, so a rule that
# never fires fails here. The base itself must pass with no problem.
import pytest

from centinela_agents.metrics import Metrics, load_metrics
from centinela_agents.validator import InvalidTree, checked_base, load_base, load_registry, problems
from support import ARBOL, METRICAS, SKILLS, VIEW_CATALOG, base_data, grounds, node_of


def set_key(node_id, key, value):
    def plant(data):
        node_of(data, node_id)[key] = value
    return plant


def drop_key(node_id, key):
    def plant(data):
        node_of(data, node_id).pop(key)
    return plant


def set_predicate(node_id, **changes):
    def plant(data):
        node_of(data, node_id)["predicado"].update(changes)
    return plant


def set_leaf(node_id, **changes):
    def plant(data):
        node_of(data, node_id)["hoja"].update(changes)
    return plant


def duplicate(node_id):
    def plant(data):
        data["nodos"].append(dict(node_of(data, node_id)))
    return plant


def set_law(index, fundamento):
    def plant(data):
        data["leyes"][index]["fundamento"] = fundamento
    return plant


def both_branches(node_id, target):
    def plant(data):
        node_of(data, node_id).update(si=target, no=target)
    return plant


PLANTED = [
    ("schema", set_key("explicar.misma_causa", "color", "rojo"), "schema:"),
    ("two values", set_predicate("detectar.cartera.saldo_vencido.dias", valor=15), "compares with an umbral and a valor at once"),
    ("two operands", set_predicate("explicar.con_evidencia", lee="estado.cause.kind y estado.actions"), "which is not one operand"),
    ("en without a list", set_predicate("aprobar.decision", valor="approve"), "tests en without a closed list"),
    ("no fundamento", drop_key("explicar.con_evidencia", "fundamento"), "explicar.con_evidencia lacks its fundamento"),
    ("no si", drop_key("explicar.con_evidencia", "si"), "explicar.con_evidencia lacks its si"),
    ("no no", drop_key("explicar.con_evidencia", "no"), "explicar.con_evidencia lacks its no"),
    ("unregistered fundamento", set_key("explicar.con_evidencia", "fundamento", "iso9999.1"), "absent from fundamentos.yaml"),
    ("leaf with fundamento", set_key("hoja.vigia.titular", "fundamento", "iso31000.6.4.2"), "inherits its parent's fundamento"),
    ("duplicate id", duplicate("explicar.con_evidencia"), "explicar.con_evidencia is declared twice"),
    ("bypass the gate", set_key("proponer.con_acciones", "si", "ejecutar.vigente"), "is reached without passing aprobar.decision"),
    ("bypass vigente", set_key("aprobar.decision", "si", "ejecutar.automatizable"), "is reached without passing ejecutar.vigente"),
    ("cycle", set_key("hoja.analista.explicar", "sigue", "hoja.vigia.titular"), "cycle"),
    ("uncapped return", set_key("proponer.causa_insuficiente", "si", "hoja.analista.explicar"), "cycle"),
    ("dangling id", set_key("explicar.con_evidencia", "no", "explicar.inexistente"), "names explicar.inexistente, which is no node, leaf or end"),
    ("unknown end", set_key("explicar.con_evidencia", "no", "fin.inventado"), "names fin.inventado, which is no node, leaf or end"),
    ("reaches no fin", both_branches("explicar.con_evidencia", "explicar.inexistente"), "explicar.con_evidencia reaches no fin"),
    ("unknown kpi column", set_predicate("detectar.cartera.saldo_vencido.dias", lee="kpi.saldo_vencido.dias_inventados"), "which the kernel does not build"),
    ("undeclared state field", set_predicate("explicar.con_evidencia", lee="estado.humor"), "which the alert's state does not declare"),
    ("kpi outside detectar", set_predicate("proponer.con_acciones", lee="kpi.saldo_vencido.max_dias_vencido", op=">", umbral="saldo_vencido", valor=None), "reads a KPI outside detectar"),
    ("unknown umbral", set_predicate("detectar.cartera.saldo_vencido.dias", umbral="inventada"), "absent from metricas.yaml and from the approved KPIs"),
    ("umbral without the column", set_predicate("detectar.cartera.saldo_vencido.dias", lee="kpi.saldo_vencido.saldo_vencido"), "sets no threshold for saldo_vencido"),
    ("valor on a kpi", set_predicate("detectar.cartera.saldo_vencido.dias", umbral=None, valor=15), "compares a KPI with a valor"),
    ("umbral on a state field", set_predicate("explicar.con_evidencia", valor=None, umbral="saldo_vencido"), "bounds a state field with an umbral"),
    ("missing skill", set_leaf("hoja.vigia.titular", skill="vigia/inexistente.md"), "which is no file under packages/agents/skills"),
    ("decision outside the list", set_leaf("hoja.vigia.titular", decision="proponer"), "outside the decisions of vigia"),
    ("unknown agent", set_leaf("hoja.vigia.titular", agente="orquestador"), "outside vigia, analista, estratega and ejecutor"),
    ("L0 changed", set_law(0, "iso31000.6.6"), "L0 differs from the base"),
    ("L1 changed", set_predicate("aprobar.decision", valor=["approve"]), "L1 node aprobar.decision differs from the base"),
]


def test_the_base_passes():
    assert problems(base_data(), grounds()) == []


@pytest.mark.parametrize("name, plant, expected", PLANTED, ids=[name for name, _, _ in PLANTED])
def test_the_validator_refuses_each_planted_violation(name, plant, expected):
    data = base_data()
    plant(data)
    found = problems(data, grounds())
    assert any(expected in problem for problem in found), found


def test_a_metric_with_no_branch_skill_or_action_row_is_refused():
    real = load_metrics(METRICAS)
    metrics = Metrics({**real.descriptions, "metrica_nueva": "Nueva"}, {**real.thresholds, "metrica_nueva": {"x": 1}})
    found = problems(base_data(), grounds(metrics=metrics))
    assert "metric metrica_nueva has no L3 branch in detectar" in found
    assert "metric metrica_nueva has no skills/analista/metrica_nueva.md" in found
    assert "metric metrica_nueva has no row in skills/estratega/acciones.md" in found


def test_load_base_returns_the_base_from_its_files():
    assert load_base(ARBOL, METRICAS, SKILLS, VIEW_CATALOG).version == 1


def test_checked_base_raises_with_every_problem():
    data = base_data()
    node_of(data, "explicar.con_evidencia").pop("no")
    with pytest.raises(InvalidTree) as refused:
        checked_base(data, load_registry(ARBOL / "fundamentos.yaml"), load_metrics(METRICAS), VIEW_CATALOG, SKILLS)
    assert "explicar.con_evidencia lacks its no" in refused.value.problems
```

- [ ] **Step 3: Run them to see them fail**

Run: `uv run pytest tests/test_validator.py -v`
Expected: collection error, `No module named 'centinela_agents.validator'`.

- [ ] **Step 4: Write `validator.py`**

```python
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pydantic import ValidationError

from .catalog import Catalog, thresholds_named
from .metrics import Metrics, load_metrics, threshold_shape_problem
from .predicate import KPI_PATH, STATE_PATH
from .schema import AGENT_DECISIONS, ENDS, GATE, ROOT, STAGES, VIGENTE, Node, Tree, branches, index, level, reachable, stage_of
from .state import STATE_FIELDS
from .yaml_loader import load_yaml

CAPPED_RETURNS = (
    ("proponer", "explicar", "estado.analyst_returns"),
    ("aprobar", "proponer", "estado.proposal_returns"),
)


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
        *approval_problems(nodes),
        *cycle_problems(nodes),
        *end_problems(nodes),
        *operand_problems(tree, grounds.catalog),
        *threshold_problems(tree, grounds),
        *leaf_problems(tree, grounds.skills),
        *coverage_problems(tree, grounds),
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
    source, goal = stage_of(node.id, nodes), stage_of(target, nodes)
    return any(
        source == start and goal == end and predicate.lee == counter and predicate.op == "=" and predicate.valor == 0
        for start, end, counter in CAPPED_RETURNS
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
    return [f"{node_id} reaches no fin" for node_id in sorted(reachable(nodes, [ROOT])) if node_id in nodes and node_id not in finishing]


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
            found.append(f"{node.id} names agent {leaf.agente}, outside vigia, analista, estratega and ejecutor")
        elif leaf.decision not in allowed:
            found.append(f"{node.id} takes {leaf.decision}, outside the decisions of {leaf.agente}")
        path = (skills / leaf.skill).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            found.append(f"{node.id} loads {leaf.skill}, which is no file under packages/agents/skills")
    return found


def coverage_problems(tree: Tree, grounds: Grounds) -> list[str]:
    read = {
        KPI_PATH.match(node.predicado.lee).group(1)
        for node in tree.nodos
        if node.predicado is not None
        and KPI_PATH.match(node.predicado.lee)
        and node.id.split(".")[0] == "detectar"
        and level(node.id) == 3
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


def base_problems(tree: Tree, base: Tree) -> list[str]:
    found = [] if tree.leyes == base.leyes else ["L0 differs from the base"]
    mine = {node.id: node for node in tree.nodos if node.hoja is None and level(node.id) == 1}
    theirs = {node.id: node for node in base.nodos if node.hoja is None and level(node.id) == 1}
    found += [f"L1 node {node_id} differs from the base" for node_id in sorted(theirs) if mine.get(node_id) != theirs[node_id]]
    found += [f"L1 node {node_id} is absent from the base" for node_id in sorted(set(mine) - set(theirs))]
    return found
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -v`
Expected: all pass. If `test_the_base_passes` fails, read each problem: it is a defect of `base.yaml` or of the catalogue fixture, never a reason to weaken a rule.

- [ ] **Step 6: Ask the user, then commit**

```bash
git add packages/agents
git commit -q -F - <<'MSG'
Validate the decision tree with one planted violation per rule, so no path reaches `Ejecutor` without the approval gate and no metric loads with a gap

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 6: The walk of `detectar`, and whether a detection still breaks

**Files:**
- Create: `packages/agents/centinela_agents/walk.py`, `packages/agents/tests/test_detect.py`

**Interfaces:**
- Consumes: `schema`, `catalog`, `metrics`, `predicate`, `state`.
- Produces:
  - `walk.Context(nodes, metrics, catalog, reader)` with `Context.of(tree, metrics, catalog, reader)`
  - `walk.Detection(metric: str, entity: tuple, entry: str, path: tuple[tuple[str, str], ...], row: Mapping)`
  - `walk.kpi_holds(predicate, row, ctx) -> bool`, `walk.read(state, path, ctx) -> Any`, `walk.state_holds(predicate, state, ctx) -> bool`
  - `walk.walk_from(start, state, row, ctx) -> tuple[str, list[tuple[str, str]]]`
  - `walk.detect(ctx, day) -> list[Detection]`
  - `walk.still_breaks(state, ctx) -> bool`

- [ ] **Step 1: Write the failing tests**

`packages/agents/tests/test_detect.py`:

```python
from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.metrics import load_metrics
from centinela_agents.walk import Context, detect, still_breaks
import pytest

from support import METRICAS, VIEW_CATALOG, base_tree

DAY = "2026-03-02"
LATER = "2026-03-05"


def run(metric, row, catalog=VIEW_CATALOG):
    ctx = Context.of(base_tree(), load_metrics(METRICAS), catalog, lambda m, day: [row] if m == metric and day == DAY else [])
    return detect(ctx, DAY)


FIRING = [
    ("saldo_vencido", {"cliente_id": "CLI-001", "max_dias_vencido": 20, "saldo_abierto": 100, "cupo_credito": 5000}, "detectar.cartera.saldo_vencido.dias"),
    ("saldo_vencido", {"cliente_id": "CLI-001", "max_dias_vencido": 6, "saldo_abierto": 6000, "cupo_credito": 5000}, "detectar.cartera.saldo_vencido.cupo"),
    ("concentracion_vencida_pct", {"cliente_id": "CLI-002", "concentracion_vencida_pct": 12.5}, "detectar.cartera.concentracion_vencida_pct.participacion"),
    ("dias_pago_prom", {"cliente_id": "CLI-003", "mes_factura": "2026-02-01", "aumento_pct": 60.0}, "detectar.cartera.dias_pago_prom.aumento"),
    ("margen_pct", {"semana": "2026-02-23", "linea": "Hogar", "caida_pts": 3.5, "margen_pct": 20.0, "margen_minimo_pct": 18.0}, "detectar.margen.margen_pct.caida"),
    ("margen_pct", {"semana": "2026-02-23", "linea": "Hogar", "caida_pts": 1.0, "margen_pct": 15.0, "margen_minimo_pct": 18.0}, "detectar.margen.margen_pct.minimo"),
    ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "A", "cobertura_dias": 9.0}, "detectar.inventario.cobertura_dias.minima"),
    ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "B", "cobertura_dias": 6.0}, "detectar.inventario.cobertura_dias.minima"),
    ("descuento_en_exceso", {"vendedor_id": "VEN-01", "semana": "2026-02-23", "descuento_en_exceso": 120000}, "detectar.comercial.descuento_en_exceso.tope"),
    ("margen_bruto_negativo", {"pedido_id": "P-1", "linea_n": 1, "margen_bruto": -5000}, "detectar.comercial.margen_bruto_negativo.bajo_costo"),
    ("variacion_costo_pct", {"sku": "SKU-3", "variacion_pct": 7.5, "dias_habiles_sin_traslado": 12}, "detectar.abastecimiento.variacion_costo_pct.sin_traslado"),
    ("dias_retraso", {"oc_id": "OC-1", "dias_retraso": 4, "recibida": False}, "detectar.abastecimiento.dias_retraso.pendiente"),
    ("veces_intervalo_habitual", {"cliente_id": "CLI-004", "pedidos": 14, "veces_intervalo_habitual": 3.6}, "detectar.clientes.veces_intervalo_habitual.inactividad"),
]

QUIET = [
    ("saldo_vencido", {"cliente_id": "CLI-001", "max_dias_vencido": 15, "saldo_abierto": 100, "cupo_credito": 5000}),
    ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "B", "cobertura_dias": 8.0}),
    ("variacion_costo_pct", {"sku": "SKU-3", "variacion_pct": 7.5, "dias_habiles_sin_traslado": 3}),
    ("dias_retraso", {"oc_id": "OC-1", "dias_retraso": 4, "recibida": True}),
    ("veces_intervalo_habitual", {"cliente_id": "CLI-004", "pedidos": 9, "veces_intervalo_habitual": 5.0}),
    ("descuento_en_exceso", {"vendedor_id": "VEN-01", "semana": "2026-02-23", "descuento_en_exceso": 0}),
]


@pytest.mark.parametrize("metric, row, last", FIRING, ids=[last for _, _, last in FIRING])
def test_each_threshold_node_fires_on_a_breaking_row(metric, row, last):
    (detection,) = run(metric, row)
    assert detection.metric == metric
    assert detection.entry == "hoja.vigia.titular"
    assert detection.path[-1] == (last, "si")
    assert detection.entity == tuple(row.get(column) for column in VIEW_CATALOG.kpis[metric].entity)


@pytest.mark.parametrize("metric, row", QUIET)
def test_a_row_inside_its_threshold_fires_nothing(metric, row):
    assert run(metric, row) == []


@pytest.mark.parametrize(
    "metric, row",
    [
        ("saldo_vencido", {"cliente_id": "CLI-009", "max_dias_vencido": None, "saldo_abierto": 0, "cupo_credito": 5000}),
        ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "C", "cobertura_dias": 1.0}),
        ("cobertura_dias", {"sku": "SKU-1", "bodega_id": "BOD-MDE", "clase_abc": "A", "cobertura_dias": None}),
    ],
)
def test_a_null_value_or_a_class_without_threshold_fires_nothing(metric, row):
    assert run(metric, row) == []


def test_a_descriptive_kpi_fires_nothing():
    real = VIEW_CATALOG.kpis["saldo_vencido"]
    catalog = Catalog({**VIEW_CATALOG.kpis, "saldo_vencido": Kpi(real.entity, real.columns, descriptive=True)})
    assert run("saldo_vencido", {"cliente_id": "CLI-001", "max_dias_vencido": 20}, catalog) == []


def test_a_customer_six_days_late_on_a_thirty_day_habit_fires_nothing_on_the_base():
    rows = {
        "saldo_vencido": [{"cliente_id": "CLI-007", "max_dias_vencido": 6, "saldo_abierto": 900000, "cupo_credito": 5000000}],
        "dias_pago_prom": [{"cliente_id": "CLI-007", "mes_factura": "2026-02-01", "aumento_pct": 20.0}],
    }
    ctx = Context.of(base_tree(), load_metrics(METRICAS), VIEW_CATALOG, lambda metric, day: rows.get(metric, []))
    assert detect(ctx, DAY) == []


def state_of(path, rows_later):
    ctx = Context.of(base_tree(), load_metrics(METRICAS), VIEW_CATALOG, lambda metric, day: rows_later if day == LATER else [])
    state = {
        "simulated_day": DAY,
        "detection": {"metric": "saldo_vencido", "entity": ["CLI-001"], "path": path},
        "decision": {"kind": "approve", "simulated_day": LATER},
    }
    return state, ctx


BY_DAYS = [["detectar.raiz", "si"], ["detectar.cartera", "si"], ["detectar.cartera.saldo_vencido", "si"], ["detectar.cartera.saldo_vencido.dias", "si"]]
BY_CUPO = [*BY_DAYS[:3], ["detectar.cartera.saldo_vencido.dias", "no"], ["detectar.cartera.saldo_vencido.cupo", "si"]]


@pytest.mark.parametrize(
    "path, rows, expected",
    [
        (BY_DAYS, [{"cliente_id": "CLI-001", "max_dias_vencido": 25, "saldo_abierto": 1, "cupo_credito": 5}], True),
        (BY_DAYS, [{"cliente_id": "CLI-001", "max_dias_vencido": 0, "saldo_abierto": 1, "cupo_credito": 5}], False),
        (BY_DAYS, [{"cliente_id": "CLI-002", "max_dias_vencido": 25, "saldo_abierto": 1, "cupo_credito": 5}], False),
        (BY_DAYS, [], False),
        (BY_CUPO, [{"cliente_id": "CLI-001", "max_dias_vencido": 20, "saldo_abierto": 6000, "cupo_credito": 5000}], True),
    ],
    ids=["still late", "paid", "another customer only", "no row", "cupo still exceeded"],
)
def test_still_breaks_reapplies_each_node_the_detection_passed_on_si(path, rows, expected):
    state, ctx = state_of(path, rows)
    assert still_breaks(state, ctx) is expected
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_detect.py -v`
Expected: collection error, `No module named 'centinela_agents.walk'`.

- [ ] **Step 3: Write `walk.py`**

```python
from dataclasses import dataclass
from typing import Any, Mapping

from .catalog import Catalog, KpiReader, thresholds_named
from .metrics import Metrics
from .predicate import compare, is_kpi, kpi_column, threshold_value
from .schema import ROOT, Node, Predicate, Tree, index
from .state import approved_action, field_value


@dataclass(frozen=True)
class Context:
    nodes: Mapping[str, Node]
    metrics: Metrics
    catalog: Catalog
    reader: KpiReader

    @classmethod
    def of(cls, tree: Tree, metrics: Metrics, catalog: Catalog, reader: KpiReader) -> "Context":
        return cls(index(tree), metrics, catalog, reader)


@dataclass(frozen=True)
class Detection:
    metric: str
    entity: tuple[Any, ...]
    entry: str
    path: tuple[tuple[str, str], ...]
    row: Mapping[str, Any]


def kpi_holds(predicate: Predicate, row: Mapping[str, Any], ctx: Context) -> bool:
    _, column = kpi_column(predicate.lee)
    thresholds = thresholds_named(predicate.umbral, ctx.metrics, ctx.catalog) or {}
    return compare(predicate.op, row.get(column), threshold_value(thresholds.get(column), row))


def read(state: Mapping[str, Any], path: str, ctx: Context) -> Any:
    if path == "estado.detection.vigente":
        return still_breaks(state, ctx)
    if path == "estado.action.type":
        action = approved_action(state)
        return None if action is None else action.get("type")
    if path == "estado.same_cause_as.status":
        return (state.get("earlier_alerts") or {}).get(state.get("same_cause_as"))
    return field_value(state, path)


def state_holds(predicate: Predicate, state: Mapping[str, Any], ctx: Context) -> bool:
    if is_kpi(predicate.lee):
        raise ValueError(f"{predicate.lee} is a KPI, and an alert reads its measure through ejecutar.vigente")
    return compare(predicate.op, read(state, predicate.lee, ctx), predicate.valor)


def walk_from(start: str, state: Mapping[str, Any], row: Mapping[str, Any], ctx: Context) -> tuple[str, list[tuple[str, str]]]:
    current, path = start, []
    while current in ctx.nodes and ctx.nodes[current].hoja is None:
        node = ctx.nodes[current]
        predicate = node.predicado
        if is_kpi(predicate.lee):
            metric, _ = kpi_column(predicate.lee)
            if metric != state["candidato"]["metrica"]:
                raise ValueError(f"{node.id} reads {metric} on a row of {state['candidato']['metrica']}")
            passed = kpi_holds(predicate, row, ctx)
        else:
            passed = state_holds(predicate, state, ctx)
        branch = "si" if passed else "no"
        path.append((current, branch))
        current = node.si if passed else node.no
    return current, path


def detect(ctx: Context, day: str) -> list[Detection]:
    found: list[Detection] = []
    for metric, kpi in ctx.catalog.kpis.items():
        for row in ctx.reader(metric, day):
            candidate = {"candidato": {"metrica": metric, "descriptivo": kpi.descriptive}}
            target, path = walk_from(ROOT, candidate, row, ctx)
            if target in ctx.nodes:
                entity = tuple(row.get(column) for column in kpi.entity)
                found.append(Detection(metric, entity, target, tuple(path), dict(row)))
    return found


def still_breaks(state: Mapping[str, Any], ctx: Context) -> bool:
    detection = state["detection"]
    day = (state.get("decision") or {}).get("simulated_day") or state["simulated_day"]
    kpi = ctx.catalog.kpis[detection["metric"]]
    entity = list(detection["entity"])
    rows = [row for row in ctx.reader(detection["metric"], day) if [row.get(column) for column in kpi.entity] == entity]
    if not rows:
        return False
    passed = [
        ctx.nodes[node_id].predicado
        for node_id, branch in detection["path"]
        if branch == "si" and node_id in ctx.nodes and is_kpi(ctx.nodes[node_id].predicado.lee)
    ]
    return all(kpi_holds(predicate, rows[0], ctx) for predicate in passed)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Ask the user, then commit**

```bash
git add packages/agents
git commit -q -F - <<'MSG'
Walk the stage `detectar` per KPI row, and re-apply a detection's thresholds on the day of execution, so an action whose cause is gone is never run

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 7: The compiler and the interpreter

**Files:**
- Create: `packages/agents/centinela_agents/failures.py`, `packages/agents/centinela_agents/graph.py`, `packages/agents/tests/test_graph.py`
- Modify: `packages/agents/tests/support.py` (append the stubs)

**Interfaces:**
- Consumes: `walk.Context`, `walk.Detection`, `walk.state_holds`, `state.AlertState`, `state.approved_action`, `schema.*`, `metrics.Metrics`, `catalog.Catalog`, `catalog.KpiReader`.
- Produces:
  - `failures.StepTimeout`, `failures.TokenCapReached`, `failures.SchemaRefused` (exceptions a leaf raises)
  - `graph.LeafFunction = Callable[[Mapping[str, Any]], Mapping[str, Any]]`, `graph.Classifier = Callable[[Mapping[str, Any]], str]`
  - `graph.DECISION_KINDS`, `graph.REJECTION_TARGETS`, `graph.REASONS: dict[str, str]`, `graph.BOUND_NODES: frozenset[str]`
  - `graph.MissingLeaf`, `graph.ResumeRefused`
  - `graph.effects(node_id, branch, state) -> dict`
  - `graph.compile_tree(tree, *, leaves, metrics, catalog, reader, classify, checkpointer)` → a compiled LangGraph graph
  - `graph.Compiler(*, leaves, metrics, catalog, reader, classify, checkpointer)` with `.graph(tree)`, cached by `tree.version`
  - `graph.start_alert(graph, detection, *, alert_id, day, earlier_alerts=None, cause_rejections=(), proposal_rejections=()) -> dict`
  - `graph.awaiting_decision(graph, alert_id) -> bool`
  - `graph.resume(graph, alert_id, decision) -> dict`
  - `tests/support.py`: `DAY`, `DECISION_DAY`, `SALDO_ROW`, `IDENTIFIED`, `EMAIL`, `MANUAL_TASK`, `Recorder`, `leaves(recorder, overrides=None)`, `reader_from(rows_by_day)`, `compiled(recorder, *, overrides=None, rows=None, classify=None, tree=None, catalog=VIEW_CATALOG)`, `saldo_detection(row=SALDO_ROW, tree=None, catalog=VIEW_CATALOG, rows=None)`, `approve(action_id="act-email", decision_id="dec-1", day=DECISION_DAY)`, `statuses(state, alert_id="A1")`

LangGraph names in this task: `StateGraph`, `START`, `END` from `langgraph.graph`; `interrupt`, `Command` from `langgraph.types`; `InMemorySaver` from `langgraph.checkpoint.memory`. If the installed version names the saver `MemorySaver`, use that name in `support.py` and say so in the commit.

- [ ] **Step 1: Append the stubs to `tests/support.py`**

Add to the imports at the top: `from langgraph.checkpoint.memory import InMemorySaver`, `from centinela_agents.graph import compile_tree`, `from centinela_agents.walk import Context, detect`. Append:

```python
DAY = "2026-03-02"
DECISION_DAY = "2026-03-05"
SALDO_ROW = {"cliente_id": "CLI-001", "segmento": "Mayorista", "cupo_credito": 5000000, "saldo_abierto": 1200000, "saldo_vencido": 800000, "max_dias_vencido": 20}
IDENTIFIED = {"kind": "identified", "sentence": {"text": "El cliente dejó de pagar desde enero.", "figures": []}, "evidence": []}
EMAIL = {"id": "act-email", "title": "Recordatorio de pago", "type": "email_draft", "impact": None, "parameters": {"recipient": "CLI-001", "vendedor_id": "VEN-01"}}
MANUAL_TASK = {"id": "act-manual", "title": "Revisión manual de la alerta", "type": "task", "impact": None, "parameters": {"owner": "Analista de cartera"}}

DEFAULT_LEAVES = {
    ("vigia", "titular"): lambda state: {"title": {"text": "Cartera vencida de CLI-001", "figures": []}},
    ("analista", "explicar"): lambda state: {"cause": IDENTIFIED, "same_cause_as": None},
    ("estratega", "proponer"): lambda state: {"actions": [EMAIL], "insufficient_cause": None},
    ("estratega", "revision_manual"): lambda state: {"actions": [MANUAL_TASK]},
    ("ejecutor", "ejecutar"): lambda state: {"executed_action": {"actionId": state["action"]["id"], "result": "Borrador creado"}},
    ("ejecutor", "nota_manual"): lambda state: {"executed_action": {"actionId": state["action"]["id"], "result": "Tarea creada"}},
}


class Recorder:
    def __init__(self):
        self.calls = []
        self.received = {}

    def count(self, agent, decision):
        return self.calls.count((agent, decision))


def leaves(recorder, overrides=None):
    chosen = {**DEFAULT_LEAVES, **(overrides or {})}

    def recording(key, function):
        def run(state):
            recorder.calls.append(key)
            recorder.received[key] = dict(state)
            return function(state)
        return run

    return {key: recording(key, function) for key, function in chosen.items()}


def reader_from(rows_by_day):
    return lambda metric, day: list(rows_by_day.get(day, {}).get(metric, []))


def compiled(recorder, *, overrides=None, rows=None, classify=None, tree=None, catalog=VIEW_CATALOG):
    return compile_tree(
        tree or base_tree(),
        leaves=leaves(recorder, overrides),
        metrics=load_metrics(METRICAS),
        catalog=catalog,
        reader=reader_from({DECISION_DAY: {"saldo_vencido": [SALDO_ROW]}} if rows is None else rows),
        classify=classify or (lambda state: "propuesta"),
        checkpointer=InMemorySaver(),
    )


def saldo_detection(row=SALDO_ROW, tree=None, catalog=VIEW_CATALOG, rows=None):
    ctx = Context.of(tree or base_tree(), load_metrics(METRICAS), catalog, reader_from({DAY: rows or {"saldo_vencido": [row]}}))
    (detection,) = detect(ctx, DAY)
    return detection


def approve(action_id="act-email", decision_id="dec-1", day=DECISION_DAY):
    return {"id": decision_id, "kind": "approve", "actionId": action_id, "simulated_day": day}


def statuses(state, alert_id="A1"):
    return [status for alert, status in state["transitions"] if alert == alert_id]
```

- [ ] **Step 2: Write the failing tests**

`packages/agents/tests/test_graph.py`:

```python
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from centinela_agents.graph import BOUND_NODES, Compiler, MissingLeaf, ResumeRefused, awaiting_decision, compile_tree, resume, start_alert
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import ENDS, branches, index
from support import DAY, DECISION_DAY, EMAIL, METRICAS, VIEW_CATALOG, Recorder, approve, base_tree, compiled, leaves, reader_from, saldo_detection, statuses


def test_an_alert_pauses_at_the_gate_and_executes_on_approval():
    recorder = Recorder()
    graph = compiled(recorder)
    state = start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    assert awaiting_decision(graph, "A1")
    assert statuses(state) == ["nueva", "en análisis", "propuesta"]
    assert recorder.count("ejecutor", "ejecutar") == 0
    final = resume(graph, "A1", approve())
    assert final["fin"] == "fin.ejecutada"
    assert final["status"] == "ejecutada"
    assert statuses(final) == ["nueva", "en análisis", "propuesta", "ejecutada"]
    assert ["aprobar.decision", "si"] in final["camino"]
    assert ["ejecutar.vigente", "si"] in final["camino"]


def test_ejecutor_receives_the_approved_action_and_the_decision_only():
    recorder = Recorder()
    graph = compiled(recorder)
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    resume(graph, "A1", approve())
    received = recorder.received[("ejecutor", "ejecutar")]
    assert set(received) == {"alert_id", "action", "decision"}
    assert received["action"] == EMAIL


def test_an_edit_replaces_the_parameters_ejecutor_receives():
    recorder = Recorder()
    graph = compiled(recorder)
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    edit = {"id": "dec-1", "kind": "edit", "actionId": "act-email", "parameters": {"recipient": "CLI-001", "vendedor_id": "VEN-02"}, "simulated_day": DECISION_DAY}
    resume(graph, "A1", edit)
    assert recorder.received[("ejecutor", "ejecutar")]["action"]["parameters"] == {"recipient": "CLI-001", "vendedor_id": "VEN-02"}


def test_a_leaf_with_no_function_is_refused_at_compile():
    recorder = Recorder()
    functions = leaves(recorder)
    functions.pop(("ejecutor", "nota_manual"))
    with pytest.raises(MissingLeaf, match="hoja.ejecutor.nota_manual"):
        compile_tree(base_tree(), leaves=functions, metrics=load_metrics(METRICAS), catalog=VIEW_CATALOG, reader=reader_from({}), classify=lambda state: "ninguno", checkpointer=InMemorySaver())


def test_a_resume_when_nothing_awaits_is_refused():
    graph = compiled(Recorder())
    start_alert(graph, saldo_detection(), alert_id="A1", day=DAY)
    resume(graph, "A1", approve())
    with pytest.raises(ResumeRefused, match="awaits no decision"):
        resume(graph, "A1", approve(decision_id="dec-2"))


def test_the_compiler_caches_a_graph_by_version():
    recorder = Recorder()
    compiler = Compiler(leaves=leaves(recorder), metrics=load_metrics(METRICAS), catalog=VIEW_CATALOG, reader=reader_from({}), classify=lambda state: "ninguno", checkpointer=InMemorySaver())
    tree = base_tree()
    assert compiler.graph(tree) is compiler.graph(tree)
    assert compiler.graph(tree.model_copy(update={"version": 2})) is not compiler.graph(tree)


def test_every_node_the_interpreter_binds_a_write_to_is_in_the_base():
    nodes = index(base_tree())
    assert BOUND_NODES <= set(nodes)
    ends = {target for node in nodes.values() for _, target in branches(node) if target.startswith("fin.")}
    assert ends <= ENDS
```

- [ ] **Step 3: Run them to see them fail**

Run: `uv run pytest tests/test_graph.py -v`
Expected: collection error, `No module named 'centinela_agents.graph'`.

- [ ] **Step 4: Write `failures.py`**

```python
class StepTimeout(Exception):
    pass


class TokenCapReached(Exception):
    pass


class SchemaRefused(Exception):
    pass
```

- [ ] **Step 5: Write `graph.py`**

```python
from typing import Any, Callable, Mapping

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .catalog import Catalog, KpiReader
from .failures import SchemaRefused, StepTimeout, TokenCapReached
from .metrics import Metrics
from .schema import ENDS, GATE, Leaf, Node, Tree, reachable
from .state import AlertState, approved_action
from .walk import Context, Detection, state_holds

LeafFunction = Callable[[Mapping[str, Any]], Mapping[str, Any]]
Classifier = Callable[[Mapping[str, Any]], str]
DECISION_KINDS = ("approve", "edit", "reject", "request_changes")
REJECTION_TARGETS = ("causa", "propuesta", "ambos", "ninguno")
DECIDED_STATUS = {"approve": "aprobada", "edit": "aprobada", "reject": "rechazada"}
ACCUMULATED = ("camino", "transitions", "failures", "events")
REASONS = {
    "timeout": "El análisis no terminó: se agotó el tiempo de respuesta del modelo.",
    "token_cap": "El análisis no terminó: la alerta alcanzó su tope de tokens.",
    "schema": "El análisis no terminó: el modelo no devolvió una respuesta válida.",
}
BOUND_NODES = frozenset({"explicar.destino_nuevo", "proponer.retorno_disponible", "aprobar.recarga_disponible", GATE})


class MissingLeaf(Exception):
    pass


class ResumeRefused(Exception):
    pass


def merge(*updates: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for update in updates:
        for key, value in update.items():
            merged[key] = [*merged.get(key, []), *value] if key in ACCUMULATED else value
    return merged


def entering(target: str, state: Mapping[str, Any], nodes: Mapping[str, Node]) -> dict[str, Any]:
    node = nodes.get(target)
    status = state.get("status")
    if node is not None and node.hoja is not None and node.hoja.agente == "analista" and status == "nueva":
        return {"status": "en análisis", "transitions": [[state["alert_id"], "en análisis"]]}
    if target == GATE and status != "propuesta":
        return {"status": "propuesta", "transitions": [[state["alert_id"], "propuesta"]]}
    return {}


def effects(node_id: str, branch: str, state: Mapping[str, Any]) -> dict[str, Any]:
    named = state.get("same_cause_as")
    merged = list(state.get("merged_alerts") or [])
    if (node_id, branch) == ("explicar.destino_nuevo", "si"):
        if named in merged:
            return {}
        return {"merged_alerts": [*merged, named], "transitions": [[named, "unida"]]}
    if (node_id, branch) == ("explicar.destino_nuevo", "no"):
        return {"same_cause_as": None, "events": [{"kind": "same_cause_dropped", "alert": named}]}
    if (node_id, branch) == ("proponer.retorno_disponible", "si"):
        return {"analyst_returns": (state.get("analyst_returns") or 0) + 1}
    if (node_id, branch) == ("aprobar.recarga_disponible", "si"):
        return {
            "proposal_returns": (state.get("proposal_returns") or 0) + 1,
            "proposal_rejections": [*(state.get("proposal_rejections") or []), state["decision"]["reason"]],
            "decision": None,
        }
    return {}


def failure_kind(error: Exception) -> str:
    if isinstance(error, StepTimeout):
        return "timeout"
    if isinstance(error, TokenCapReached):
        return "token_cap"
    if isinstance(error, SchemaRefused):
        return "schema"
    return "error"


def fallback(leaf: Leaf, state: Mapping[str, Any], error: Exception, ctx: Context) -> dict[str, Any]:
    key = (leaf.agente, leaf.decision)
    if key == ("vigia", "titular"):
        detection = state["detection"]
        words = [ctx.metrics.descriptions.get(detection["metric"], detection["metric"]), *map(str, detection["entity"])]
        return {"title": {"text": " ".join(words), "figures": []}}
    if key == ("analista", "explicar"):
        reason = REASONS.get(failure_kind(error), REASONS["schema"])
        return {"cause": {"kind": "no_evidence", "reason": reason, "queriesReviewed": list(state.get("queries") or [])}, "same_cause_as": None}
    if key == ("estratega", "proponer"):
        return {"actions": None, "insufficient_cause": None}
    if leaf.agente == "ejecutor":
        return {"executed_action": None}
    raise error


def leaf_node(node: Node, function: LeafFunction, ctx: Context):
    leaf = node.hoja

    def run(state: Mapping[str, Any]) -> dict[str, Any]:
        given = (
            {"alert_id": state["alert_id"], "action": approved_action(state), "decision": state.get("decision")}
            if leaf.agente == "ejecutor"
            else state
        )
        try:
            update, failures = dict(function(given)), []
        except Exception as error:
            update, failures = fallback(leaf, state, error, ctx), [{"step": node.id, "kind": failure_kind(error)}]
        return merge(update, entering(node.sigue, {**state, **update}, ctx.nodes), {"camino": [[node.id, "hoja"]], "failures": failures})

    return run


def predicate_node(node: Node, ctx: Context):
    def run(state: Mapping[str, Any]) -> dict[str, Any]:
        recorded: dict[str, Any] = {}
        if node.id == GATE:
            decision = interrupt({"alert_id": state["alert_id"], "awaiting": GATE})
            recorded = {"decision": decision}
            if decision["kind"] in DECIDED_STATUS:
                recorded["status"] = DECIDED_STATUS[decision["kind"]]
            state = {**state, **recorded}
        passed = state_holds(node.predicado, state, ctx)
        branch = "si" if passed else "no"
        target = node.si if passed else node.no
        change = merge(recorded, effects(node.id, branch, state))
        return merge(change, entering(target, {**state, **change}, ctx.nodes), {"camino": [[node.id, branch]], "next_node": target})

    return run


def classified(classify: Classifier, state: Mapping[str, Any]) -> str:
    try:
        target = classify(state)
    except Exception:
        return "ninguno"
    return target if target in REJECTION_TARGETS else "ninguno"


def end_node(end_id: str, classify: Classifier):
    def run(state: Mapping[str, Any]) -> dict[str, Any]:
        alert = state["alert_id"]
        if end_id == "fin.unida":
            return {"fin": end_id, "merged_into": state["same_cause_as"], "status": "unida", "transitions": [[alert, "unida"]]}
        if end_id == "fin.ejecutada":
            return {"fin": end_id, "status": "ejecutada", "transitions": [[alert, "ejecutada"]]}
        if end_id == "fin.rechazada":
            return {"fin": end_id, "rejection_target": classified(classify, state)}
        return {"fin": end_id}

    return run


def read_next(state: Mapping[str, Any]) -> str:
    return state["next_node"]


def read_entry(state: Mapping[str, Any]) -> str:
    return state["entry"]


def compile_tree(
    tree: Tree,
    *,
    leaves: Mapping[tuple[str, str], LeafFunction],
    metrics: Metrics,
    catalog: Catalog,
    reader: KpiReader,
    classify: Classifier,
    checkpointer: Any,
):
    ctx = Context.of(tree, metrics, catalog, reader)
    entries = sorted(node.id for node in tree.nodos if node.hoja is not None and node.hoja.agente == "vigia")
    graph = StateGraph(AlertState)
    for name in sorted(reachable(ctx.nodes, entries)):
        node = ctx.nodes.get(name)
        if node is None:
            graph.add_node(name, end_node(name, classify))
            graph.add_edge(name, END)
        elif node.hoja is not None:
            function = leaves.get((node.hoja.agente, node.hoja.decision))
            if function is None:
                raise MissingLeaf(f"{name} needs a function for {node.hoja.agente}/{node.hoja.decision}")
            graph.add_node(name, leaf_node(node, function, ctx))
            graph.add_edge(name, node.sigue)
        else:
            graph.add_node(name, predicate_node(node, ctx))
            graph.add_conditional_edges(name, read_next, sorted({node.si, node.no}))
    graph.add_conditional_edges(START, read_entry, entries)
    return graph.compile(checkpointer=checkpointer)


class Compiler:
    def __init__(self, *, leaves, metrics: Metrics, catalog: Catalog, reader: KpiReader, classify: Classifier, checkpointer: Any):
        self._dependencies = {"leaves": leaves, "metrics": metrics, "catalog": catalog, "reader": reader, "classify": classify, "checkpointer": checkpointer}
        self._graphs: dict[int, Any] = {}

    def graph(self, tree: Tree):
        if tree.version not in self._graphs:
            self._graphs[tree.version] = compile_tree(tree, **self._dependencies)
        return self._graphs[tree.version]


def thread(alert_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": alert_id}}


def start_alert(graph, detection: Detection, *, alert_id: str, day: str, earlier_alerts=None, cause_rejections=(), proposal_rejections=()) -> dict[str, Any]:
    initial = {
        "alert_id": alert_id,
        "simulated_day": day,
        "entry": detection.entry,
        "earlier_alerts": {other: status for other, status in (earlier_alerts or {}).items() if other != alert_id},
        "detection": {
            "metric": detection.metric,
            "entity": list(detection.entity),
            "path": [list(step) for step in detection.path],
            "row": dict(detection.row),
        },
        "status": "nueva",
        "transitions": [[alert_id, "nueva"]],
        "analyst_returns": 0,
        "proposal_returns": 0,
        "cause_rejections": list(cause_rejections),
        "proposal_rejections": list(proposal_rejections),
        "merged_alerts": [],
    }
    graph.invoke(initial, thread(alert_id))
    return graph.get_state(thread(alert_id)).values


def awaiting_decision(graph, alert_id: str) -> bool:
    return graph.get_state(thread(alert_id)).next == (GATE,)


def decision_problem(decision: Mapping[str, Any], state: Mapping[str, Any]) -> str | None:
    if not decision.get("id"):
        return "the decision has no record in apps/api"
    kind = decision.get("kind")
    if kind not in DECISION_KINDS:
        return f"{kind} is no decision"
    if kind in ("reject", "request_changes") and not str(decision.get("reason", "")).strip():
        return f"{kind} carries no reason"
    if kind == "request_changes" and (state.get("proposal_returns") or 0) >= 1:
        return "the alert already requested changes once"
    return None


def resume(graph, alert_id: str, decision: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = graph.get_state(thread(alert_id))
    if snapshot.next != (GATE,):
        raise ResumeRefused(f"{alert_id} awaits no decision")
    problem = decision_problem(decision, snapshot.values)
    if problem is not None:
        raise ResumeRefused(f"{alert_id}: {problem}")
    graph.invoke(Command(resume=dict(decision)), thread(alert_id))
    return graph.get_state(thread(alert_id)).values
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -v`
Expected: all pass. If LangGraph refuses a node name, read its message: the ids contain dots and accents only, and the reserved names are `__start__` and `__end__`; report it before renaming anything, because the ids are the tree's.

- [ ] **Step 7: Ask the user, then commit**

```bash
git add packages/agents
git commit -q -F - <<'MSG'
Compile the decision tree to the LangGraph graph, with the approval as an interrupt in its gate and every leaf injected, so routing runs with no model

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 8: The `ORQ-` cases on the compiled graph

**Files:**
- Create: `packages/agents/tests/test_orq.py`

**Interfaces:**
- Consumes: `support.*` from Tasks 5 and 7, `graph.*`, `validator.problems`, `validator.checked_base`, `walk.detect`, `failures.StepTimeout`.
- Produces: one test per case, `test_orq_<case>`, which `evals/AGENTS.md` names in Task 10.

- [ ] **Step 1: Write the tests**

`packages/agents/tests/test_orq.py`:

```python
# The orchestrator's cases of evals/AGENTS.md that need no apps/api and no model: the tree is
# compiled with stub leaves and a stub KPI reader, and each test names its case. The cases that
# need apps/api's record (a second avanzar, the order of a day, a reason handed to the next run)
# are not here.
import pytest

from centinela_agents.catalog import Catalog, Kpi
from centinela_agents.failures import StepTimeout
from centinela_agents.graph import REASONS, ResumeRefused, awaiting_decision, resume, start_alert
from centinela_agents.metrics import load_metrics
from centinela_agents.schema import Tree
from centinela_agents.validator import InvalidTree, checked_base, load_registry, problems
from centinela_agents.walk import Context, detect
from support import (
    ARBOL, DAY, DECISION_DAY, EMAIL, MANUAL_TASK, METRICAS, SALDO_ROW, SKILLS, VIEW_CATALOG,
    Recorder, approve, base_data, base_tree, compiled, grounds, node_of, reader_from, saldo_detection, statuses,
)

CALL = {"id": "act-call", "title": "Llamada al cliente", "type": "llamada", "impact": None, "parameters": {"cliente_id": "CLI-001"}}


def started(recorder, alert_id="A1", earlier=None, **options):
    graph = compiled(recorder, **options)
    state = start_alert(graph, saldo_detection(), alert_id=alert_id, day=DAY, earlier_alerts=earlier)
    return graph, state


def test_orq_a_tree_with_a_missing_no_is_refused_at_startup():
    data = base_data()
    node_of(data, "explicar.con_evidencia").pop("no")
    with pytest.raises(InvalidTree) as refused:
        checked_base(data, load_registry(ARBOL / "fundamentos.yaml"), load_metrics(METRICAS), VIEW_CATALOG, SKILLS)
    assert "explicar.con_evidencia lacks its no" in refused.value.problems


def test_orq_a_path_to_ejecutor_without_aprobar_is_refused():
    data = base_data()
    node_of(data, "proponer.con_acciones")["si"] = "ejecutar.vigente"
    assert "hoja.ejecutor.ejecutar is reached without passing aprobar.decision" in problems(data, grounds())


def test_orq_request_changes_reproposes_once_and_refuses_a_second():
    recorder = Recorder()
    graph, _ = started(recorder)
    state = resume(graph, "A1", {"id": "dec-1", "kind": "request_changes", "reason": "Prefiero una llamada", "simulated_day": DECISION_DAY})
    assert recorder.count("estratega", "proponer") == 2
    assert awaiting_decision(graph, "A1")
    assert state["proposal_rejections"] == ["Prefiero una llamada"]
    assert state["decision"] is None
    assert statuses(state) == ["nueva", "en análisis", "propuesta"]
    with pytest.raises(ResumeRefused, match="already requested changes once"):
        resume(graph, "A1", {"id": "dec-2", "kind": "request_changes", "reason": "Otra vez", "simulated_day": DECISION_DAY})
    assert awaiting_decision(graph, "A1")
    assert resume(graph, "A1", approve(decision_id="dec-3"))["fin"] == "fin.ejecutada"


def test_orq_an_action_type_with_no_tool_becomes_one_manual_task():
    recorder = Recorder()
    graph, _ = started(recorder, overrides={("estratega", "proponer"): lambda state: {"actions": [CALL], "insufficient_cause": None}})
    final = resume(graph, "A1", approve(action_id="act-call"))
    assert recorder.count("ejecutor", "nota_manual") == 1
    assert recorder.count("ejecutor", "ejecutar") == 0
    assert final["executed_action"] == {"actionId": "act-call", "result": "Tarea creada"}
    assert final["fin"] == "fin.ejecutada"


@pytest.mark.parametrize(
    "rows",
    [{DECISION_DAY: {"saldo_vencido": [{**SALDO_ROW, "max_dias_vencido": 0}]}}, {}],
    ids=["paid", "no row"],
)
def test_orq_an_action_whose_kpi_no_longer_breaks_ends_at_ya_no_aplica(rows):
    recorder = Recorder()
    graph, _ = started(recorder, rows=rows)
    final = resume(graph, "A1", approve())
    assert final["fin"] == "fin.ya_no_aplica"
    assert final["status"] == "aprobada"
    assert recorder.count("ejecutor", "ejecutar") == 0
    assert "ejecutada" not in statuses(final)


def test_orq_two_alerts_of_one_cause_join_the_one_analysed_first():
    recorder = Recorder()
    graph, state = started(recorder, earlier={"A0": "propuesta"}, overrides={("analista", "explicar"): lambda state: {"cause": {"kind": "identified", "sentence": {"text": "x", "figures": []}, "evidence": []}, "same_cause_as": "A0"}})
    assert state["fin"] == "fin.unida"
    assert state["merged_into"] == "A0"
    assert statuses(state) == ["nueva", "en análisis", "unida"]
    assert recorder.count("estratega", "proponer") == 0


def test_orq_a_larger_alert_absorbs_a_smaller_one_still_nueva():
    recorder = Recorder()
    graph, state = started(recorder, earlier={"S1": "nueva"}, overrides={("analista", "explicar"): lambda state: {"cause": {"kind": "identified", "sentence": {"text": "x", "figures": []}, "evidence": []}, "same_cause_as": "S1"}})
    assert state["merged_alerts"] == ["S1"]
    assert ["S1", "unida"] in state["transitions"]
    assert awaiting_decision(graph, "A1")


@pytest.mark.parametrize("named, earlier", [("R1", {"R1": "rechazada"}), ("A1", {}), ("X9", {})], ids=["rejected", "itself", "unknown"])
def test_orq_a_same_cause_that_fails_both_checks_is_dropped_and_logged(named, earlier):
    recorder = Recorder()
    graph, state = started(recorder, earlier=earlier, overrides={("analista", "explicar"): lambda state: {"cause": {"kind": "identified", "sentence": {"text": "x", "figures": []}, "evidence": []}, "same_cause_as": named}})
    assert state["same_cause_as"] is None
    assert state["events"] == [{"kind": "same_cause_dropped", "alert": named}]
    assert awaiting_decision(graph, "A1")


def test_orq_an_estratega_fixed_to_insufficient_cause_runs_analista_twice_then_one_manual_review():
    recorder = Recorder()
    graph, state = started(recorder, overrides={("estratega", "proponer"): lambda state: {"actions": None, "insufficient_cause": "La causa no nombra el SKU"}})
    assert recorder.count("analista", "explicar") == 2
    assert recorder.received[("analista", "explicar")]["insufficient_cause"] == "La causa no nombra el SKU"
    assert recorder.count("estratega", "revision_manual") == 1
    assert state["analyst_returns"] == 1
    assert state["actions"] == [MANUAL_TASK]
    assert awaiting_decision(graph, "A1")


def test_orq_a_resume_with_no_recorded_decision_is_refused():
    recorder = Recorder()
    graph, _ = started(recorder)
    with pytest.raises(ResumeRefused, match="no record in apps/api"):
        resume(graph, "A1", {"kind": "approve", "actionId": "act-email"})
    assert awaiting_decision(graph, "A1")
    assert recorder.count("ejecutor", "ejecutar") == 0


@pytest.mark.parametrize(
    "classify, target",
    [(lambda state: "causa", "causa"), (lambda state: "otro", "ninguno"), (None, "ninguno")],
    ids=["causa", "outside the list", "classifier fails"],
)
def test_orq_a_rejection_reaches_the_classifier_and_its_failure_targets_ninguno(classify, target):
    def failing(state):
        raise RuntimeError("ollama")

    recorder = Recorder()
    graph, _ = started(recorder, classify=classify or failing)
    final = resume(graph, "A1", {"id": "dec-1", "kind": "reject", "reason": "El cliente ya pagó", "simulated_day": DECISION_DAY})
    assert final["fin"] == "fin.rechazada"
    assert final["status"] == "rechazada"
    assert final["rejection_target"] == target


def test_orq_a_model_call_past_its_timeout_takes_the_fallback_and_still_reaches_propuesta():
    def timeout(state):
        raise StepTimeout("ollama")

    recorder = Recorder()
    graph, state = started(recorder, overrides={("analista", "explicar"): timeout})
    assert state["cause"]["kind"] == "no_evidence"
    assert state["cause"]["reason"] == REASONS["timeout"]
    assert state["failures"] == [{"step": "hoja.analista.explicar", "kind": "timeout"}]
    assert recorder.count("estratega", "revision_manual") == 1
    assert statuses(state)[-1] == "propuesta"


def test_orq_a_failed_execution_leaves_the_alert_aprobada():
    def broken(state):
        raise RuntimeError("sandbox")

    recorder = Recorder()
    graph, _ = started(recorder, overrides={("ejecutor", "ejecutar"): broken})
    final = resume(graph, "A1", approve())
    assert final["fin"] == "fin.fallo_ejecucion"
    assert final["status"] == "aprobada"


RETRASO = Kpi(entity=("cliente_id",), columns=frozenset({"cliente_id", "dias_sobre_habito"}), thresholds={"dias_sobre_habito": 0})


def expanded():
    data = base_data()
    data["version"] = 2
    node_of(data, "detectar.cartera")["predicado"]["valor"].append("retraso_habito")
    node_of(data, "detectar.cartera.dias_pago_prom")["no"] = "detectar.cartera.retraso_habito"
    data["nodos"] += [
        {"id": "detectar.cartera.retraso_habito", "fundamento": "iso31000.6.4.2", "predicado": {"lee": "estado.candidato.metrica", "op": "=", "valor": "retraso_habito"}, "si": "detectar.cartera.retraso_habito.dias", "no": "fin.sin_alerta"},
        {"id": "detectar.cartera.retraso_habito.dias", "fundamento": "fin-pol-004.s4", "predicado": {"lee": "kpi.retraso_habito.dias_sobre_habito", "op": ">", "umbral": "retraso_habito"}, "si": "hoja.vigia.titular", "no": "fin.sin_alerta"},
    ]
    return data


def test_orq_walkthrough_a_customer_who_paid_in_30_days_is_6_days_late():
    late = {
        "saldo_vencido": [{"cliente_id": "CLI-007", "max_dias_vencido": 6, "saldo_abierto": 900000, "cupo_credito": 5000000}],
        "dias_pago_prom": [{"cliente_id": "CLI-007", "mes_factura": "2026-02-01", "aumento_pct": 20.0}],
        "retraso_habito": [{"cliente_id": "CLI-007", "dias_sobre_habito": 6}],
    }
    base_ctx = Context.of(base_tree(), load_metrics(METRICAS), VIEW_CATALOG, reader_from({DAY: late}))
    assert detect(base_ctx, DAY) == []

    catalog = Catalog({**VIEW_CATALOG.kpis, "retraso_habito": RETRASO})
    data = expanded()
    assert problems(data, grounds(catalog=catalog)) == []
    tree = Tree.model_validate(data)
    (detection,) = detect(Context.of(tree, load_metrics(METRICAS), catalog, reader_from({DAY: late})), DAY)
    assert detection.path[-1] == ("detectar.cartera.retraso_habito.dias", "si")

    recorder = Recorder()
    graph = compiled(recorder, tree=tree, catalog=catalog, rows={DECISION_DAY: {"retraso_habito": [{"cliente_id": "CLI-007", "dias_sobre_habito": 9}]}})
    start_alert(graph, detection, alert_id="A1", day=DAY)
    assert awaiting_decision(graph, "A1")
    final = resume(graph, "A1", approve())
    assert recorder.calls == [("vigia", "titular"), ("analista", "explicar"), ("estratega", "proponer"), ("ejecutor", "ejecutar")]
    assert recorder.received[("ejecutor", "ejecutar")]["action"] == EMAIL
    assert statuses(final) == ["nueva", "en análisis", "propuesta", "ejecutada"]
```

The walkthrough builds version 2 by hand, including two edits of L2 and L3 nodes to attach the new branch; how an agent attaches an expansion is spec 3's, and its validator criteria may refuse these edits later. The test proves the walk, not the move.

- [ ] **Step 2: Run them**

Run: `uv run pytest -v`
Expected: all pass. A failing case is a defect of Task 7's code or of `base.yaml`; fix it there, and never loosen an assertion of this file to make it pass.

- [ ] **Step 3: Tick the mapping**

Tick each row of "Today's 'Nodes and edges', row by row" above whose test passes, and write the test's name beside it. A row with no test name stays unticked and is reported to the user.

- [ ] **Step 4: Ask the user, then commit**

```bash
git add packages/agents/tests/test_orq.py docs/superpowers/2026-10-03-decision-tree-plan.md
git commit -q -F - <<'MSG'
Run the orchestrator's routing cases on the compiled tree with stub leaves, so every route of today's graph is proven without a model

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 9: `request_changes` on screen

**Files:**
- Modify: `apps/web/src/api/types.ts`, `apps/web/src/api/client.ts`, `apps/web/src/screens/ProposedActions.tsx`
- Create: `apps/web/src/screens/ReasonDialog.tsx`
- Delete: `apps/web/src/screens/RejectDialog.tsx`

**Interfaces:**
- Produces: `Decision` gains `{ kind: 'request_changes'; reason: string }`; `ReasonDialog` props `{ open, eyebrow, title, hint, label, missing, failure, confirm, variant: 'danger' | 'primary', icon, onClose, onSend }`.

- [ ] **Step 1: Load the design skill**

Invoke the `arena:design` skill before touching a screen, as `apps/web/AGENTS.md` requires. Run `grep -rn "RejectDialog" apps/web/src`; expected: only `ProposedActions.tsx` and `RejectDialog.tsx`. Another hit is a screen to update in Step 4.

- [ ] **Step 2: Extend the contract**

In `apps/web/src/api/types.ts`, replace

```ts
export type Decision =
  | { kind: 'approve'; actionId: string }
  | { kind: 'edit'; actionId: string; parameters: Record<string, string | number> }
  | { kind: 'reject'; reason: string };
```

with

```ts
export type Decision =
  | { kind: 'approve'; actionId: string }
  | { kind: 'edit'; actionId: string; parameters: Record<string, string | number> }
  | { kind: 'reject'; reason: string }
  | { kind: 'request_changes'; reason: string };
```

- [ ] **Step 3: Serve it in the simulated API**

In `apps/web/src/api/client.ts`, after the line `const logEvents: LogEvent[] = [];` add `const changesRequested = new Set<string>();`. In `decide`, directly after the block that handles `decision.kind === 'reject'` (it ends with `return copy(alert);` and `}`), add:

```ts
  if (decision.kind === 'request_changes') {
    const reason = decision.reason.trim();
    if (!reason) {
      throw new ApiError(422, 'Para pedir cambios hace falta un motivo');
    }
    if (changesRequested.has(alert.id)) {
      throw new ApiError(422, 'Esta alerta ya pidió cambios una vez');
    }
    changesRequested.add(alert.id);
    log(alert.id, 'decision', person, `Cambios solicitados. Motivo: ${reason}`);
    await wait(STEP_DELAY_MS);
    log(alert.id, 'proposal', { kind: 'agent', agent: 'estratega' }, `Propuesta revisada con el motivo: ${reason}`);
    return copy(alert);
  }
```

The alert stays `proposed`, because `request_changes` adds no state to the lifecycle.

- [ ] **Step 4: Generalize the reason dialog**

Create `apps/web/src/screens/ReasonDialog.tsx`:

```tsx
import { useState } from 'react';
import { ArenaButton, ArenaDialog, ArenaTextarea } from '@dravensoft/arena-react';
import { ApiError } from '../api/client';

interface Props {
  open: boolean;
  eyebrow: string;
  title: string;
  hint: string;
  label: string;
  missing: string;
  failure: string;
  confirm: string;
  variant: 'danger' | 'primary';
  icon: string;
  onClose: () => void;
  onSend: (reason: string) => Promise<void>;
}

export function ReasonDialog({ open, eyebrow, title, hint, label, missing, failure, confirm, variant, icon, onClose, onSend }: Props) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | undefined>();
  const [sending, setSending] = useState(false);

  const close = () => {
    setReason('');
    setError(undefined);
    onClose();
  };

  const send = async () => {
    if (!reason.trim()) {
      setError(missing);
      return;
    }
    setSending(true);
    try {
      await onSend(reason.trim());
      setReason('');
      setError(undefined);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : failure);
    } finally {
      setSending(false);
    }
  };

  return (
    <ArenaDialog
      open={open}
      eyebrow={eyebrow}
      title={title}
      fillBelow="sm"
      onClose={close}
      footer={
        <>
          <ArenaButton variant="ghost" onClick={close}>
            Cancelar
          </ArenaButton>
          <ArenaButton variant={variant} icon={icon} loading={sending} onClick={send}>
            {confirm}
          </ArenaButton>
        </>
      }
    >
      <div className="arena-stack arena-stack--group">
        <p>{hint}</p>
        <ArenaTextarea
          label={label}
          required
          rows={4}
          maxLength={500}
          counter
          value={reason}
          error={error}
          onChange={(text) => {
            setReason(text);
            if (text.trim()) {
              setError(undefined);
            }
          }}
        />
      </div>
    </ArenaDialog>
  );
}
```

Run: `git rm apps/web/src/screens/RejectDialog.tsx`.

- [ ] **Step 5: Add the action to the detail**

In `apps/web/src/screens/ProposedActions.tsx`:

1. Replace `import { RejectDialog } from './RejectDialog';` with `import { ReasonDialog } from './ReasonDialog';`.
2. After `const [rejecting, setRejecting] = useState(false);` add `const [requesting, setRequesting] = useState(false);`.
3. In `send`, replace the `if (decision.kind === 'reject') { ... } else { ... }` notification block with:

```tsx
      if (decision.kind === 'reject') {
        notify({ tone: 'neutral', title: 'Propuesta rechazada', message: 'El motivo quedó en la bitácora.' });
      } else if (decision.kind === 'request_changes') {
        notify({ tone: 'neutral', title: 'Cambios solicitados', message: 'La propuesta se revisará con tu motivo.' });
      } else {
        notify({
          tone: 'success',
          title: `Aprobada: ${chosen.title}`,
          message: result.executedAction?.result,
        });
      }
```

4. Add `setRequesting(false);` after both `setRejecting(false);` lines in `send`.
5. Between the `Editar` and `Rechazar` buttons add:

```tsx
        <ArenaButton variant="secondary" icon="ph-bold ph-arrow-counter-clockwise" onClick={() => setRequesting(true)}>
          Solicitar cambios
        </ArenaButton>
```

6. Replace the `<RejectDialog ... />` element with:

```tsx
      <ReasonDialog
        open={requesting}
        eyebrow="Solicitar cambios"
        title="¿Qué debe cambiar en la propuesta?"
        hint="El motivo queda en la bitácora, y la propuesta se revisa una sola vez."
        label="Qué debe cambiar"
        missing="Escribe qué debe cambiar para continuar."
        failure="No se pudo registrar la solicitud. Inténtalo de nuevo."
        confirm="Solicitar cambios"
        variant="primary"
        icon="ph-bold ph-arrow-counter-clockwise"
        onClose={() => setRequesting(false)}
        onSend={(reason) => send({ kind: 'request_changes', reason })}
      />
      <ReasonDialog
        open={rejecting}
        eyebrow="Rechazar"
        title="¿Por qué rechazas la propuesta?"
        hint="El motivo queda en la bitácora junto a tu nombre."
        label="Motivo del rechazo"
        missing="Escribe el motivo del rechazo para continuar."
        failure="No se pudo registrar el rechazo. Inténtalo de nuevo."
        confirm="Rechazar"
        variant="danger"
        icon="ph-bold ph-x"
        onClose={() => setRejecting(false)}
        onSend={(reason) => send({ kind: 'reject', reason })}
      />
```

- [ ] **Step 6: Build and audit**

Run: `npm run build` and `npm run arena:audit` in `apps/web`.
Expected: both exit 0; contrast and ramp warnings are reported, not failed, as `apps/web/AGENTS.md` says. A type error in `client.ts` means a `Decision` branch reaches code that reads `actionId`; the `request_changes` block must come before that code.

- [ ] **Step 7: Ask the user to run the person check**

Ask the user to run `npm run dev`, open an alert in `propuesta` at phone width and by keyboard only, in both themes, and check: the four actions wrap with no horizontal scroll; "Solicitar cambios" with an empty reason shows the error; a reason keeps the alert in the inbox; a second request shows "Esta alerta ya pidió cambios una vez". Wait for the answer.

- [ ] **Step 8: Ask the user, then commit**

```bash
git add apps/web/src
git commit -q -F - <<'MSG'
Let a person request changes to a proposal once, with a reason, so the loop back to `Estratega` the team drew exists on screen

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 10: The level pages

**Files:**
- Modify: `packages/agents/AGENTS.md`, `packages/agents/skills/AGENTS.md`, `apps/api/AGENTS.md`, `evals/AGENTS.md`, `AGENTS.md`, `DOUBTS.md`

**Interfaces:**
- Consumes: the names Tasks 2 to 8 produced; cite them as `path:member(parameters)`.
- Produces: the headings Task 11's `Draws:` captions name, exactly: `## What a leaf may use`, `### The decision tree`, `#### The node`, `#### The levels`, `#### The ends`, `#### The validator`, `#### The node ejecutar.vigente`, `### How a step runs`. The heading `## The orchestrator's graph` stays, because `docs/guide/chapters/alert-journey.md` draws it.

Read each page whole before editing it, and re-read it whole after.

- [ ] **Step 1: `packages/agents/AGENTS.md`, the opening and the files**

Replace `It holds no code yet; this page states the domain each agent is built against.` with `It holds the decision tree, its validator and its interpreter as code; the agents hold no code yet, and this page states the domain each is built against.`

After the opening paragraph, before `## Decisions`, add:

```markdown
## Why each file exists

| Path | Why it exists |
|---|---|
| `arbol/base.yaml` | the base of the decision tree: the laws, and every node, leaf and end the orchestrator walks |
| `arbol/fundamentos.yaml` | the registry: every clause and policy section a node may rest on |
| `centinela_agents/` | the schema of the tree, its validator, the walk of `detectar`, and the compiler to the LangGraph graph |
| `skills/` | what each agent is told ([`skills/AGENTS.md`](./skills/AGENTS.md)) |
| `tests/` | one planted violation per rule of the validator, the walk of `detectar`, and the `ORQ-` cases of [`../../evals/AGENTS.md`](../../evals/AGENTS.md) that need no `apps/api` |
| `pyproject.toml`, `uv.lock` | the package and its pinned dependencies; `uv.lock` is written by uv ([`../../GENERATED.md`](../../GENERATED.md)) |

## Commands

Run from this directory, with [uv](https://docs.astral.sh/uv/), because the Python of the
development machine has no `ensurepip` and uv builds the environment without it:

| Command | What it does |
|---|---|
| `uv sync` | installs the package and its dependencies into `.venv` |
| `uv run pytest` | validates the base tree and runs the routing cases on the compiled graph, with stub leaves and no model |
```

- [ ] **Step 2: `packages/agents/AGENTS.md`, Decisions and the universe**

In the first bullet of "Decisions", replace `The approval is an interrupt before \`Ejecutor\`.` with `The approval is the interrupt at the gate \`aprobar.decision\`, which every path to \`Ejecutor\` passes.`

Add a bullet at the end of "Decisions":

```markdown
- **The kernel reaches the tree through two inputs**: the catalogue of KPI columns the validator
  checks each `lee` against, and a reader the interpreter calls with a metric and a simulated day.
  The tree never opens a connection, because no agent does.
```

In "What the data cannot answer", add a row at the end of the table:

```markdown
| the goals of a customer or of the company, such as a sales target over six months | no table records them |
```

- [ ] **Step 3: `packages/agents/AGENTS.md`, "The domain of each agent" becomes "What a leaf may use"**

Replace the heading `## The domain of each agent` with `## What a leaf may use`, and the sentence under it with:

```markdown
**Each agent answers one question, and no agent answers another's.** Which agent acts next is a
branch of the decision tree, in the next section; what an agent may use once a leaf calls it is
this one, because a tool is a permission, not a route.
```

Keep the table that follows. Then, inside the subsections:

- `### \`Vigía\` detects`: after the `**Tools:**` bullet, add `- **Leaves:** \`detectar\`, the walk of the stage \`detectar\` in code, and \`titular\`, the title.` Replace `- **Ceiling:** it fires only on a threshold in \`metricas.yaml\`, evaluated on the simulated day.` with `- **Ceiling:** it fires only where the walk of \`detectar\` reaches a leaf, which compares a KPI with its \`umbrales\` in \`metricas.yaml\` on the simulated day.` Keep the rest of the bullet.
- `### \`Analista\` explains, and answers the chat`: after `**Tools:**`, add `- **Leaves:** \`explicar\`, and \`responder_chat\` on the chat's own route.`
- `### \`Estratega\` proposes`: replace the `**Input:**` bullet with `- **Input:** the alert, its \`Cause\`, and the rejection reasons kept for its metric, the reason of a \`request_changes\` among them.` and add after it `- **Leaves:** \`proponer\`, and \`revision_manual\`, which is code and calls no model: one \`task\` for a manual review and nothing else, whose \`owner\` is the one \`skills/estratega/acciones.md\` names for the metric. The tree reaches it on \`no_evidence\`, on a second insufficient cause, and on a failed \`proponer\`.`
- `### \`Ejecutor\` acts after approval`: after `**Input:**`, add `- **Leaves:** \`ejecutar\`, for an action whose type has a tool in \`packages/tools\`, and \`nota_manual\`, for one that has none: a \`task\` naming the manual step for a person. Either receives the approved action and the recorded decision, and nothing else of the alert's state.`
- `### The orchestrator routes`: rename it `### The orchestrator interprets the tree`. Replace `It is the only part that knows which step an alert is in, and it decides who goes next. It is code, except one step that classifies a rejection reason. How it routes is the next section.` with `It is the only part that knows which step an alert is in. It walks the decision tree and keeps nothing else to decide: every route is a branch of the tree, and the interpreter decides only how a step runs. It is code, except one step that classifies a rejection reason.` Replace `- **Ceiling:** it moves an alert only along an edge of the graph below,` with `- **Ceiling:** it moves an alert only along a branch of the tree,`. In its `**Input:**` bullet, after `the rejection reasons \`apps/api\` keeps for the alert's metric.` add ` With each, the version of the tree to walk.`

- [ ] **Step 4: `packages/agents/AGENTS.md`, the graph section**

In `### Two runs`, replace `it runs \`Vigía\`'s detection against the earlier alerts, orders the detected alerts,` with `it walks the stage \`detectar\` for every row of every KPI, \`centinela_agents/walk.py:detect(ctx, day)\`, checks each detection against the earlier alerts, orders the detected alerts,` and replace `**The alert graph is LangGraph, one thread per alert, the alert id as the thread id.**` with `**The alert graph is LangGraph, compiled from the tree, one thread per alert, the alert id as the thread id.**`

Replace everything from the heading `### Nodes and edges` up to, not including, `### The state of an alert` with:

````markdown
### The decision tree

**The tree is data, validated by code and walked by a deterministic interpreter; a model acts
only at a leaf.** Its base is [`arbol/base.yaml`](./arbol/base.yaml), beside the registry
[`arbol/fundamentos.yaml`](./arbol/fundamentos.yaml), because routing is the orchestrator's
concern. It is YAML, as `metricas.yaml` is, whose `umbrales` its predicates apply. A client's
version is not a file: `apps/api` keeps it and hands it to each run, because no agent writes
anywhere.

**The tree compiles to the LangGraph graph; an invalid base stops the start.**
`centinela_agents/validator.py:load_base(arbol, metricas, skills, catalog)` validates the base and
raises with every problem. `centinela_agents/graph.py:compile_tree(tree, *, leaves, metrics,
catalog, reader, classify, checkpointer)` makes a graph node of each leaf, each predicate node and
each end reachable from a `vigia` leaf, and a conditional edge out of each predicate node. Each run
compiles the version `apps/api` hands in, cached by its `version`, by
`centinela_agents/graph.py:Compiler`.

**A predicate node is a graph node, not only the function of an edge.** It evaluates its
predicate, records its id and branch in `camino`, applies the write bound to that branch, and its
edge reads the target it chose. So the path an alert walked is in its state, a branch can carry
the orchestrator's own write, and the gate `aprobar.decision` is where the graph pauses: it calls
LangGraph's `interrupt()`, and `centinela_agents/graph.py:resume(graph, alert_id, decision)`
resumes it with the recorded decision.

#### The node

```yaml
- id: detectar.cartera.saldo_vencido.dias
  fundamento: fin-pol-004.s4
  predicado: { lee: kpi.saldo_vencido.max_dias_vencido, op: ">", umbral: saldo_vencido }
  si: hoja.vigia.titular
  no: detectar.cartera.saldo_vencido.cupo
- id: hoja.vigia.titular
  hoja: { agente: vigia, decision: titular, skill: vigia/contrato.md }
  sigue: hoja.analista.explicar
```

| Field | Rule |
|---|---|
| `id` | unique; its first segment is a stage (`detectar`, `explicar`, `proponer`, `aprobar`, `ejecutar`, `cerrar`, `medir`), or `hoja` for a leaf |
| `fundamento` | the id of one entry of the registry; required on a node, absent on a leaf, which inherits its parent's |
| `predicado.lee` | a KPI column (`kpi.<metric>.<column>`), read only in `detectar`, or a field of the alert's state (`estado.<field>`) |
| `predicado.op` | one of `>`, `>=`, `<`, `<=`, `=`, `!=`, `en` (membership in a closed list written in the node), `existe`; quoted in YAML, except `en` and `existe` |
| `predicado.umbral` or `predicado.valor` | `umbral` names a metric of `metricas.yaml` or an approved KPI, and the value compared is its `umbrales` entry for the column `lee` reads; `valor` is a literal, admitted only for a state field |
| `si`, `no` | both required, each a node, a leaf or an end |
| `hoja` | `agente`, a `decision` from that agent's closed list, and `skill`, a file under `skills/` the step starts from |
| `sigue` | on a leaf only: where the walk continues once the agent returns |

| Agent | Its closed list of decisions |
|---|---|
| `vigia` | `detectar` (code), `titular`, `proponer_kpi`, `expandir` |
| `analista` | `explicar`, `responder_chat`, `expandir` |
| `estratega` | `proponer`, `revision_manual` (code), `expandir` |
| `ejecutor` | `ejecutar`, `nota_manual`, `expandir` |

**A predicate holds no literal threshold**, so a threshold stays in `metricas.yaml`; a threshold
whose text has two conditions is two nodes. A comparison with a null value is false, so a row a KPI
cannot measure fires nothing. A `lee` on the state names a field of "The state of an alert" below,
a field of the candidate the day run walks `detectar` with (`estado.candidato.metrica`,
`estado.candidato.descriptivo`), or a field the orchestrator derives when a node reads it:
`estado.same_cause_as.status`, the state of the named alert among the earlier alerts;
`estado.action.type`, the type of the approved action; and `estado.detection.vigente`, below.
`centinela_agents/state.py:STATE_FIELDS` is the list the validator checks.

#### The levels

| Level | Holds | Changed by |
|---|---|---|
| L0 | the laws, `leyes` in the base, each on one entry of the registry | a pull request only |
| L1 | every node whose id names no metric family: each stage's entry, its gates, its capped returns | a pull request only |
| L2 | one branch per metric family, `<stage>.<family>`: `cartera`, `margen`, `inventario`, `comercial`, `abastecimiento`, `clientes` | the stage's agent by self-expansion, or a pull request |
| L3 | the nodes of one metric and their leaves, `<stage>.<family>.<...>` | the stage's agent by self-expansion, or a pull request |

**L1 is every node that names no family, not one node per stage**, because the gates and the
capped returns are the same for every metric and must never move by self-expansion. A leaf's
stage is its agent's. `cerrar` has no node: it is the set of ends below, which `apps/api` closes.
`medir` has no node in the base, because its only decision, `proponer_kpi`, has no leaf in it.

#### The ends

| End | What the interpreter does on reaching it |
|---|---|
| `fin.sin_alerta` | ends the walk of `detectar`: no alert |
| `fin.unida` | writes `merged_into` and proposes `unida` |
| `fin.rechazada` | runs the classifier of the rejection reason; an exception or a target outside its closed list is `ninguno` |
| `fin.recarga_agotada` | ends a second `request_changes`, which `resume` refuses before it reaches the graph |
| `fin.ya_no_aplica` | records that the condition no longer holds; the alert stays `aprobada`, and `Ejecutor` is not called |
| `fin.ejecutada` | proposes `ejecutada` |
| `fin.fallo_ejecucion` | records the failure; the alert stays `aprobada` |

**The orchestrator's own writes are bound to L1 nodes by id**, in
`centinela_agents/graph.py:effects(node_id, branch, state)`, because L1 changes only by pull
request. `explicar.destino_nuevo` on `si` absorbs the named alert into this one and proposes
`unida` for it; on `no` it drops `same_cause_as` and logs it. `proponer.retorno_disponible` on `si`
counts a return to `Analista`. `aprobar.recarga_disponible` on `si` counts the `request_changes`,
keeps its reason in `proposal_rejections`, and clears the decision, so the gate waits again.
Entering an `analista` leaf from `nueva` proposes `en análisis`, and entering `aprobar.decision`
proposes `propuesta` once.

#### The validator

`centinela_agents/validator.py:problems(data, grounds)` refuses a tree where:

- a node fails the schema, or a predicate fails the atomicity test: more than one operand, an
  `umbral` and a `valor` together, `en` without a closed list;
- a node lacks its `fundamento`, its `si` or its `no`, or rests on an id absent from the registry;
- a path from `detectar.raiz` reaches an `Ejecutor` leaf without passing `aprobar.decision` and
  `ejecutar.vigente`;
- the graph has a cycle other than the two capped returns, `proponer` → `explicar` and
  `aprobar.recargar` → `proponer`, each the `si` of a node that reads its counter equal to 0;
- a branch names no node, leaf or end of the closed list, or a node reaches no end;
- a `lee` names a KPI column the catalogue does not hold, a state field `STATE_FIELDS` does not
  declare, or a KPI outside `detectar`, because an alert reads its measure only through
  `ejecutar.vigente`;
- an `umbral` names a metric absent from `metricas.yaml` and from the approved KPIs, or one with no
  threshold for the column `lee` reads;
- a leaf's `skill` is no file under `skills/`, or its `decision` is outside its agent's list;
- a metric of `metricas.yaml` has no L3 branch in `detectar`, no file in `skills/analista/`, or no
  row in `skills/estratega/acciones.md`;
- L0 or an L1 node differs from the base.

The catalogue is an input: the validator checks each `lee` on a KPI against the catalogue it is
handed, never against a database. `uv run pytest` plants one violation per rule.

#### The node ejecutar.vigente

Before every `Ejecutor` leaf, `ejecutar.vigente` reads `estado.detection.vigente`:
`centinela_agents/walk.py:still_breaks(state, ctx)` reads, on the simulated day of the decision,
the KPI row of the alert's entity and re-applies each node of `detectar` the detection passed on
`si`, with the same `umbral`. `si` goes on to `ejecutar.automatizable`; `no`, or no row for the
entity, ends at `fin.ya_no_aplica`. It is code, so `Ejecutor` keeps no discretion, and it rests on
`iso9001.10.2.1.c`: an action addresses a nonconformity, which a resolved one no longer has.

### How a step runs

The fallback of a failed step, the token cap, the retry and the order of a day's alerts are
settings of the interpreter, not nodes, because they decide how a step runs, not which step runs.

**A resume is refused** without a recorded decision id, with a kind outside `approve`, `edit`,
`reject` and `request_changes`, with a reject or a `request_changes` that carries no reason, or with
a second `request_changes`, by `centinela_agents/graph.py:resume(graph, alert_id, decision)`. The
graph never passes the gate on a decision `apps/api` did not record.
````

Then move, unchanged and in this order, under `### How a step runs`, the paragraphs that sat after the old table: "**A transition `apps/api` refuses ends that alert's run**…", "**The loop to `Analista` is capped at one return**…", "**A step fails** when…", and the fallback table. After the paragraph on the loop to `Analista`, add:

```markdown
**A `request_changes` is capped at one per alert**, for the same reason: each pass is a thinking
run on the one loaded model.

**A fallback writes a value, never a route**: the metric's `descripcion` and the entity for the
title, `no_evidence` for the cause, no actions for the proposal, no executed action for `Ejecutor`.
The tree routes each one, at `explicar.con_evidencia`, `proponer.con_acciones` and
`ejecutar.resultado`.
```

- [ ] **Step 5: `packages/agents/AGENTS.md`, the state, routing, order and owners**

In the table of "The state of an alert", change the `proposal_rejections` row's "Written by" to `orchestrator, from its input and from a \`request_changes\``, and add these rows after `status`:

```markdown
| `entry`: the leaf the walk of `detectar` reached | orchestrator | orchestrator |
| `earlier_alerts`: the state of each earlier alert | orchestrator, from its input | orchestrator, for `estado.same_cause_as.status` |
| `proposal_returns` | orchestrator | orchestrator |
| `camino`: each node and the branch it took | orchestrator | `apps/api` |
| `events`: a dropped `same_cause_as` | orchestrator | `apps/api` |
| `next_node`, the target a predicate node chose | orchestrator | orchestrator |
| `fin`: the end the walk reached | orchestrator | `apps/api` |
```

In "Routing", replace `- **A rejection reason goes to the classifier** in \`skills/orquestador/\`,` with `- **A rejection reason goes to the classifier** in \`skills/orquestador/\`, at \`fin.rechazada\`,`.

In "Order", replace `\`unir\` joins this alert to one analysed before it,` and the following `and \`absorber\` joins to this alert one the day run has not reached yet.` with `\`explicar.destino_analizado\` joins this alert to one analysed before it, and \`explicar.destino_nuevo\` joins to this alert one the day run has not reached yet.`

In "What is the orchestrator's, and what is not", replace the row `| the interrupt before \`Ejecutor\` | orchestrator |` with `| the interrupt at \`aprobar.decision\` | orchestrator |`, and add the row `| walking the tree, compiling a version, refusing an invalid base | orchestrator |` after the row on merging.

- [ ] **Step 6: `packages/agents/AGENTS.md`, coverage and rules**

In "Coverage: every rule has one owner per step", replace the `detect` row's last cell with `its L3 branch of \`detectar\` in the tree, and the metric's entry in \`metricas.yaml\`: view, \`umbrales\`, \`fuente_umbral\`, \`pesos_en_riesgo\``. Replace the paragraph from `A metric with no file in \`skills/analista/\`` through the end of its bash block with:

```markdown
**A gap is a refusal.** The validator refuses a metric of `metricas.yaml` with no L3 branch in
`detectar`, no file in `skills/analista/`, or no row in `skills/estratega/acciones.md`, so the
base does not load with a gap. Run from this directory: `uv run pytest tests/test_validator.py`.
```

In "Rules of this level", add as the first bullet:

```markdown
- **A route is a branch of the tree.** No code outside the interpreter decides which step an alert
  takes, so a change of route is a change to `arbol/base.yaml`. *The validator refuses an invalid
  base at startup, and `uv run pytest` holds the routes.*
```

Replace `**An agent is given only the tools its section names.**` with `**An agent is given only the tools its section of "What a leaf may use" names.**`, and in the last rule replace `a change to a skill, a prompt or a graph runs the set in` with `a change to a skill, a prompt or the tree runs \`uv run pytest\` and the set in`.

- [ ] **Step 7: `packages/agents/skills/AGENTS.md`**

Replace

```
model. Within it, every file is always loaded except two: a file named for a metric,
`<metrica>.md`, is loaded only for an alert of that `metrica` or a chat question anchored to one,
and of the table in `estratega/acciones.md` only the rows of the alert's `metrica` are loaded,
because the token cost of each alert is recorded and judged.
```

with

```
model. A leaf of the decision tree names in `skill` the file its step starts from. Within the
directory, every file is always loaded except three: a file named for a decision of its agent
(`expandir.md`, `proponer_kpi.md`) is loaded only when the walk reaches that decision's leaf; a
file named for a metric, `<metrica>.md`, is loaded only for an alert of that `metrica` or a chat
question anchored to one; and of the table in `estratega/acciones.md` only the rows of the alert's
`metrica` are loaded, because the token cost of each alert is recorded and judged.
```

- [ ] **Step 8: `apps/api/AGENTS.md`**

Replace

```
- **The API checks a decision before it resumes an alert**: the role may make it, a rejection
  carries a reason, and an edit keeps the keys of the action's `parameters`, adding none and
  dropping none, because `Ejecutor` passes them unchanged.
```

with

```
- **The API checks a decision before it resumes an alert**: the role may make it, a rejection
  carries a reason, an edit keeps the keys of the action's `parameters`, adding none and dropping
  none, because `Ejecutor` passes them unchanged, and a `request_changes` carries a reason and is
  refused on an alert that already had one, because the return to `Estratega` is capped at one.
- **`request_changes` adds no state to the lifecycle.** The alert stays `propuesta` while
  `Estratega` proposes again, and its reason joins the rejection reasons `Estratega` reads, because
  a person asking for another proposal has neither approved nor rejected the alert.
```

- [ ] **Step 9: `evals/AGENTS.md`**

In the orchestrator row of "The cases of each agent", append to the cases cell, before its closing `|`:

```
; a tree with a missing `no` (refused at startup); a `request_changes` (one re-proposal, a second refused); an action type with no tool (one `task`, through `nota_manual`); an approved action whose KPI no longer breaks on the day of execution (`fin.ya_no_aplica`, `Ejecutor` not called); a path to `Ejecutor` without `aprobar.decision` (refused); a customer who paid in 30 days and is 6 days late (no alert on the base; once a KPI measures it, the walk from `detectar` to `ejecutada`)
```

and replace the row's last cell with `the lifecycle and the \`bitácora\` \`apps/api\` records, \`verificacion_sql\` for the pesos at risk that set the order, and the state of the compiled graph for the routing cases`.

After the table, before "The test copy of a policy", add:

```markdown
**The orchestrator's routing cases run with no model and no `apps/api`**:
[`../packages/agents/tests/test_orq.py`](../packages/agents/tests/test_orq.py) compiles the tree
with stub leaves and a stub KPI reader, one test per case, named for it, and
[`../packages/agents/AGENTS.md`](../packages/agents/AGENTS.md) names the command. The cases that
need `apps/api`'s record (a second `/simulacion/avanzar`, the order of a day's alerts, three
alerts of one cause, a reason handed to the next run of its metric) are not in that file.
```

- [ ] **Step 10: the root `AGENTS.md`**

- Replace `\`apps/web\` holds a scaffold; the other parts hold no code yet.` with `\`apps/web\` holds a scaffold and \`packages/agents\` holds the decision tree's validator and interpreter; the other parts hold no code yet.`
- Replace `On a fresh clone, the first step is \`npm install\` in \`apps/web\`, whose commands are in [\`apps/web/AGENTS.md\`](./apps/web/AGENTS.md).` with `On a fresh clone, the first steps are \`npm install\` in \`apps/web\`, whose commands are in [\`apps/web/AGENTS.md\`](./apps/web/AGENTS.md), and \`uv sync\` in \`packages/agents\`, whose commands are in [\`packages/agents/AGENTS.md\`](./packages/agents/AGENTS.md).`
- In the rule `**A node of the decision tree rests on one entry of the registry**`, replace its closing `*No gate holds this.*` with `*The validator in \`packages/agents\` refuses a node that does not.*`
- In "Verification only a person runs", item 2, replace `After a change to an agent, a prompt or a tool,` with `After a change to an agent, a prompt, a tool or the decision tree,`.

- [ ] **Step 11: `DOUBTS.md`**

At the end of "Filed debts", add:

```markdown
**The base tree reads KPI columns no kernel builds.**
[`packages/agents/arbol/base.yaml`](./packages/agents/arbol/base.yaml) compares columns of
`kpi.<metric>.<column>`, and the validator checks them against the catalogue it is handed. No part
serves that catalogue: the only one is the tests', `packages/agents/tests/support.py:VIEW_CATALOG`,
written as each metric's view columns plus the ones the base reads that no view has. It costs a
base that loads in the tests and fails at startup against the real catalogue, or a detection that
reads a column the kernel names otherwise. It is paid when the kernel builds every column below,
`packages/tools` serves `kpi_catalogo`, and the startup validates against it. Re-derive it with
`grep -o 'kpi\.[a-z0-9_]*\.[a-z0-9_]*' packages/agents/arbol/base.yaml | sort -u`.
```

- [ ] **Step 12: Grep for what the pages still say about the old graph**

Run: `grep -rn "Nodes and edges\|domain of each agent\|esperar_decision\|clasificar_rechazo\|\`unir\`\|\`absorber\`\|\`analizar\`\|coverage command\|interrupt before" --include='*.md' . | grep -v node_modules | grep -v docs/superpowers`
Expected: no hit except `unir` in `docs/guide/chapters/kpi-kernel.md`, which names a key of the kernel's language, and the hits Task 11 rewrites in `docs/guide/chapters/decision-tree.md`. Read every other hit in its file and fix it to the tree's names.

- [ ] **Step 13: Check links and the generated files**

Run the link check of the root `AGENTS.md`, verification item 6; expected: no output. Run `git status --short`; expected: only the six pages of this task modified.

- [ ] **Step 14: Ask the user, then commit**

```bash
git add AGENTS.md DOUBTS.md packages/agents/AGENTS.md packages/agents/skills/AGENTS.md apps/api/AGENTS.md evals/AGENTS.md
git commit -q -F - <<'MSG'
State the decision tree on the agents' page, where routes are branches and each agent's section keeps only what a leaf may use, and file the catalogue the tree reads as a debt

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 11: The guide, and the checks only a person runs

**Files:**
- Modify: `docs/guide/chapters/decision-tree.md`, `docs/guide/chapters/status.md`
- Later, on the user's word: delete this plan and update the spec's status line

**Interfaces:**
- Consumes: the headings Task 10 wrote.

- [ ] **Step 1: The chapter's opening and warning**

In `docs/guide/chapters/decision-tree.md`, replace `This chapter owns what the tree is until [packages/agents](../../../packages/agents/AGENTS.md) states it.` with `What the tree is, [packages/agents](../../../packages/agents/AGENTS.md) states; this chapter keeps what founds it, the walk the team drew, and how the tree grows.`

Replace

```
> **Decided, not implemented.** Only the registry of `fundamentos` exists as a file. No node, no
> validator and no interpreter exist yet.
```

with

```
> **Decided, not implemented.** How the tree grows, below, is a design with no code. The base, its
> validator and its interpreter are code, and [packages/agents](../../../packages/agents/AGENTS.md)
> states them.
```

- [ ] **Step 2: Shrink the node, the levels, the validator and `ejecutar.vigente`**

Replace the whole section `## The node` (from its heading up to, not including, `## The levels and who changes them`) with:

```markdown
## The node, the levels and the validator

What a node holds, the closed decisions of each agent, the levels and who changes each, the ends,
the validator and `ejecutar.vigente` are stated by
[packages/agents](../../../packages/agents/AGENTS.md), its section on the decision tree. The base
itself is [`arbol/base.yaml`](../../../packages/agents/arbol/base.yaml).
```

In `## The levels and who changes them`, keep the mermaid diagram and add directly after its closing fence: `*Draws: \`packages/agents/AGENTS.md\` § The levels*`. Delete the paragraph that starts `The base's L2 families are`. Replace the laws table with the same table without its `fundamento` column, and add after it: `Each law rests on the registry entry its row of \`leyes\` names in the base.` Keep the paragraph "**What never grows at runtime:**".

Delete the sections `## The validator` and `## \`ejecutar.vigente\`` whole.

- [ ] **Step 3: The walkthrough's diagram**

In the walkthrough's mermaid block, replace `G -- reject --> R(["clasificar_rechazo, then end"])` with `G -- reject --> R(["fin.rechazada: the reason is classified"])`, and add after the block's closing fence: `*Draws: \`packages/agents/AGENTS.md\` § The decision tree*`.

- [ ] **Step 4: `status.md`**

In "By part":
- `packages/agents` row: replace `the agents, the orchestrator's graph;` with `the agents, the decision tree and its interpreter;`, and replace `the decision tree, its validator and its growth ([the decision tree](./decision-tree.md)); \`proponer_kpi\`` with `the growth of the decision tree ([the decision tree](./decision-tree.md)); \`proponer_kpi\``.
- `apps/api` row: replace `` `request_changes`, the store of tree versions per client, `` with `the store of tree versions per client, `.
- `evals` row: replace `cases for the tree and the kernel` with `cases for the tree's growth and the kernel`.

- [ ] **Step 5: Build the guide without Docmost**

Run, from `docs/guide`: `python3 publish.py --build-only /tmp/claude-1000/guide-build` (use the session's scratchpad directory if it differs).
Expected: it writes the tree and prints no `draws ... which that page lacks`. A refusal names a caption whose heading differs from Task 10's; fix the caption or the heading, never both at once.

- [ ] **Step 6: The verification list of the root `AGENTS.md`**

Run each, and report each result to the user:

1. Item 2: `uv run pytest` in `packages/agents`; expected: all pass.
2. Item 3: the screen check of Task 9 Step 7, if the user has not run it.
3. Item 4: `git status --short` against `GENERATED.md`; expected: nothing but the files of this task.
4. Item 5: ask the user to publish the guide (`docker compose up -d`, `python publish.py` in `docs/guide`) and read the decision tree chapter and `packages/agents` in Docmost: both diagrams render, and every internal link opens a page.
5. Item 6: the link check; expected: no output.
6. Item 7: read every page this plan touched end to end, for present tense and for a fact stated in two places: the chapter must not restate a table of `packages/agents/AGENTS.md`, and `packages/agents/AGENTS.md` must not restate the spec.

- [ ] **Step 7: Ask the user, then commit**

```bash
git add docs/guide/chapters/decision-tree.md docs/guide/chapters/status.md
git commit -q -F - <<'MSG'
Shrink the guide's decision-tree chapter to what founds the tree and how it grows, and caption its diagrams with the sections they draw

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

- [ ] **Step 8: Ask about the registry debt before any merge**

Ask the user whether a person with the licensed ISO texts has confirmed every entry of `packages/agents/arbol/fundamentos.yaml`, as the registry debt in `DOUBTS.md` requires before the first node cites one. If not, the branch does not merge; say so, and stop here.

- [ ] **Step 9: Once the user confirms the execution is complete, retire the plan**

Delete this plan (`git rm docs/superpowers/2026-10-03-decision-tree-plan.md`) and replace the spec's status line with `**Status:** executed; kept while spec 3 builds on it.`, then ask and commit with the message `Delete the executed decision-tree plan, keeping its spec while the tree's growth builds on it`.
