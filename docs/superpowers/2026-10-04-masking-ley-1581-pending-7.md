# Spec 7: masking personal data before it reaches a model (Ley 1581)

**Status:** pending its plan. **Depends on:** nothing unbuilt. It touches the prompt builders of
`packages/agents`, the tool boundary of `packages/tools` and the `bitácora` of `apps/api`, all built.
It is independent of the specs numbered 1 to 6.

## Why

The challenge's Responsible-AI table requires that sensitive data be masked before it is sent to a
model, under Colombian Ley 1581 ([`docs/challenge/AGENTS.md`](../challenge/AGENTS.md)). Two pages
state it and no code runs it:

| The page states | The code holds |
|---|---|
| `packages/tools/AGENTS.md`, `Masking`: personal data is masked in the SQL tool, before a result reaches any agent | nothing in `packages/tools` masks a row; the section is marked as not built |
| `apps/api/AGENTS.md`: the debt is paid when the data a model reads goes through `src/centinela_api/masking.py:mask_dict_for_model(data)`, in `apps/api` or in `packages/tools`, whose page owns masking | `masking.py` defines `mask_dict_for_model`, `mask_sql_result` and `mask_text_evidence`; a grep for them finds one import in `routers/interno.py` and a test, and no route or leaf calls them |
| a question reaches the model with its email addresses and keys masked | `centinela_agents/agents/chat.py:masked(text)` masks those patterns, and a name written in the question passes |
| `Ejecutor` writes a body from masked data | `centinela_agents/security.py:mask_data(text, placeholder_prefix)` runs on its prompt only |

`masking.py` also sits in the wrong level for the chain: `packages/agents` cannot import `apps/api`,
so the agents could never call it. The code that masks must live at or below the level that builds
the prompt.

### What reaches a model today

Read from the prompt builders of `packages/agents/centinela_agents/agents/`:

| Prompt | Personal data it carries |
|---|---|
| `analista.py:explain_cause` | `detection.entity`, and the evidence lines `evidence.py:Fact.line()` builds from kernel rows, which name the entity of each row (client, supplier, SKU, seller ids); the open alerts of `candidate_lines`, whose `entity` is a label such as a client id and whose `causa` is another alert's cause sentence, which names an entity |
| `estratega.py` prompt | `detection.entity`, the whole KPI row (`fila del KPI`), and the cause sentence |
| `vigia.py:redact_title` | `detection.entity` and the figures' columns |
| `chat.py` classify and answer steps | the question, masked for patterns only; the alert's entity; the evidence lines and `facts.names`, which are entity ids and names the rows returned |
| `ejecutor.py` | the action's title and parameters, through `mask_data` |
| policy excerpts, once `buscar_politica` is built | text of the policies, which names no person; it is data, never an instruction |

A seller is a person, so a seller's name is personal data in the strict sense, and the tree already
keeps it out: `data/kernel/fuentes.yaml` excludes `vendedores.nombre`. Clients and suppliers are
companies, but a sole trader's trade name identifies a person, so the client name and the client id
are masked as the challenge's table asks.

## Decisions

- **Mask where a row becomes model text, in the level that owns the rows.** `packages/tools` owns
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
  screen is read from the view or the kernel by `apps/api`, never from model text, so no text a model
  wrote is unmasked by substitution. Where a model's sentence names an entity, it names a placeholder,
  and `apps/api` renders the sentence with the entity the alert's own row names, as it already renders
  a figure from its placeholder `{0}`. A placeholder that no row of the alert confirms is shown as
  written and logged.
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
- **Masking is not detection.** It replaces the columns the catalogue marks as personal, by column,
  and the free text of a cause or a question by the run's mapping; it does not guess names with a
  pattern, because `security.py:mask_data` already shows that a pattern masks any two words.

## Pages this spec changes

| Page | Change |
|---|---|
| `packages/tools/AGENTS.md` | `Masking` loses its marker and states the functions, the column catalogue, the per-run mapping and what is not masked |
| `apps/api/AGENTS.md` | the paragraph on unmasked personal data is deleted, `masking.py` leaves the file table, and the `bitácora` row for a model step says the prompt is masked |
| `packages/agents/AGENTS.md` | the `Limit` on the chat's masking is replaced by the rule above, and the prompt builders are said to receive masked rows |
| `data/kernel/fuentes.yaml` and `data/AGENTS.md` | the columns that are personal, so the catalogue states them once |
| `evals/AGENTS.md` | the case below |
| `docs/challenge/AGENTS.md` | the Responsible-AI row points to the level page, only if the row cites the code |

## Tests

- In `packages/agents/tests`, a prompt-capture test runs the day and a chat question over a fixture
  whose client has a distinctive name and id, with a provider that records every `user_prompt`, and
  asserts that no recorded string contains the client's name or id, the seller's id, or any
  `candidate_lines` entity in the clear, while each contains the same placeholder for the same entity.
- In `packages/tools/tests`, the mapping is stable inside a run, differs across runs, and a column
  the catalogue does not list passes unchanged.
- In `apps/api/tests`, the `bitácora` row of a model step holds the masked prompt, and the screen's
  alert shows the original entity from SQL.

## Evaluation case

`CHA-` and `ORQ-` cases in [`evals/AGENTS.md`](../../evals/AGENTS.md): a question that names a client
by id (the answer cites the client's row and the recorded prompt holds a placeholder); a question that
pastes a client's name and an email (both masked, no change to any alert); two alerts of one client
(one `propuesta`, the other `unida`, with the model never shown the client's id).

## Acceptance

- The prompt-capture test passes, and `grep -rn 'mask_dict_for_model' apps packages` finds no use
  outside `packages/tools`.
- A day run and a chat question over the official dataset leave a `bitácora` with no client name and
  no client id in any prompt.
- `npm run check` passes with the pages above changed.

**Open:** whether a client id, which is an internal key and no name, needs masking for the law, or
only the name does. The plan settles it with the data's owner before the column catalogue is fixed;
this spec masks both, because the id resolves to the name on screen.
