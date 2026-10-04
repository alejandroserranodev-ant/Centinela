# Tree growth follow-ups

Branch `plan/tree-expansion` (PR #20). Resolves the pending items the reviews of "how the tree
grows" left, grouped by the files they touch. Each task ends with its tests green and one commit
or more; the plan is deleted once the branch carries it.

Spec: the sections "How the tree grows" of `packages/agents/arbol/AGENTS.md` and "The tree's
versions" of `apps/api/AGENTS.md`, which each task reads before it edits.

## Global Constraints

- No comments and no docstrings in hand-written source, except one header of at most ten lines on
  a test or SQL file. The docstrings of `apps/api/src/centinela_api/modelos.py` stay: they are the
  OpenAPI descriptions.
- Documentation in English, present tense; code cited as `path/to/file.py:member(parameters)`,
  never by line number; a fact lives in one page only, the level that owns it.
- Each commit message is one sentence about what the tree now does and why, sent with
  `git commit -q -F - <<'MSG'` and ending with the line
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- `git add` only the paths touched, never `git add -A`.
- A budget in `scripts/check/check-routes.ts` rises only when a page grows, to the cost rounded
  up to the next hundred.
- The OpenAPI contract is regenerated, never edited: `python -m centinela_api.contrato` in
  `apps/api` with its `.venv`, then `npm run contract` in `apps/web`.
- No SQL against the local development database, no publishing of the guide.
- An item that turns out not to be a defect on reading the code is not changed; the report says
  why.
- Test commands: `uv run pytest` in `packages/agents`; `.venv/bin/pytest -m "not integracion"` in
  `apps/api`; `npm run typecheck` and `npm test` in `apps/web`; `npm run check` at the root.
- Test names in English where they already are; no test name mixes Spanish and English words.

## Task 1: growth, expansion and validator in `packages/agents`

Files: `centinela_agents/growth.py`, `centinela_agents/validator.py`,
`centinela_agents/expansion.py` if needed, `tests/test_growth.py`, `tests/test_expansion.py`,
`tests/test_validator.py`, and `arbol/AGENTS.md` where a stated fact changes.

1. **Evidence only from rows the split newly adds.** `growth.py:grow(...)` takes its evidence from
   every reached row, including a row the target leaf already excludes, so when several rows reach
   the count at once an alert behind an already-excluded row is consumed by the new version. The
   evidence must come only from the rows the split adds to `excluye`. Add a test where one row is
   already excluded by the leaf and two rows reach the count together: the evidence holds only the
   alerts of the new row.
2. **One fingerprint of everything the validator and the replay read.** Add a function in
   `packages/agents` (in `validator.py` or `expansion.py`, beside what it hashes) that returns a
   sha256 hex digest of: the base tree, the registry, the metrics, the caps and repetitions of the
   growth settings, the text of `skills/estratega/acciones.md`, and the relative paths and texts of
   every skill file a base leaf loads plus `skills/analista/*.md` under `grounds.skills`. Changing
   any of those must change the digest; test it by editing each input in a temporary copy (or by
   building grounds with one value changed) and asserting the digest differs, and that two loads
   of the same inputs give the same digest. Task 3 uses it in `apps/api`.
3. **Unify how the validator reads the skills.** `validator.py:exclusion_problems(tree, grounds)`
   reads the action rows through the global skills path of `centinela_agents/skills.py`, while
   `coverage_problems` reads `grounds.skills`; make both read `grounds.skills` (give
   `skills.action_rows` a path parameter with the current default if that is the cheapest way).
   `validator.py:load_base(...)` becomes `load_grounds(...).base`.
4. **`tests/test_expansion.py`.** A negative assertion there passes trivially; make it fail when L0
   or L1 change (e.g. assert the layer hash or the L0/L1 nodes of the yielded tree equal the
   parent's). `expansion.py:move_problems(parent, move, grounds)` returns early in a way that hides
   the real problem when `nueva` is not well formed; make it report that problem with its message
   and test the message.
5. **`tests/test_growth.py`.** The nesting test checks the restoration only through `metric_leaf`;
   also assert the `excluye` of the `.1` leaf after the retirement, or walk the compiled graph.
   The test that no module opens a database connection checks only `psycopg`; extend it to
   `sqlite3`, `asyncpg` and `sqlalchemy`.
6. **`tests/test_validator.py`.** The two PLANTED retirement rows assert the same message; make the
   family case prove it fires through liveness (its message or setup must differ from the other
   row's so that a validator without the liveness check fails it).

## Task 2: orchestrator and graph in `packages/agents`

Files: `centinela_agents/orchestrator.py`, `centinela_agents/graph.py`,
`centinela_agents/evidence.py` if needed, `tests/test_orchestrator.py`, `tests/test_orq.py`,
`packages/agents/AGENTS.md` where a stated fact changes, and `DOUBTS.md`'s rules for whatever is
left (read it: a debt goes to the level's page, not to a ledger).

1. **`orchestrator.py:CentinelaOrchestrator.use_tree(tree)`** leaves the `Sources` built in the
   constructor indexing the first tree's nodes, so the KPI columns of a node a later version adds
   (`agregar_rama`) never reach the evidence. Make the sources read the nodes of the tree in use.
   Test it: a second tree with a node the first lacks reaches the sources after `use_tree`.
2. **`_graphs`** is keyed by version alone, falls back to `self.graph` for an unknown version,
   is assigned in two non-atomic steps and grows without bound. Fix what is cheap: an unknown
   version must not resolve to another version's graph (the caller then sees no paused graph),
   the graph and its registration are set so a reader never sees one without the other, and check
   whether the base tree's own version can collide with a stored version id. Whatever is not cheap
   (the bound) is written as a debt where `DOUBTS.md` says, with its cost.
3. **`graph.py:leaf_node(...)`**: the nested conditional that builds `given` for a leaf, passing
   `excluye`, becomes a named helper.
4. **`tests/test_orchestrator.py`**: a fixed slice over a list is fragile; select by content.
5. **`tests/test_orq.py`**: the `MagicMock` import is unused or misplaced, and a lambda is bound to
   a name; make both idiomatic.

## Task 3: tree versions in `apps/api`

Files: `src/centinela_api/arboles.py`, `src/centinela_api/routers/simulacion.py`,
`src/centinela_api/modelos.py`, `src/centinela_api/routers/arbol.py` if needed,
`tests/test_arboles.py`, `tests/test_arbol.py`, `tests/test_avanzar.py` or the test the day run
lives in, the contract (`src/api/openapi.json` and `apps/web/src/api/schema.generated.ts` via the
regeneration commands), and `apps/api/AGENTS.md`.

1. **A failure to load the stored version is visible at the end of the day.** Today a failure in
   `arboles.py:vigente` or the replay inside `arboles.py:del_dia(conn, dia)` is caught only by the
   `Detection phase failed` handler of `routers/simulacion.py`: an ERROR in the log, a day with no
   alerts and a clock already advanced. Add a field to `modelos.py:AdvanceEnd` that says the day's
   analysis failed (with a Spanish message fit for a manager), set it from that handler, and test
   it in the day run's test. Add a test that a failure of the stored version propagates out of
   `del_dia` (it is not swallowed like the drafter's failure). Update the paragraph of
   `apps/api/AGENTS.md` that describes this, and the `end` row of the endpoints table. Task 4
   shows it on screen.
2. **`huella` covers what the validator and the replay read.** `arboles.py:huella(base)` hashes
   only `base.yaml`; use Task 1's fingerprint so a change to `acciones.md`, `fundamentos.yaml`,
   `metricas.yaml` or `crecimiento.yaml` replays the stored moves on the next day. Say on the
   API's page that the base's hash covers those inputs.
3. **A rebase that drops an expansion a person already retired keeps the retirement.** Today
   `vigente` writes a `descartada` row for the expansion and another for its `retiro`, the list
   shows `inactive` instead of "retired by", and the `bitácora` gets two rows for one change.
   Write one `descartada` row, for the expansion only, one `bitácora` row, and keep the status
   `retired` with who and why. Test it.
4. **The list between a merged base and the next day.** `arboles.py:estados(filas)` derives the
   status from the newest stored version, built on the old base until the next day run replays.
   Do not write on a GET. State it in one sentence on the API's page, beside the statuses.
5. **`arboles.py:insertar(...)`**: its keyword parameters get type annotations.
6. **Tests.** `tests/test_arboles.py`: a rebase that, in the same pass, drops one expansion and
   keeps or drops another that depends on it. `tests/test_arbol.py`: a 401 without a token; rename
   the tests whose names mix Spanish with `inactive` so each name reads in one language.
7. **An `inactive` expansion says why.** `modelos.py:TreeExpansion` gains a field that tells a move
   a merged base dropped from one no longer live because an expansion it nests under was retired,
   set by `arboles.py:expansiones(...)`; test both in `tests/test_arboles.py`. Task 4 shows it.

## Task 4: the `Configuración` tab "Árbol de decisión" and the day's end in `apps/web`

Files: `src/screens/Expansions.tsx`, `src/state/Simulation.tsx`, `src/api/http-client.ts`,
`src/api/types.ts` if needed, a pure `.ts` helper and its `.test.ts` if logic moves out of a
component, and `apps/web/AGENTS.md`.

1. **The day's end** (from Task 3): when the `end` event says the analysis failed, the shell shows
   a danger notice with the server's message instead of "no new decisions".
2. **A failed retirement.** The dialog shows the server's reason (`ApiError.message`) when the
   retirement fails; on a 409 (already retired by someone else) the list reloads so the row shows
   its real status.
3. **Evidence links** are `ArenaTextLink`s, as in `src/screens/Bitacora.tsx`, not `ghost` buttons.
4. **The "Quién" column** names the agent as `Bitácora` does (`Centinela · <stage>`), because
   `apps/web/AGENTS.md` keeps agent vocabulary off a manager's screen; reuse the same mapping, do
   not copy it.
5. **An `inactive` row says why**: a muted text line under the tag, from the field Task 3 adds,
   distinguishing a move a new base dropped from one whose parent expansion was retired.
6. The web suite (`node --test "src/**/*.test.ts"`) renders no screen, so no render test is added;
   any logic moved into a pure helper gets a `.test.ts`.

## Task 5: the flaky `apps/api/tests/test_resumen.py`

`tests/test_resumen.py` sometimes fails with `ModuleNotFoundError` naming `integracion`, depending
on the collection order, since before this branch. Diagnose the cause with
superpowers:systematic-debugging (reproduce with a fixed order, find what imports what), fix the
cause, not the symptom, and prove it by running the suite in the orders that failed.
