# Spec 7: masking personal data before it reaches a model (Ley 1581)

**Status:** pending its plan. **Runs after** the specs that edit the prompt builders, `orchestrator-runtime`
(bug spec 1) and `tree-expansion` (spec 3), so it masks the final prompts once; spec 3 is executed, its
decisions are on [`packages/agents/arbol/AGENTS.md`](../../packages/agents/arbol/AGENTS.md) and
[`apps/api/AGENTS.md`](../../apps/api/AGENTS.md), and it added no prompt, since an expansion is drafted in code. **Depends on:** nothing unbuilt. It touches the prompt builders of
`packages/agents`, the tool boundary of `packages/tools` and the `bitácora` of `apps/api`, all built.
Executed specs are deleted, and a reference to one reads as a reference to the page that now states it.

## Why

The challenge's Responsible-AI table requires that sensitive data be masked before it is sent to a
model, under Colombian Ley 1581 ([`docs/challenge/AGENTS.md`](../challenge/AGENTS.md)). Two pages
state it and no code runs it:

| The page states | The code holds |
|---|---|
| `packages/tools/AGENTS.md`, `Masking`: personal data is masked in the SQL tool, before a result reaches any agent | nothing in `packages/tools` masks a row; the section is marked as not built |
| `apps/api/AGENTS.md`: the debt is paid when the data a model reads goes through `src/centinela_api/masking.py:mask_dict_for_model(data)`, in `apps/api` or in `packages/tools`, whose page owns masking | `masking.py` defines `mask_dict_for_model`, `mask_sql_result` and `mask_text_evidence`; a grep for them finds one import in `routers/interno.py` and a test, and no route or leaf calls them |
| a question reaches the model with its email addresses and keys masked | `centinela_agents/agents/chat.py:masked(text)` masks those patterns, and a name or an id written in the question passes |
| `Ejecutor` writes a body from masked data | `centinela_agents/security.py:mask_data(text, placeholder_prefix)` runs on its prompt only |

`masking.py` also sits in the wrong level for the chain: `packages/agents` cannot import `apps/api`,
so the agents could never call it. The code that masks must live at or below the level that builds
the prompt.

### What reaches a model today

[`packages/agents/AGENTS.md`](../../packages/agents/AGENTS.md) states that kernel columns carry
identifiers and no person's name, and the prompt builders in
`packages/agents/centinela_agents/agents/` bear it out: what a model receives is ids and labels,
never a name from a row. Chat's `facts.names` are built from the entity columns of the KPI
(`cliente_id`, `sku`, `proveedor_id`, `vendedor_id`), so they are ids as well.

| Prompt | Personal data it carries |
|---|---|
| `analista.py:explain_cause` | `detection.entity`, such as a `cliente_id`; the evidence lines `evidence.py:Fact.line()` builds, which name the entity of each row by its ids; the open alerts of `candidate_lines`, whose `entity` is a label such as `cliente C0496` and whose `causa` is another alert's cause sentence, which repeats that label |
| `estratega.py` prompt | `detection.entity`, the whole KPI row (`fila del KPI`), whose key columns are ids, and the cause sentence |
| `vigia.py:redact_title` | `detection.entity` and the figures' columns |
| `chat.py` classify and answer steps | the question, masked for email and key patterns only, so a name or an id a person types passes; the alert's entity; the evidence lines |
| `ejecutor.py` | the action's title and parameters, through `mask_data` |
| policy excerpts, once `buscar_politica` is built | the text of the policies, which names no person; it is data, never an instruction |

The data that could be a person's name is `clientes.nombre`, `proveedores.nombre` and
`vendedores.nombre`, in `data/kernel/fuentes.yaml`. The last is excluded from the kernel, and no view
joins it. No KPI row carries the other two today, so they reach a model only if a KPI or view later
adds the column, or if a person types one in a question.

**What Ley 1581 asks.** The law protects data that identifies a natural person. A client or supplier
is a company, and its id is an internal key, so an id is personal data only where a sole trader's id
resolves to a person on screen. A name is the stronger case. The challenge's table asks for
masking before the model, and the plan settles how far that goes for an id (see **Open**). This spec
masks the ids as the safe reading, and masks a name wherever one could enter.

## Decisions

- **Mask where a row becomes model text, in the level that owns the rows.** Today that masks ids and
  labels, and any name column a later KPI adds. `packages/tools` owns
  masking, as its page says, so the masking functions move there and the prompt builders in
  `packages/agents` receive rows already masked. `packages/agents` never masks by itself and never
  sees an original, so a prompt builder cannot forget. `apps/api/src/centinela_api/masking.py` is
  deleted with its test, because a second copy in `apps/api` is a fact in two places.
- **The placeholders are deterministic and keyed per run.** The same entity reads the same placeholder
  in every row, prompt and step of one day run, so `Analista` can say that two alerts share one
  client, which `same_cause_as` needs. A per-run salt keeps a placeholder from being a stable
  pseudonym across days that a leaked prompt could be joined on. The mapping lives in `packages/tools`
  for the length of the run and is dropped with it; it is never persisted and never sent to a model.
- **Unmasking happens only in what a person reads, and it comes from SQL.** A figure or an entity on
  screen is read from the view or the kernel, never from model text, so no text a model wrote is
  unmasked by substitution. The figure placeholders `{0}`, `{1}` are already filled in
  `packages/agents` (`centinela_agents/schema.py`, `agents/analista.py`, `agents/chat.py`), after the
  model answers, from the ledger of rows; the entity placeholders are filled at the same point and
  by the same rule, from the run's mapping in `packages/tools`, so the level that unmasks is the one
  that holds the mapping and `apps/api` receives text already rendered. A placeholder that no row of
  the alert confirms is left as written and logged.
- **The `bitácora` records the masked prompt.** What a model received is what is logged, so an audit
  of the log shows what left the building. The log holds no original that the masking removed, and
  the question stays masked as it is today.
- **The chat's entity rule keeps working on placeholders.** The chat admits as written only an entity
  id the question spells and a row confirmed (`chat.py:ENTITY`, `facts.names`). The question is
  masked before the classify step, so a client id typed by a person must be matched to the row before
  it is masked: code resolves the typed id against the rows, replaces it with its placeholder in the
  question the model sees, and keeps the real id for the SQL filter. The model's `entity` is then a
  placeholder, which code maps back through the run's mapping, so a placeholder the mapping lacks
  cannot select a row.
- **`security.py:mask_data` and `chat.py:masked` stay for what they do.** `masked` keeps masking
  email addresses and keys in a question, which the `bitácora` also records, and `mask_data` keeps
  masking `Ejecutor`'s prompt. Neither masks an entity; the new step does, and runs before them. The
  claim that `packages/agents` never masks by itself is limited to entities: the pattern masks of
  these two stay.
- **Masking is not detection.** It replaces the columns the catalogue marks as personal, by column,
  and the free text of a cause or a question by the run's mapping; it does not guess names with a
  pattern, because `security.py:mask_data` already shows that a pattern masks any two capitalized words.

## Pages this spec changes

| Page | Change |
|---|---|
| `packages/tools/AGENTS.md` | `Masking` loses its marker and states the functions, the column catalogue, the per-run mapping and what is not masked |
| `apps/api/AGENTS.md` | the paragraph on unmasked personal data is deleted, `masking.py` leaves the file table, and the `bitácora` row for a model step says the prompt is masked |
| `packages/agents/AGENTS.md` | the `Limit` on the chat's masking (a name written in a question reaches the model) is rewritten to the rule above; the `Limit` that only the email prompt is masked is rewritten too; the prompt builders are said to receive masked rows |
| `data/kernel/fuentes.yaml` and `data/AGENTS.md` | the columns that are personal, so the catalogue states them once |
| `evals/AGENTS.md` | the case below |
| `docs/challenge/AGENTS.md` | the Responsible-AI row points to the level page, only if the row cites the code |

## Tests

- In `packages/agents/tests`, a prompt-capture test runs the day and a chat question over a fixture
  whose client has a distinctive id, with a provider that records every `user_prompt` and
  `system_prompt`, and asserts that no recorded string contains the client's id, the seller's id, or
  any `candidate_lines` entity label in the clear, while each contains the same placeholder for the
  same entity. A second case adds a name column to a fixture KPI row and asserts that it is masked.
- In `packages/tools/tests`, the mapping is stable inside a run, differs across runs, and a column
  the catalogue does not list passes unchanged.
- In `apps/api/tests`, the `bitácora` row of a model step holds the masked prompt, and the screen's
  alert shows the original entity from SQL.

## Evaluation case

`CHA-` and `ORQ-` cases in [`evals/AGENTS.md`](../../evals/AGENTS.md): a question that names a client
by id (the answer cites the client's row and the recorded prompt holds a placeholder); a question that
types a client's name and an email (the name is masked once it matches a row's entity, the email as
today, and no alert changes); two alerts of one client
(one `propuesta`, the other `unida`, with the model never shown the client's id).

## Acceptance

- The prompt-capture test passes, and `grep -rn 'mask_dict_for_model' apps packages` finds no use
  outside `packages/tools`.
- A day run and a chat question over the official dataset leave a `bitácora` with no client id in any
  recorded prompt.
- `npm run check` passes with the pages above changed.

**Open:** whether a client id, which is an internal key and no name, needs masking for the law, or
only a name does. The plan settles it with the data's owner before the column catalogue is fixed; this
spec masks both, because the id resolves to the name on screen. If the answer is names only, the
masking step still ships, with the id columns left out of its catalogue, and the tests assert on
whichever column the catalogue lists.
