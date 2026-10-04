# Masking personal data before a model (Ley 1581) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** every prompt that leaves for a model carries placeholders in place of the personal values the catalogue lists, every model answer comes back with them filled from the run's mapping, and the `bitácora` keeps the masked prompt.

**Architecture:** `packages/tools` owns the catalogue (`personales` in `data/kernel/fuentes.yaml`) and a per-run `Masking` that registers personal values from rows, masks text by its mapping and fills placeholders back. `packages/agents` opens one `Masking` per day run, per resume and per chat question, hands it to the graph through the run's config (which LangGraph never checkpoints for an object), registers what each leaf can put in a prompt, and masks at the one place every model call passes, `MeteredProvider`, which refuses a call made outside a masking scope. `apps/api` stores each masked prompt as a `bitácora` row of type `prompt`, kept out of the screen's log like `costo`.

**Tech Stack:** Python 3.13, LangGraph 1.2, pytest, FastAPI, psycopg.

**Spec:** `docs/superpowers/2026-10-04-masking-ley-1581-pending-7.md`

## Why the mask sits at the provider, not in each prompt builder

The spec places masking "where a row becomes model text" and wants the prompt builders unable to
forget. A builder writes rows, entity tuples, alert briefs, cause sentences, action parameters and a
person's question into a prompt; masking each of those in each builder is the omission the branch
shipped with (only `detection.entity` of two builders). `MeteredProvider` already wraps every model
call of every leaf, so masking the finished prompt there by the run's mapping covers every builder,
present and future, and fails closed when no scope is open. The mapping is filled from rows, which
is the spec's "by column" rule; the text is masked "by the run's mapping", which is the spec's rule
for free text. The builders stay as they are, which also keeps this branch from conflicting with
`tree-expansion`, whose drafter edits the same builders.

The model's answer is unmasked in the same place, before any leaf validates it, so every check that
runs today (`stray_digits`, `ENTITY`, `same_cause_as`) sees the same text it sees today.

## Global Constraints

- Hand-written source carries no comments, except one header of at most ten lines on a script, a test or a SQL file (`check:docs`).
- Documentation in English, present tense; domain words in Spanish in backticks.
- Prose cites code as `path/to/file.py:member(parameters)`, never by line number (`check:citations`).
- `packages/agents` never imports `apps/api`; only `packages/tools` reads the database.
- The mapping is never persisted, never logged and never sent to a model.
- A placeholder holds no digit, so `evidence.py:stray_digits(text, allowed)` never reads one as a figure.
- The open question of the spec is settled by its default: ids and names are both masked.

## Review Focus

- A model call made outside any scope (a new caller of the provider): it must raise, not send the prompt in the clear. Task 2 tests it.
- A person types a client id in lower case (`cli-001`): the prompt holds the placeholder. Task 2 tests it.
- The model writes a placeholder the mapping does not hold: it stays as written and is logged, and the chat's entity is not chosen from it. Task 1 and Task 2 test it.
- An entity value that is a prefix of another (`VEN-01`, `VEN-010`): each masks to its own placeholder, never a half. Task 1 tests it.
- An alert resumed after an API restart (no day-run mapping in memory): Ejecutor's prompt is still masked, from a fresh mapping the leaf fills from the state. Task 2 tests it.

---

### Task 1: The catalogue and the run's mapping in `packages/tools`

**Files:**
- Modify: `data/kernel/fuentes.yaml` (a `personales` list on `clientes`, `proveedores`, `vendedores`)
- Modify: `packages/tools/centinela_tools/sources.py` (`Table.personal`, validated)
- Rewrite: `packages/tools/centinela_tools/masking.py`
- Rewrite: `packages/tools/tests/test_masking.py`
- Modify: `packages/tools/tests/test_sources.py` (a `personales` column that is not readable is refused)

**Interfaces:**
- Produces: `masking.py:personal_columns(sources=None) -> frozenset[str]`; `masking.py:Masking(columns=None, salt=None)` with `register(column, value) -> str | None`, `register_row(row) -> None`, `register_tree(value) -> None`, `text(text) -> str`, `unmask(text) -> str`, `unmask_tree(value) -> Any`, `placeholder(original) -> str | None`.

- [ ] **Step 1:** `fuentes.yaml` gains `personales: [cliente_id, nombre]` on `clientes`, `[proveedor_id, nombre]` on `proveedores`, `[vendedor_id]` on `vendedores`. `sources.py:table_of(name, spec)` reads it into `Table.personal: frozenset[str]` and refuses a personal column that is not readable.
- [ ] **Step 2: failing tests** in `test_masking.py`: the same value reads the same placeholder inside a `Masking`; two `Masking` read different placeholders; a column outside the catalogue passes unchanged; a placeholder holds no digit; `text` masks case-insensitively and whole tokens only (`VEN-01` inside `VEN-010` is not touched); `unmask` restores a known placeholder and leaves an unknown one as written; `register_tree` finds personal keys at any depth; `personal_columns()` reads `fuentes.yaml`.
- [ ] **Step 3: implement.** Placeholder: `KIND_LETTERS`, `KIND` the column without `_id` in upper case (`CLIENTE`, `PROVEEDOR`, `VENDEDOR`, `NOMBRE`), six letters drawn from an HMAC-SHA256 of the column and value under a random per-instance salt, widened by one letter on a collision. `text` substitutes every registered original, longest first, between non-word boundaries, ignoring case. `unmask` replaces `(?:KINDS)_[A-Z]{6,}` tokens found in the mapping and logs the rest at warning.
- [ ] **Step 4:** `uv run pytest` in `packages/tools` passes.
- [ ] **Step 5: commit.**

### Task 2: Every model call of `packages/agents` goes through the mapping

**Files:**
- Create: `packages/agents/centinela_agents/privacy.py`
- Modify: `metered.py` (`MeteredProvider` masks, records, unmasks; `Meter.prompts`)
- Modify: `graph.py` (`leaf_node` opens the scope and returns `prompts`; `run_config`, `stream_alert`, `start_alert`, `resume` take `masking`)
- Modify: `state.py` (`prompts: Annotated[list, operator.add]` in `AlertState` and `ChatState`)
- Modify: `day.py:run_day(...)` (one `Masking` per day, holding the earlier alerts and the day's detections)
- Modify: `orchestrator.py` (`ask` and `resume` open one; `rejection_target` runs in a scope; `ask` returns `prompts`)
- Modify: `evidence.py` (`Ledger.consult` registers its rows in the open scope; the branch's `mask_entity` and masked rows go)
- Modify: `agents/analista.py`, `agents/estratega.py` (back to `main`: the prompt is masked at the provider)
- Modify: `agents/chat.py:classify(...)` (a question with a token holding a digit reads the KPIs keyed by a personal column first, so a typed id is in the mapping)
- Rewrite: `tests/test_masking_e2e.py`; modify `tests/test_leaves_in_the_graph.py`, `tests/test_metered.py`

**Interfaces:**
- Consumes: Task 1's `Masking`.
- Produces: `privacy.py:current` (a `ContextVar`), `privacy.py:scope(masking)`, `privacy.py:register_state(masking, catalog, state)`, `privacy.py:register_entity(masking, catalog, metric, entity)`, `privacy.py:MASKING` (the config key); `Meter.prompts: list[dict]` of `{"agent", "system", "user"}`; the state's `prompts`; `CentinelaOrchestrator.ask(...)["prompts"]`.

- [ ] **Step 1: failing tests** in `test_masking_e2e.py`, over `CentinelaOrchestrator` with a provider that records every request: a day run with two alerts of client `CLI-001` (seller `VEN-01`) and a chat question naming `cli-001` leave no recorded `system_prompt` or `user_prompt` holding `CLI-001`, `cli-001` or `VEN-01`, and one placeholder for `CLI-001` across the day's prompts; a fixture KPI row with a `nombre` column reaches the prompt masked; a placeholder in the model's answer comes back as `CLI-001` in the stored title; an unknown placeholder in the chat's `entity` chooses no entity; Ejecutor's prompt after a resume with no day run is masked; the state's `prompts` hold the masked text. In `test_metered.py`: a call with no scope raises.
- [ ] **Step 2: implement** `privacy.py`, the provider, the leaf scope and the run's mapping as the Architecture says; `register_state` registers the detection's entity and row, the anchored alert's entity, and every personal key in the state.
- [ ] **Step 3:** update the two tests in `test_leaves_in_the_graph.py` that read `CLI-001` in a prompt: they read its placeholder.
- [ ] **Step 4:** `uv run pytest` in `packages/agents` passes.
- [ ] **Step 5: commit.**

### Task 3: `apps/api` keeps the masked prompt and loses its own masking

**Files:**
- Modify: `apps/api/sql/01_esquema.sql` (`prompt` in `bitacora_tipo_check`)
- Modify: `apps/api/src/centinela_api/bitacora.py` (`registrar_prompt(conn, alerta_id, actor, detalle, dia_simulado)`; `listar` leaves `prompt` out, like `costo`)
- Modify: `routers/simulacion.py:_registrar(...)`, `routers/chat.py:chat(...)`, `routers/alertas.py` (resume): one `prompt` row per entry the run added
- Delete: `apps/api/src/centinela_api/masking.py`; its import in `routers/interno.py`; its tests in `tests/test_flujo_agentes.py`
- Test: the `bitácora` test file that already records a run

- [ ] **Step 1: failing test:** after a recorded run whose state carries a prompt with a placeholder, `api.bitacora` holds a `prompt` row with that text and `listar` does not return it; the alert's entity is the original from the detection.
- [ ] **Step 2: implement**, the detail being `"<agent>\n--- system\n<system>\n--- user\n<user>"`.
- [ ] **Step 3:** the API's tests pass; `grep -rn 'mask_dict_for_model' apps packages` finds nothing.
- [ ] **Step 4: commit.**

### Task 4: The pages, the evaluation cases and the branch's leftovers

**Files:**
- Modify: `packages/tools/AGENTS.md` (`Masking` loses its marker: the functions, the catalogue, the per-run mapping, what is not masked)
- Modify: `apps/api/AGENTS.md` (the unmasked-data paragraph goes, `masking.py` leaves the file table, the `bitácora` holds the masked prompt as `prompt`)
- Modify: `packages/agents/AGENTS.md` (the chat's and Ejecutor's masking limits rewritten; the provider masks every prompt; the scopes)
- Modify: `data/AGENTS.md` (the `personales` list)
- Modify: `evals/AGENTS.md`, `evals/casos_chat.csv` (the spec's `CHA-` and `ORQ-` cases)
- Modify: `docs/challenge/AGENTS.md` only if its Responsible-AI row cites code
- Delete: `docs/superpowers/2026-10-04-phase-1-ley-1581-implementation.md` (Spanish, and it calls the work complete)

- [ ] **Step 1:** edit each page; run `npm run check` until it passes.
- [ ] **Step 2: commit.**

### Task 5: Verification and closing

- [ ] `uv run pytest` in `packages/tools` and `packages/agents`, the API's tests, `npm run check`, `git status --short` against `GENERATED.md`.
- [ ] Delete the spec and this plan, since the branch executes them; commit.
