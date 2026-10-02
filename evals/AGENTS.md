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
