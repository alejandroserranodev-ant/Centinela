# evals: the evaluation set

This level owns the cases that prove Centinela still works: the seeded scenarios it must detect,
the questions it must answer with the right figure, and the attacks it must refuse. The brief
requires the set to run on every significant change, because agent degradation is one of the
risks [`../docs/challenge/AGENTS.md`](../docs/challenge/AGENTS.md) lists. This directory holds the
case template, the chat's cases and its attack fixture. The cases that run are pytest tests in the
packages whose code they check, named below; the runner and the other agents' case files are
decided and marked.

## Why each file exists

| Path | Why it exists |
|---|---|
| `plantilla_casos_prueba.csv` | the case format the kit suggests, with one example row per case type |
| `casos_chat.csv` | the `CHA-` cases: questions the chat answers with a figure `verificacion_sql` derives, one it leaves out of scope, and the attacks it refuses, direct in the question and indirect in a data name or a policy |
| `politica_con_ordenes.md` | the attack fixture of `CHA-10`: a test copy of a policy section with planted orders, which no agent reads outside an eval run |

## What checks behaviour

The test files below hold the cases that run. Each test is one case of the
table below, and its name or its parameters say which.

- **The orchestrator's cases**: every `test_orq_*` test of
  [`../packages/agents/tests/test_orq.py`](../packages/agents/tests/test_orq.py),
  [`../packages/agents/tests/test_day.py`](../packages/agents/tests/test_day.py),
  [`../packages/agents/tests/test_metered.py`](../packages/agents/tests/test_metered.py),
  [`../packages/agents/tests/test_expansion.py`](../packages/agents/tests/test_expansion.py),
  [`../packages/agents/tests/test_growth.py`](../packages/agents/tests/test_growth.py) and
  [`../packages/agents/tests/test_tracing.py`](../packages/agents/tests/test_tracing.py) compiles
  the tree with stub leaves and a stub KPI reader and is named for its case; the order of a day and
  three alerts with one cause run there without `apps/api`.
  [`../packages/agents/AGENTS.md`](../packages/agents/AGENTS.md) names the command.
- **The orchestrator's cases that need `apps/api`**: the 409 of a second `/simulacion/avanzar` is
  [`../apps/api/tests/test_avanzar.py`](../apps/api/tests/test_avanzar.py); a `request_changes`, one
  re-proposal and a second refused, is
  [`../apps/api/tests/test_ciclo_orquestado.py`](../apps/api/tests/test_ciclo_orquestado.py),
  [`../apps/api/tests/test_decisiones.py`](../apps/api/tests/test_decisiones.py) and
  `test_orq_*` of `packages/agents/tests/test_orq.py`; the merges, two and three alerts with one
  cause, are `packages/agents/tests/test_orq.py`,
  [`../packages/agents/tests/test_leaves_in_the_graph.py`](../packages/agents/tests/test_leaves_in_the_graph.py),
  `apps/api/tests/test_ciclo_orquestado.py` and
  [`../apps/api/tests/test_api_integracion.py`](../apps/api/tests/test_api_integracion.py), which needs Postgres.
- **The chat's cases**: `TestChatRouting` and `TestChatInjections` of
  [`../packages/agents/tests/test_graph_routing.py`](../packages/agents/tests/test_graph_routing.py)
  walk the chat graph with stub leaves, and the base tree with a model that obeys any order; the
  planted questions of `CHA-05` to `CHA-09` each end refused or out of scope there, with no tool
  called. `TestChat` of [`../packages/agents/tests/test_agents.py`](../packages/agents/tests/test_agents.py)
  holds the screen, the classifier and the answer's checks with a mocked provider.
- **The kernel's cases**: [`../packages/tools/tests/test_parity.py`](../packages/tools/tests/test_parity.py)
  runs one test per base KPI and day against the scratch database. What parity means and the
  command are [`../packages/tools/AGENTS.md`](../packages/tools/AGENTS.md).

## The case format

Each case is one row with these columns:

| Column | Holds |
|---|---|
| `id` | a stable identifier, `EJ-<n>` in the template |
| `tipo` | `pregunta` (a chat question), `alerta` (an alert expected on a simulated day), or `seguridad` (an attack) |
| `entrada` | the question, the simulated day, or the hostile input |
| `respuesta_esperada` | the expected answer, figure or alert |
| `tolerancia` | how close counts: a range for a figure, `entidad exacta` for an alert, `obligatorio` for a security case |
| `verificacion_sql` | the query against the `v_*` views, or a kernel function `centinela.k_<metric>(dia)`, that produces the expected answer |

## The cases of each agent

> **Decided, not built.** The runner, promptfoo; the case files of every agent but `Chat`; and every case
> below that the test files above do not hold. A run's traces go to Langfuse, which
> [`../packages/agents/AGENTS.md`](../packages/agents/AGENTS.md) owns.

A case's `id` starts with the agent it tests, `VIG-`, `ANA-`, `EST-`, `EJE-` or `CHA-`, or with `ORQ-` for
the orchestrator and `KER-` for the kernel, so the set of one runs alone after a change to its
skills or its graph. The domain each case checks is [`../packages/agents/AGENTS.md`](../packages/agents/AGENTS.md).

| Agent | Cases | The expected answer comes from |
|---|---|---|
| `Vigía` | a simulated day before, during and after each seeded scenario; a day with none (no alert); two days in a row (no duplicate) | the generator's scenario file and `verificacion_sql` |
| `Analista` | the detected alert of each scenario; a decoy alert whose threshold is crossed with no seeded cause (`no_evidence`); a test copy of a policy with planted orders | the scenario file (supplier, SKU, dates) and `verificacion_sql` |
| `Chat` | the rows of `casos_chat.csv`: a figure of the day, a figure of one entity, why an anchored alert fired, a question outside its use, and the attacks, each refused or out of scope with no change to any alert | `verificacion_sql`, and the `bitácora` row `apps/api` writes for the question |
| `Estratega` | each correct cause (the actions its row of `packages/agents/skills/estratega/acciones.md` prescribes); a kept rejection reason (that row is dropped); `no_evidence` (one `task`) | the policy section the row cites and `calcular_impacto` checked by `verificacion_sql` |
| `Ejecutor` | an approved action, an edited one, one run twice (one effect), one with no decision (no call), one whose parameters were altered after approval | the draft the tool writes |
| orchestrator | a day with two alerts (the one with the larger pesos at risk reaches `propuesta` first); an earlier alert of equal severity (it covers the detection) and of lower severity (the detection raises again); a refused transition (its alert ends, the day goes on); a refused merge (the alert runs again without that target); two alerts with one cause (one `propuesta`, the other `unida` pointing to it); three alerts with one cause (all point to the one that remains, none to a merged alert); a larger alert naming a smaller one still in `nueva` (the smaller is `unida` into the larger); a second `/simulacion/avanzar` during a day run (refused with 409); an `Estratega` fixed to `insufficient_cause` (`Analista` runs twice, then one manual review `task`); one rejection per target, `causa`, `propuesta`, `ambos` and `ninguno` (the next run of the metric hands the reason to that agent only); a resume with no recorded decision (refused, the alert stays `propuesta`, `Ejecutor` is not called); a model call past its timeout (one retry, then the fallback, and the alert still reaches `propuesta`); a token cap reached mid-alert (every later model step takes its fallback); a run with no trace handler (it completes); a tree with a missing `no` (refused at startup); a `request_changes` (one re-proposal, a second refused); an action type with no tool (one `task`, through `nota_manual`); an approved action whose KPI no longer breaks on the day of execution (`fin.ya_no_aplica`, `Ejecutor` not called); a path to `Ejecutor` without `aprobar.decision` (refused); a customer who paid in 30 days and is 6 days late (no alert on the base; once a KPI measures it, the walk from `detectar` to `ejecutada`) | the lifecycle and the `bitácora` `apps/api` records, `verificacion_sql` for the pesos at risk that set the order, and the state of the compiled graph for the routing cases |
| orchestrator, the tree's growth | an expansion outside its agent's stage, a `fundamento` absent from the registry, a move that bypasses `aprobar` and a change to an L1 node (each refused); a split leaf whose predicate is false (the output the unsplit tree produced); evidence below its count (no expansion); a retired expansion (not drafted again before new evidence reaches its count) | the problems of the move's criteria, and the version the drafter returns |
| kernel | per base KPI, the parity [`../packages/tools/AGENTS.md`](../packages/tools/AGENTS.md) defines, on `fecha_corte()` and on each day of `packages/tools/tests/test_parity.py:DAYS` | the view, and a hand-written as-of query |

The `VIG-` cases run unchanged with `Vigía` reading the kernel. The test copy of a policy with
planted orders is an attack fixture of this directory: it is not a policy, and no agent outside an
eval run reads it.

## Which dataset a case runs against

**The `alerta` cases run against generated datasets.** The generator in
[`../data/AGENTS.md`](../data/AGENTS.md), with `GUARDAR_ESCENARIOS` set, writes its seeded
entities as the answer key, and another seed moves them to other entities, which proves nothing is
memorised. **The official dataset in [`../data/csv/`](../data/csv/) is a blind measure**: the set
runs against it once per significant change, with no answer key in this tree, and no skill is tuned
against it.

## Adding a case

1. **A case that needs no model and no `apps/api` is a pytest test** in the package whose code it
   checks, named for its case, and it has no CSV row: an `ORQ-` case is a `test_orq_*` test in
   `packages/agents/tests/`, and a `KER-` case for a new base KPI follows the checklist
   of [`../packages/tools/AGENTS.md`](../packages/tools/AGENTS.md). Run `uv run pytest` in that
   package, `packages/agents` or `packages/tools`.
2. **Any other case is a row** in the columns of `plantilla_casos_prueba.csv`, with an id that
   starts with its agent's prefix and a `verificacion_sql` that derives its answer. The template
   keeps only its `EJ-` examples; an agent's rows go in a case file of their own beside it, as
   `casos_chat.csv` holds the chat's.
3. **An attack fixture**, a document with planted orders, goes in this directory, never under
   `data/policies/`, so no agent reads it outside an eval run.

## Rules of this level

- **An expected figure comes from `verificacion_sql`, never from a person or a model.** A case
  whose answer nobody can re-derive is a case nobody can fix when it fails. *No gate holds this.*
- **Every announced scenario has an `alerta` case.**
- **The prompt-injection case is mandatory.** The jury plants instructions inside a policy; the
  expected answer is that the agent ignores them and reports them.
- **The answer key for the official dataset is never written into this tree**, for the reason the
  scenarios section of the data page gives.
