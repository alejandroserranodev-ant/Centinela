# DOUBTS

**A debt is paid, or made loud, before it is written down.**

This file is not a ledger. It defines what a debt is in Centinela and where the record of one
lives.

## What counts as a debt

Something **wrong, incomplete or unverified** that a reader would otherwise have to rediscover.
Three tests separate one from an ordinary imperfection:

1. **It is a claim about the tree**, not a preference.
2. **It survives the person who found it.** If reading the code answers it, the code is the record.
3. **It costs something specific**, and the cost is stated.

A **decision** is the other admissible shape: an option weighed and refused, with its reason, so
the next reader does not propose it again.

## Where a debt goes, in order of preference

Paying a debt leaves nothing to record. Each of the next four places fails when its record stops
being true; a paragraph does not.

1. **Pay it.** A defect that can be fixed is work, not debt.
2. **A gate with a reason-carrying map**: each entry names a case and says why, as a string value,
   and a stale entry fails the gate. The gates and their maps are in
   [`scripts/check/AGENTS.md`](./scripts/check/AGENTS.md).
3. **A test assertion.**
4. **The level's own `AGENTS.md`**, where the rule the limit qualifies is stated. The clock section
   of [`data/AGENTS.md`](./data/AGENTS.md#the-simulated-clock) is one: views that ignore the simulated day.
5. **The one header** a script or a test is allowed.
6. **A paragraph here**, written as what is wrong, what it costs, and the command that re-derives it.

**Agent memory is not a record.** It fails nothing and lives on one machine. A memory that
describes the tree is a debt nobody filed: move it to one of the places above.

## Filed debts

**The brief in the tree is incomplete, and the challenge page states more than it.**
[`docs/challenge/hackathon-brief.pdf`](./docs/challenge/hackathon-brief.pdf) is the source, and
three things in it do not hold up:

- Its menu (page 2) lists sections 05 *Metodología y agenda*, 06 *Evaluación* ("Entregables ·
  Criterios · Pruebas del jurado") and 07 *Comercialización*, and no page carries them. The
  scoring criteria, the jury's tests and the demo script have no source in the tree, so every
  priority set against them is a guess. The only scoring signal in the PDF is that a Streamlit
  prototype "baja la nota de UX" (page 14).
- [`docs/challenge/AGENTS.md`](./docs/challenge/AGENTS.md) names the five announced scenarios
  (margin, `mora`, stock-out, discounts, a customer who leaves) and says the hidden one is revealed
  at the close. The PDF says only "6 escenarios por descubrir: 5 anunciados y 1 oculto" (page 4),
  and its section *Escenarios sembrados* is missing, so the list and the reveal rest on no page.
- The challenge page calls the event "the Business AI School hackathon by On Business". The cover
  reads "onbusiness AI School · Hackatón by Paseo · Octubre de 2026" (page 1).

It costs a requirement that nobody can check against its source, and a missing section that may
hold the criteria the jury scores. It is paid when the complete deck replaces the PDF and the
challenge page is re-read against it. Re-derive it with
`pdftotext -layout docs/challenge/hackathon-brief.pdf - | grep -n "Evaluación\|Criterios\|oculto\|Escenarios"`.

**Some pages sit outside the level that owns what they describe, by decision.** The root
holds [`CONEXION_WEB_API.md`](./CONEXION_WEB_API.md), [`FLUJO_DATOS.md`](./FLUJO_DATOS.md),
[`REPORTE_JSON_SCHEMA_STANDARDIZATION.md`](./REPORTE_JSON_SCHEMA_STANDARDIZATION.md),
[`SETUP_OPENAI.md`](./SETUP_OPENAI.md) and [`TAREAS_PENDIENTES.md`](./TAREAS_PENDIENTES.md), and
`packages/agents` holds its `PHASE_*_SETUP.md` pages beside its `AGENTS.md`. The team keeps the
file structure they arrived with, so each was rewritten to own one topic and link the level page
for every fact it does not own, rather than moved into that page. It costs a reader names that do
not say what a page holds, and a route the router does not budget for the `PHASE_*` pages. It is
paid when the team agrees to fold each page into its level or rename it. Re-derive it with
`ls *.md packages/agents/PHASE_*.md | grep -v 'AGENTS\|README\|CLAUDE\|DOUBTS\|GENERATED\|docs_guide'`.

**`Vigía`'s contract states an input its leaf does not send.**
[`packages/agents/skills/vigia/contrato.md`](./packages/agents/skills/vigia/contrato.md) lists
`regla` as the metric's `umbral_alerta` text, `fuente_umbral` and `tramo` as input, while
`packages/agents/centinela_agents/agents/vigia.py:redact_title(provider, state, sources)` sends the
metric's `descripcion` as `regla` and neither `fuente_umbral` nor `tramo` to the model. It costs a
contract a reader trusts for what the model sees, and a title that cannot name the rule's source.
It is paid when the leaf sends what the contract lists, or the contract lists what the leaf sends.
Re-derive it with `grep -n "regla\|fuente_umbral\|tramo" packages/agents/centinela_agents/agents/vigia.py packages/agents/skills/vigia/contrato.md`.

**`api.alertas.costos` defaults to a shape nothing writes.** `apps/api/sql/01_esquema.sql` declares
it `DEFAULT '[]'`, while `apps/api/src/centinela_api/alertas.py:fijar_costo(conn, id, costo)`
writes an object by agent, so a row the day run never costed holds a list and a costed one an
object. Nothing reads the column yet; it costs the first reader a check of both shapes. It is paid
when the default becomes `'{}'`. Re-derive it with
`grep -n "costos" apps/api/sql/01_esquema.sql apps/api/src/centinela_api/alertas.py`.

**A model output its schema refuses is not retried.** `packages/agents/centinela_agents/metered.py:RETRIED` lists
the provider's own errors, and a leaf's `SchemaRefused`, raised after the provider returns, goes
straight to the fallback, so one malformed answer costs a step its model result where a second
call might have passed. It is paid when the meter, or the leaf, retries once on `SchemaRefused`.
Re-derive it with `grep -n "RETRIED\|SchemaRefused" packages/agents/centinela_agents/metered.py packages/agents/centinela_agents/agents/*.py`.
