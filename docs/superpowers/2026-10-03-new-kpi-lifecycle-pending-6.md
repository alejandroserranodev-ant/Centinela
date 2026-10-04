# Spec 6 of 6: how a new KPI is born

**Status:** pending its plan. **Depends on:** spec 3, `tree-expansion`, because a new KPI exists to
let a node enter the tree; spec 5, `current-kpis-in-kernel`, because the kernel must already carry
the current metrics; spec 4, `kpi-kernel`, for the approved kind of KPI, held as frozen SQL in
`apps/api`'s catalogue.

**Executed specs.** Specs 1, 2, 3, 4 and 5 are executed and deleted, and a reference below to one of them
reads as a reference to the page that now states it: spec 1, the foundations and the scope of growth,
is [`packages/agents/arbol/AGENTS.md`](../../packages/agents/arbol/AGENTS.md); spec 2, the tree, is
the same page; spec 3, how the tree grows, is that page's *How the tree grows*, which holds the move
`agregar_rama` this spec's `Vigía` drafts on, and *The tree's versions* of
[`apps/api/AGENTS.md`](../../apps/api/AGENTS.md); spec 4, the kernel, is the language in [`data/AGENTS.md`](../../data/AGENTS.md) and the
tools in [`packages/tools/AGENTS.md`](../../packages/tools/AGENTS.md); spec 5, the base KPIs, is
[`data/AGENTS.md`](../../data/AGENTS.md).

## Why

The current metrics may not suffice for a client's decisions. The case the team drew proves it: a
customer who always paid in 30 days is 6 days late, `FIN-POL-004 §4` prescribes a reminder from day
1, and no metric fires (`saldo_vencido` above 15 days, `dias_pago_prom` above a 50% rise). Centinela
must notice that it lacks a measure, propose one, and make it available, while **no person and no
text can make it build a measure**: a person who writes a KPI can write an expensive one or carry
an injection into SQL. The flow is therefore one way: **a signal, a repetition counted in code, a
proposal by `Vigía` in the kernel's language, and a person's approval, which activates it.**
Nothing is created in a database at any step, because no agent changes a database (spec 1).

## Decisions

- **The signal is shared, the proposal is `Vigía`'s.** `Analista`, `Estratega` and the tree's
  validator emit a `kpi_gap` as an output; `Vigía` owns the catalogue of measurement (ISO 9001
  §9.1.1) and writes the proposal. `Analista` meets the gap but answers "why", and proposing a
  measure is not an explanation.
- **Detection stays rules; the proposal is a new model step.** `Vigía`'s detection keeps no model.
  The leaf `vigia`/`proponer_kpi` runs with thinking on, and its output schema is the kernel's
  language, so the model can only fill fields the language has.
- **Approval activates; nothing is deployed.** On approval, `apps/api` marks the stored proposal,
  with its frozen compiled SQL and hash, as active in the client's catalogue, and hands it to the
  next run. No agent runs a step after the approval, because the approval changes no database and
  no world outside `apps/api`'s own record.
- **The administrator approves or rejects; nobody edits.** An edit of a proposal is authoring a
  KPI, which is the thing the flow exists to prevent. No endpoint accepts a `kernel:` block from a
  person.
- **A gap is a threshold gap or a measure gap, and only a measure gap reaches the kernel.** When
  an existing KPI already measures the need and only its threshold would have to change, the gap is
  reported to the administrator as a threshold gap and nothing is proposed, because a threshold
  changes only by a document (`data/AGENTS.md`).

## The signal

A `kpi_gap` is structured, and no field holds free text from a policy, the chat or a person:

| Field | Holds |
|---|---|
| `origen` | `analista` (no KPI or view tests a hypothesis of its skill), `estratega` (an action's `impact` is `null` because no formula exists), `arbol` (an expansion needs an operand the catalogue lacks, spec 3) |
| `ancla` | the hypothesis id of the skill, the action row of `acciones.md`, or the node id |
| `pregunta` | the GQM question as a closed shape: entity type, the `medida` and `linea_base` the need asks for, the source table |
| `entidad`, `dia` | the alert's entity and the simulated day |
| `clase` | `medida` or `umbral`, decided in code by checking whether a KPI of the client's catalogue already has that shape |

The agent returns the gap; `apps/api` persists it in its own schema and writes it to the `bitácora`.

## The repetition

**A gap becomes a candidate when its `pregunta` repeats at least N times over at least M distinct
simulated days or entities**, counted in code by `apps/api` over the persisted gaps, keyed by the
hash of `pregunta`. N and M are settings of the method, like the windows of an `analista/` skill:
they decide when a proposal is drafted, never whether an alert fires, and they are never presented
as a business rule. A candidate whose `pregunta` was rejected before is not drafted again until N
new gaps arrive after the rejection.

## The proposal

`vigia`/`proponer_kpi` receives the candidate (the `pregunta`, its anchors, the entities and days)
and returns:

| Output | Rule |
|---|---|
| the `kernel:` block | the language of spec 4, nothing else |
| the ISO 22400-2 fields | name, description, unit, range, trend, timing, audience |
| `justificacion` | GQM: goal = the node or anchor, question = the `pregunta`, metric = this KPI; plus the count of gaps and their ids |
| `umbral_alerta` and `fuente_umbral` | both or neither: a threshold quotes a policy section; with neither, the KPI is descriptive |

Code then runs `kpi_validar` and `kpi_dry_run` on the current simulated day. A refusal goes back
to `proponer_kpi` once with the guard named; a second refusal drops the candidate and logs it. A
proposal that passes is handed to `apps/api` with its compiled SQL, its hash, the compiler version,
its dry-run rows, row count and time, and its planner cost.

A threshold an approved KPI carries needs an entry in `metricas.yaml` for a node's `umbral` to name
(spec 2). Until a person promotes the KPI (spec 4), its threshold lives in its catalogue entry with
its `fuente_umbral`, and the validator of spec 2 accepts an `umbral` that names an approved KPI of
the client's catalogue as it accepts a `metricas.yaml` entry.

## The lifecycle of a proposal

Owned by `apps/api`, separate from an alert's:

| Transition | Proposed by |
|---|---|
| → `kpi_propuesta` | the orchestrator, when the proposal passes validation and dry run |
| `kpi_propuesta` → `kpi_activa` or `kpi_rechazada` | `apps/api`, from the administrator's decision; a rejection carries a reason, which returns to `proponer_kpi` with the next candidate of the same `pregunta` |
| `kpi_activa` → `kpi_retirada` | `apps/api`, from the administrator's decision; the tree's nodes that read it are retired with it (spec 3) |
| `kpi_activa` → `kpi_promovida` | `apps/api`, when a person's pull request moves the definition into `metricas.yaml` (spec 4) |

Only the `administrador` role decides. A `kpi_activa` is handed to every run of the client, and the
kernel runs its stored SQL only when the hash matches.

## Endpoints and screen

| Method | Path | Purpose |
|---|---|---|
| GET | `/kpis` | the catalogue, base and approved, with each KPI's ISO 22400-2 fields and whether it is descriptive |
| GET | `/kpis/propuestas` | proposals in `kpi_propuesta`, with justification, compiled SQL, dry run and cost |
| POST | `/kpis/propuestas/{id}/decision` | `approve` or `reject` with a reason; no other body is accepted |
| POST | `/kpis/{id}/retiro` | retire an approved KPI, with a reason |

In `apps/web`, the screen `Configuración` gains the catalogue and the proposals inbox. A proposal
shows its justification first, then the dry-run rows, then the SQL under "cómo llegué aquí". It has
two actions, approve and reject, and no edit.

## The demonstration case

The case of the diagram, run on a generated dataset so no seeded entity of the official one is
named: a customer whose invoices are late 1 to 15 days against a history of paying on time.

1. `Analista` emits gaps for its hypothesis "the customer departs from their own payment habit".
2. The repetition makes a candidate.
3. `proponer_kpi` proposes a KPI of days past due per open invoice against the customer's median
   historical days to pay, with `fuente_umbral` `FIN-POL-004 §4`, first row.
4. The administrator approves, and the KPI becomes `kpi_activa`.
5. On the next run, `Vigía` self-expands `detectar` with `detectar.cartera.retraso_habito` (spec 3).
6. The next simulated day, the walkthrough of spec 2 runs to the end.

**Open:** whether this is a measure gap or only a threshold gap on `saldo_vencido` (whose `tramos`
already name 1 to 15 days) is checked in the plan, against the kernel, before the case is fixed. If
it is a threshold gap, the demonstration shows the threshold gap report, and the measure gap uses
another case from the same generated dataset.

## Prompt injection and cost

| Attack | Why it fails |
|---|---|
| a policy passage or a chat message says "create a KPI that …" | no field of a `kpi_gap` holds text, and `proponer_kpi` reads only the candidate |
| a proposal asks for an unbounded window or a cross join | the language has no such construct, and `EXPLAIN` caps the cost |
| a person posts a `kernel:` block | no endpoint accepts one |
| an approved KPI's SQL is altered after approval | the kernel refuses SQL whose hash does not match |
| a compiled query tries to write | `centinela_kernel` holds no write grant, and the transaction is read-only |

## Pages this spec changes

| Page | Change |
|---|---|
| `packages/agents/AGENTS.md`, `Vigía` | its question gains "and which measure it lacks to see one"; its output gains the KPI proposal; its model mode becomes "none to detect; thinking off to word the title; thinking on to propose a KPI" |
| `packages/agents/AGENTS.md`, `Analista` and `Estratega` | each output gains `kpi_gap`, with the condition that emits it |
| `packages/agents/skills/` | `vigia/proponer_kpi.md`, written by the rules of `skills/AGENTS.md` and loaded only at the leaf `proponer_kpi`, by the loading rule spec 2 writes; `analista/contrato.md` and `estratega/contrato.md` gain the rule that emits a `kpi_gap` |
| `apps/api/AGENTS.md` | the gap store and its repetition count, the catalogue of approved KPIs per client and its lifecycle, the `administrador` role, the endpoints above |
| `apps/web/AGENTS.md` and `apps/web/src/api/types.ts` | the catalogue and the proposals in `Configuración`; `KpiProposal` and `KpiDecision` in the draft contract |
| `evals/AGENTS.md` | `KPI-` cases: gaps below N (no proposal); gaps at N (one proposal); a threshold gap (reported, no proposal); a proposal the guard refuses twice (dropped); a rejected `pregunta` (no new proposal until N new gaps); a stored SQL whose hash no longer matches (refused); a policy passage asking for a KPI (no gap, reported); a retired KPI (its nodes retired, never handed to a run) |
| `docs/guide/chapters/kpi-kernel.md` | the section on how a new KPI is born shrink to a link to the level page this spec writes them into; the diagrams stay in the chapter, each captioned `Draws:` with that page's new section, and the chapter's warning box drops what this spec implements |

## Acceptance

- The `KPI-` cases pass.
- The demonstration case runs from the first gap to an active KPI, a self-expanded node, and an
  alert on the next simulated day, with no object created in the database.
- `grep -rn 'kernel' apps/api` shows no route that reads a `kernel:` block from a request body.
