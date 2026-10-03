# evals: the evaluation set

This level owns the cases that prove Centinela still works: the seeded scenarios it must detect,
the questions it must answer with the right figure, and the attacks it must refuse. The brief
requires the set to run on every significant change, because agent degradation is one of the
risks [`../docs/challenge/AGENTS.md`](../docs/challenge/AGENTS.md) lists. This directory holds only
the case template. The cases that run are pytest tests in the packages whose code they check,
named below; the runner, the case files and the attack fixture are decided and marked.

## Why each file exists

| Path | Why it exists |
|---|---|
| `plantilla_casos_prueba.csv` | the case format the kit suggests, with one example row per case type |

## What checks behaviour

Two test files hold the cases that need no model and no `apps/api`. Each test is one case of the
table below, and its name or its parameters say which.

- **The orchestrator's routing cases**: every `test_orq_*` test of
  [`../packages/agents/tests/test_orq.py`](../packages/agents/tests/test_orq.py) compiles the tree
  with stub leaves and a stub KPI reader and is named for its case.
  [`../packages/agents/AGENTS.md`](../packages/agents/AGENTS.md) names the command. The cases that
  need `apps/api`'s record (a second `/simulacion/avanzar`, the order of a day's alerts, three
  alerts of one cause, a reason handed to the next run of its metric) are not in that file.
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

> **Decided, not built.** The runner, promptfoo; the case ids and the case files; and every case
> below that the two test files above do not hold. A run's traces go to Langfuse, which
> [`../packages/agents/AGENTS.md`](../packages/agents/AGENTS.md) owns.

A case's `id` starts with the agent it tests, `VIG-`, `ANA-`, `EST-` or `EJE-`, or with `ORQ-` for
the orchestrator and `KER-` for the kernel, so the set of one runs alone after a change to its
skills or its graph. The domain each case checks is [`../packages/agents/AGENTS.md`](../packages/agents/AGENTS.md).

| Agent | Cases | The expected answer comes from |
|---|---|---|
| `Vigía` | a simulated day before, during and after each seeded scenario; a day with none (no alert); two days in a row (no duplicate) | the generator's scenario file and `verificacion_sql` |
| `Analista` | the detected alert of each scenario; a decoy alert whose threshold is crossed with no seeded cause (`no_evidence`); chat questions; a test copy of a policy with planted orders | the scenario file (supplier, SKU, dates) and `verificacion_sql` |
| `Estratega` | each correct cause (the actions its row of `packages/agents/skills/estratega/acciones.md` prescribes); a kept rejection reason (that row is dropped); `no_evidence` (one `task`) | the policy section the row cites and `calcular_impacto` checked by `verificacion_sql` |
| `Ejecutor` | an approved action, an edited one, one run twice (one effect), one with no decision (no call), one whose parameters were altered after approval | the draft the tool writes |
| orchestrator | a day with two alerts (the one with the larger pesos at risk reaches `propuesta` first); two alerts with one cause (one `propuesta`, the other `unida` pointing to it); three alerts with one cause (all point to the one that remains, none to a merged alert); a larger alert naming a smaller one still in `nueva` (the smaller is `unida` into the larger); a second `/simulacion/avanzar` during a day run (refused with 409); an `Estratega` fixed to `insufficient_cause` (`Analista` runs twice, then one manual review `task`); one rejection per target, `causa`, `propuesta`, `ambos` and `ninguno` (the next run of the metric hands the reason to that agent only); a resume with no recorded decision (refused, the alert stays `propuesta`, `Ejecutor` is not called); a model call past its timeout (one retry, then the fallback, and the alert still reaches `propuesta`); a tree with a missing `no` (refused at startup); a `request_changes` (one re-proposal, a second refused); an action type with no tool (one `task`, through `nota_manual`); an approved action whose KPI no longer breaks on the day of execution (`fin.ya_no_aplica`, `Ejecutor` not called); a path to `Ejecutor` without `aprobar.decision` (refused); a customer who paid in 30 days and is 6 days late (no alert on the base; once a KPI measures it, the walk from `detectar` to `ejecutada`) | the lifecycle and the `bitácora` `apps/api` records, `verificacion_sql` for the pesos at risk that set the order, and the state of the compiled graph for the routing cases |
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
   `packages/agents/tests/test_orq.py`, and a `KER-` case for a new base KPI follows the checklist
   of [`../packages/tools/AGENTS.md`](../packages/tools/AGENTS.md). Run `uv run pytest` in that
   package, `packages/agents` or `packages/tools`.
2. **Any other case is a row** in the columns of `plantilla_casos_prueba.csv`, with an id that
   starts with its agent's prefix and a `verificacion_sql` that derives its answer. The template
   keeps only its `EJ-` examples; the case files beside it are written with the runner.
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
