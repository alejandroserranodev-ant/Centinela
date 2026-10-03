# packages/agents/arbol: how the decision tree is written

The decision tree is every route an alert can take, written as data: atomic rules, each resting on
one entry of a registry, whose leaves are the decisions of an agent. This page decides how a node,
a leaf and an end are written, what the validator refuses, and where each kind of change lands.
What runs: the base below is parsed, validated, walked in `detectar` and compiled to the LangGraph
graph, and `uv run pytest` holds all four. What is decided, not built: a client's own version of
the tree, its growth by self-expansion, and the caps on that growth; each section that states one
opens with the marker. How the compiled graph runs an alert is [`../AGENTS.md`](../AGENTS.md).

## Why each file exists

| Path | Why it exists |
|---|---|
| `base.yaml` | the base every client shares: the laws, `leyes`, and every node, leaf and end the orchestrator walks. A change to it is a pull request, and the validator compares every version with it |
| `fundamentos.yaml` | the registry: every clause of a standard and every policy section a node or a law may rest on, each with its `cita` and what it `funda`. Only a person adds to it |

## The tree

**The tree is data, validated by code and walked by a deterministic interpreter; a model acts
only at a leaf.** Routing is the orchestrator's concern, so the base sits beside the code that
walks it. It is YAML, as `data/metricas.yaml` is, whose `umbrales` its predicates apply.

**Every entry of the registry that cites a standard names a numbered clause, confirmed against its
licensed text before a node rests on it.** The texts are licensed and are not in the repository, so
the person who adds an entry confirms its clause in the review of its pull request, and an entry
with no clause number is refused there, because no reader can check it. A standard founds
structure, never a threshold: a node founded on an ISO clause compares a state, and a node that
compares a KPI rests on the policy section or the kit entry its threshold quotes in
`fuente_umbral`.

> **Decided, not built.** A client's version of the tree is not a file: `apps/api` keeps it and
> hands it to each run, because no agent writes anywhere.
> `centinela_agents/graph.py:Compiler` caches a graph per version and content, so two
> clients may hold different trees under one version number.

## The stages

Each node's id starts with its stage, and the stages follow ISO 31000 §6.4 to §6.7 and ISO 9001
§10.2, the registry entries their L1 nodes rest on. A stage that needs a business measure reads it
from the kernel, the one place an agent obtains a measure to compare or to cite; a fact the kernel
does not measure, such as a price in force, comes from a `v_*` view.

| Stage | Who decides | Consults the kernel for |
|---|---|---|
| `detectar` | `Vigía`, in code | the KPI a threshold compares: `centinela_agents/walk.py:detect(ctx, day)` |
| `explicar` | `Analista` | testing each hypothesis, with base, approved and descriptive KPIs. *Decided, not built*, and the skill names no kernel tool |
| `proponer` | `Estratega` | the figures an impact is computed from, through `calcular_impacto`. *Decided, not built* |
| `aprobar` | a person | nothing; the gate reads the recorded decision |
| `ejecutar` | `Ejecutor` | that the KPI which justified the action still breaks its threshold, in code, at [`ejecutar.vigente`](#the-node-ejecutarvigente). `Ejecutor`'s model consults nothing |
| `cerrar` | `apps/api` | nothing: it is the set of ends, which `apps/api` closes |
| `medir` | `Vigía` | validating and dry-running a candidate KPI. *Decided, not built*: no node of the base is in `medir` |

`cerrar` records the action, its result and who made it. Whether the metric of an executed alert
returns inside its threshold on later simulated days is the effectiveness review ISO 9001 §10.2.1 d)
names, and it is decided, not built.

## The node

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
| `id` | unique; a node's first segment is a stage of `centinela_agents/schema.py:STAGES`, and a leaf's is `hoja` |
| `fundamento` | the id of one entry of the registry; required on a node, absent on a leaf, which inherits its parent's |
| `predicado.lee` | a KPI column, `kpi.<metric>.<column>`, read only in `detectar`; or a field of the alert's state, `estado.<field>` |
| `predicado.op` | one of `centinela_agents/schema.py:Operator`; `en` is membership in a closed list written in the node, `existe` tests that a value is present. Quoted in YAML, except `en` and `existe` |
| `predicado.umbral` | on a KPI only: a metric of `data/metricas.yaml` or an approved KPI, whose `umbrales` entry for the column `lee` reads is the value compared |
| `predicado.valor` | on a state field only: a literal, or a non-empty list with `en`; none with `existe` |
| `si`, `no` | both required, each a node, a leaf or an end |
| `hoja` | `agente`, a `decision` of that agent's closed list, `centinela_agents/schema.py:AGENT_DECISIONS`, and `skill`, the file under [`../skills/`](../skills/AGENTS.md) the step starts from |
| `sigue` | on a leaf only, required: where the walk continues once the agent returns |

**The atomicity test.** A node is atomic when its predicate holds one operand, one operator and no
`and`, `or` or `not`, and its `fundamento` names one entry of the registry. A node that splits into
two independent predicates is two nodes, and a threshold whose text has two conditions is two
nodes, because the atomic node is the unit a client changes.

**A predicate holds no literal threshold**, so a threshold stays in `data/metricas.yaml`. A
comparison with a null value is false, so a row a KPI cannot measure fires nothing. A threshold is
a number, a boolean, `{columna}` naming a column of the same KPI row, or `{por, valores}` keyed by a
column of the row, `centinela_agents/metrics.py:threshold_shape_problem(spec)`.

> **Limit.** `centinela_agents/catalog.py:catalog_from_kernel(answer)` never fills
> `centinela_agents/catalog.py:Kpi`'s `thresholds`, because `kpi_catalogo` returns none. An `umbral`
> naming an approved KPI therefore resolves only in the tests, which build that catalogue by hand.

**A `lee` on the state names a field of `centinela_agents/state.py:STATE_FIELDS`**: a field of the
alert's state, a field of the candidate the walk of `detectar` carries (`estado.candidato.metrica`,
`estado.candidato.descriptivo`), or one of `centinela_agents/state.py:DERIVED_FIELDS`, which
`centinela_agents/walk.py:read(state, path, ctx)` derives when a node reads it: the state of the
alert `same_cause_as` names among the earlier alerts, the type of the approved action, and
`estado.detection.vigente`, below.

**The tree's YAML reads only `true` and `false` as booleans**, through
`centinela_agents/yaml_loader.py:StrictBoolLoader`, because YAML 1.1 reads the key `no` and the
values `yes`, `on` and `off` as booleans, which would turn every `no` branch into `False`. A `valor`
that spells a boolean another way is refused, since it would be text that never equals one.

## The levels

`centinela_agents/schema.py:level(node_id)` reads a node's level from its id.

| Level | Holds | Changed by |
|---|---|---|
| L0 | the laws, `leyes`, each on one entry of the registry | a pull request only |
| L1 | every node whose id names no metric family: each stage's entry, its gates, its capped returns | a pull request only |
| L2 | one branch per metric family, `<stage>.<family>`, the families of `centinela_agents/schema.py:FAMILIES` | the stage's agent by self-expansion, or a pull request |
| L3 | the nodes of one metric, `<stage>.<family>.<...>` | the stage's agent by self-expansion, or a pull request |

**L1 is every node that names no family, not one node per stage**, because the gates and the
capped returns are the same for every metric and must never move by self-expansion. A leaf's stage
is its agent's, `centinela_agents/schema.py:AGENT_STAGE`. A leaf names no family either, but the
validator holds it apart: a leaf of the base keeps its agent, its decision and its `sigue`, and a
new leaf is allowed, so a branch grows without rerouting the base.
The laws are not branches: the interpreter is to check them on every step, and a step that breaks
one fails, which is decided, not built.

## The ends

`centinela_agents/schema.py:ENDS` is the closed list; `centinela_agents/graph.py:end_node(end_id,
classify)` is what the interpreter does on reaching each.

| End | What the interpreter does |
|---|---|
| `fin.sin_alerta` | ends the walk of `detectar`: no alert |
| `fin.unida` | writes `merged_into` and proposes `unida` |
| `fin.rechazada` | runs the classifier of the rejection reason; an exception or a target outside `centinela_agents/graph.py:REJECTION_TARGETS` is `ninguno` |
| `fin.recarga_agotada` | ends a second `request_changes`, which the resume refuses before it reaches the graph |
| `fin.ya_no_aplica` | records that the condition no longer holds; the alert stays `aprobada`, and `Ejecutor` is not called |
| `fin.ejecutada` | proposes `ejecutada` |
| `fin.fallo_ejecucion` | records the failure; the alert stays `aprobada` |

## The orchestrator's writes

**The orchestrator's own writes are bound to L1 nodes by id**, in
`centinela_agents/graph.py:effects(node_id, branch, state)`, because L1 changes only by pull
request; `centinela_agents/graph.py:BOUND_NODES` lists them, and a test holds that each is in the
base. `explicar.destino_nuevo` on `si` absorbs the named alert into this one and proposes `unida`
for it; on `no` it drops `same_cause_as` and logs `same_cause_dropped`.
`proponer.retorno_disponible` on `si` counts a return to `Analista`. `aprobar.recarga_disponible`
on `si` counts the `request_changes`, keeps its reason in `proposal_rejections`, and clears the
decision, so the gate waits again. Entering an `analista` leaf from `nueva` proposes `en análisis`,
and entering `aprobar.decision` proposes `propuesta` once, `centinela_agents/graph.py:entering(target,
state, nodes)`. A leaf that runs again clears the outputs of its decision it does not return,
`centinela_agents/graph.py:LEAF_OUTPUTS`, so a second proposal never keeps the first's
`insufficient_cause`.

## The node ejecutar.vigente

Before every `Ejecutor` leaf, `ejecutar.vigente` reads `estado.detection.vigente`:
`centinela_agents/walk.py:still_breaks(state, ctx)` reads, on the simulated day of the decision,
the KPI row of the alert's entity and re-applies each node of `detectar` the detection passed on
`si`, with the same `umbral`. `si` goes on to `ejecutar.automatizable`; `no`, no row for the
entity, or a path none of whose KPI nodes is left in the tree, ends at `fin.ya_no_aplica`, because
nothing runs on a condition no node can check again. Two rows for one entity raise, and the resume
fails, because the entity is the key of the KPI and a second row breaks the kernel's contract. It is
code, so `Ejecutor` keeps no discretion, and it rests on `iso9001.10.2.1.c`: an action addresses a
nonconformity, which a resolved one no longer has.

## The validator

`centinela_agents/validator.py:problems(data, grounds)` returns every problem of a tree, and
`centinela_agents/validator.py:load_base(arbol, metricas, skills, catalog)` raises with all of
them, so an invalid base stops the start. **`tests/test_validator.py:PLANTED` is the complete list
of what it refuses**, one planted violation per rule, each named for the rule it breaks; a rule
that never fires fails there, and the base itself must pass with no problem. Its families:

- the schema, the shape of a node or a leaf, and the atomicity of its predicate;
- a `fundamento` or a law resting on an id absent from the registry;
- a path from `detectar.raiz` to an `Ejecutor` leaf that skips `aprobar.decision` or
  `ejecutar.vigente`;
- a cycle other than the two capped returns, each reading the counter `effects` keeps equal to 0;
- a branch to nothing, a node that reaches no end, a node `detectar.raiz` does not reach;
- a `lee` the catalogue or `STATE_FIELDS` does not declare, a KPI read outside `detectar`, or a KPI
  read where the candidate may be another metric;
- an `umbral` that names no threshold for its column, or one of no admitted shape;
- a leaf whose agent, decision or `skill` is unknown;
- a metric of `data/metricas.yaml` with no L3 branch in `detectar`, no `skills/analista/<metric>.md`,
  or no row in [`skills/estratega/acciones.md`](../skills/estratega/acciones.md), which
  `centinela_agents/validator.py:coverage_problems(tree, grounds)` reads;
- L0, an L1 node or a leaf of the base that differs from the base, or an L1 node the base lacks.

The catalogue is an input: the validator checks each `lee` on a KPI against the catalogue it is
handed, never against a database.

## How the tree grows

> **Decided, not built.** No code grows the tree; the leaf `expandir` is in each agent's closed
> list and in no node of the base.

| What grows | By | Who | Bound | Before it takes effect |
|---|---|---|---|---|
| L2 and L3 | self-expansion | any agent, inside its own stage | the registry, the laws, the validator | nothing; it is recorded, versioned and retirable |
| any level | a pull request against `base.yaml` | a person | the validator and `uv run pytest` | review |
| the registry | a new clause or policy section | a person, by pull request | the clause exists in its standard or in `data/policies/` | review |

**What never grows at runtime**: L0, L1, the registry, the kernel's language, the list of tools,
the closed decisions of each agent, and the dataset. Each bounds what does grow, and a bound that
moves with what it bounds is no bound.

- **An agent expands the tree only inside its own stage**, with leaves of its own label: `Vigía` in
  `detectar` and `medir`, `Analista` in `explicar`, `Estratega` in `proponer`, `Ejecutor` in
  `ejecutar`. `aprobar` and `cerrar` have no agent and grow by pull request only, because each stage
  has one owner and an agent that rewrites another's stage would decide what that one does.
- **An expansion rests only on what the tree already holds**: its `fundamento` is a registry entry,
  its operand a KPI of the catalogue or a declared state field, its threshold an `umbral`. An agent
  cannot introduce a standard, a policy section or a threshold, which is why only a person grows
  the registry.
- **No person approves an expansion before it runs**, because every path to an `Ejecutor` leaf
  still passes `aprobar.decision` and `ejecutar.vigente`, which the validator holds: an expansion
  changes which leaf decides and on what, never what reaches the world.
- **An expansion is an output, never a write.** The agent returns it, the orchestrator validates
  it, and `apps/api` persists it as a new version, writes it to the `bitácora`, and lets the
  administrator retire it at any time.
- **Growth is capped by settings sized to the machine**, as the model is: the depth of a path, the
  nodes per stage, and the active approved KPIs per client, because a walk and its skill must fit
  the context of a 4 to 8 billion parameter model, and a tree no model can read is a tree no agent
  uses.

## Adding to the tree

Each list is in the order the change is made. `uv run pytest`, from `packages/agents`, closes each.

**A metric.**

1. Its entry and `kernel:` block in `data/metricas.yaml`, with an `umbrales` entry for each column
   a node compares; then regenerate the base KPIs, as [`packages/tools`](../../tools/AGENTS.md)
   states.
2. The metric in the `en` list of its family's node, `detectar.<family>`. A new family is also an
   entry of `centinela_agents/schema.py:FAMILIES`, and its node joins the chain of families.
3. Its L3 branch: a node `detectar.<family>.<metric>` that tests `estado.candidato.metrica`, then
   one atomic KPI node per condition of its threshold, each on the registry entry of its policy
   section, the last one's `si` at `hoja.vigia.titular`.
4. `skills/analista/<metric>.md`, as [`../skills/AGENTS.md`](../skills/AGENTS.md) orders.
5. Its rows in both tables of `skills/estratega/acciones.md`: its actions, and the owner of its
   manual review.
6. A row of `tests/test_detect.py:FIRING` per KPI node, holding only columns its KPI returns.
7. Its name in `apps/web/src/api/types.ts:Metric`, and its `alerta` case, as
   [`evals/AGENTS.md`](../../../evals/AGENTS.md#adding-a-case) orders.

**A node or a predicate.** A new state field a `lee` names joins
`centinela_agents/state.py:STATE_FIELDS`, and `centinela_agents/state.py:AlertState` when a step
writes it; a derived field also joins `centinela_agents/state.py:DERIVED_FIELDS` and
`centinela_agents/walk.py:read(state, path, ctx)`. Its `fundamento` is an entry the registry
already holds, or a pull request adds one. An L1 node changes only by a pull request against
`base.yaml`.

**An end.** `centinela_agents/schema.py:ENDS`, what it does in
`centinela_agents/graph.py:end_node(end_id, classify)`, and, when it proposes a state, the lifecycle
of [`apps/api`](../../../apps/api/AGENTS.md).

**An orchestrator write.** A branch of `centinela_agents/graph.py:effects(node_id, branch, state)`
and its node in `centinela_agents/graph.py:BOUND_NODES`; the node is L1, so it is a pull request.

**An agent decision.** `centinela_agents/schema.py:AGENT_DECISIONS`; the outputs it clears in
`centinela_agents/graph.py:LEAF_OUTPUTS`; the value it falls back to in
`centinela_agents/graph.py:fallback(leaf, state, error, ctx)`; its leaf in `base.yaml`; the
function the host hands `compile_tree` for it, and its stub in `tests/support.py:DEFAULT_LEAVES`,
because a leaf with no function is refused at compile; and its skill.

**An action type.** The type in the `en` list of `ejecutar.automatizable`, an L1 node, so a pull
request, once [`packages/tools`](../../tools/AGENTS.md) holds its tool; its rows in
`skills/estratega/acciones.md`; and `apps/web/src/api/types.ts:ActionType`. A type with no tool
needs none of this: it reaches a person through `nota_manual`.
