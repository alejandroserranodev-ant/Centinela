# evals: the evaluation set

This level owns the cases that prove Centinela still works: the seeded scenarios it must detect,
the questions it must answer with the right figure, and the attacks it must refuse. The brief
requires the set to run on every significant change, because agent degradation is one of the
risks [`../docs/challenge/AGENTS.md`](../docs/challenge/AGENTS.md) lists. The runner is promptfoo;
traces of a run go to Langfuse.

## Why each file exists

| Path | Why it exists |
|---|---|
| `plantilla_casos_prueba.csv` | the case format the kit suggests, with one example row per case type |

## The case format

Each case is one row with these columns:

| Column | Holds |
|---|---|
| `id` | a stable identifier, `EJ-<n>` in the template |
| `tipo` | `pregunta` (a chat question), `alerta` (an alert expected on a simulated day), or `seguridad` (an attack) |
| `entrada` | the question, the simulated day, or the hostile input |
| `respuesta_esperada` | the expected answer, figure or alert |
| `tolerancia` | how close counts: a range for a figure, `entidad exacta` for an alert, `obligatorio` for a security case |
| `verificacion_sql` | the query against the `v_*` views that produces the expected answer |

## The cases of each agent

A case's `id` starts with the agent it tests, `VIG-`, `ANA-`, `EST-` or `EJE-`, so the set of one
agent runs alone after a change to its skills. The domain each case checks is
[`../packages/agents/AGENTS.md`](../packages/agents/AGENTS.md).

| Agent | Cases | The expected answer comes from |
|---|---|---|
| `Vigía` | a simulated day before, during and after each seeded scenario; a day with none (no alert); two days in a row (no duplicate) | the generator's scenario file and `verificacion_sql` |
| `Analista` | the detected alert of each scenario; a decoy alert whose threshold is crossed with no seeded cause (`no_evidence`); chat questions; a test copy of a policy with planted orders | the scenario file (supplier, SKU, dates) and `verificacion_sql` |
| `Estratega` | each correct cause (the actions its row of `packages/agents/skills/estratega/acciones.md` prescribes); a kept rejection reason (that row is dropped); `no_evidence` (one `task`) | the policy section the row cites and `calcular_impacto` checked by `verificacion_sql` |
| `Ejecutor` | an approved action, an edited one, one run twice (one effect), one with no decision (no call), one whose parameters were altered after approval | the draft the tool writes |

The test copy of a policy lives in this directory as an attack fixture; it is not a policy, and no
agent outside an eval run reads it. **Practice runs use generated datasets only**; the official
dataset is run once per significant change as a blind measure, and no skill is tuned against it.

## Rules of this level

- **An expected figure comes from `verificacion_sql`, never from a person or a model.** A case
  whose answer nobody can re-derive is a case nobody can fix when it fails. *No gate holds this.*
- **Every announced scenario has an `alerta` case**, and the official dataset in
  [`../data/csv/`](../data/csv/) is the one they run against.
- **The prompt-injection case is mandatory.** The jury plants instructions inside a policy; the
  expected answer is that the agent ignores them and reports them.
- **A generated dataset proves nothing is memorised.** Run the `alerta` cases against a dataset
  from the generator in [`../data/AGENTS.md`](../data/AGENTS.md), with `GUARDAR_ESCENARIOS` set so
  its seeded entities become the answer key.
- **The answer key for the official dataset is not written into this tree before the close**,
  for the reason the scenarios section of the data page gives.
