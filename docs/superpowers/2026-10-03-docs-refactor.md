# Docs refactor: documents that state the tree, gates that hold them, and where a new feature lands

## Context

Branch `docs/docs-refactor`. Four parallel audits checked every `.md` in the tree against the code,
against `docs_guide.md` §3–4 and against the root `AGENTS.md` rules. The documents have drifted from
the code, and nothing catches the drift:

- **False claims.** The root says "the other parts hold no code yet", but `data` holds SQL and the
  generator, `docs/guide` holds `publish.py`, and `apps/web` runs screens. The root says `Vigía`
  "reads the views", but it reads `kpi_consultar`. The root says MCP is "undecided". The root says
  "no gates yet", but pytest gates exist. The `detection` row in the agents state table is wrong.
  `docs/guide/AGENTS.md` tells the reader to `cp .env.example .env` over a tracked file.
- **Unbuilt design written as if it runs**, with no marker. Examples: MCP servers,
  `calcular_impacto`, retry and token cap, Langfuse, `run_day`, de-duplication and order, the eval
  runner and its cases, the approved-KPI file, self-expansion.
- **Facts stated on several pages.** The kernel definition, the read-only grants, the stack
  choices, the `request_changes` cap, base-KPI parity, masking, and the universe table.
- **No "where does a new feature go" answer.** No router row covers the kernel, a node, the
  registry or a skill. No level has a checklist per kind of feature. `packages/agents/AGENTS.md` is
  36 KB, against a route budget of 8–10 KB.
- **Every rule is held by a person.** `docs_guide.md` §6 and §9 (step two and three) name the gates
  that would hold them.

The goal is that every page states the present tree, marks what is decided but not built, owns
each fact once, and gives a checklist per kind of feature. Gates run with **npm and Node directly,
like `apps/web`, never Bun**, and hold what can be held. An agent building the remaining challenge
features then finds where its change lands from the router, and `npm run check` fails when a page
stops being true.

### Decisions taken with the user

1. **Executed specs 1, 2, 4 and 5 are deleted.** The pending specs (3, 6, bug 1) cite level pages
   instead.
2. **Unbuilt design keeps its place on its level, marked.** Each level page opens with one sentence
   on what runs. Each design section with no code opens with `> **Decided, not built.**`, the
   guide's existing convention.
3. **Scope is the docs, the gates `docs_guide.md` suggests, and trivial tree defects**:
   `identity.html`'s broken stylesheet, and skill prompts that contradict the kernel or their own
   rules. Deeper defects are recorded, not fixed. This covers: severity has no definition; an
   approved KPI's `umbral` never resolves outside tests; `publish.py:inventory` hard-codes the
   parts.
4. **Split `packages/agents/AGENTS.md`**, creating `packages/agents/arbol/AGENTS.md`.
5. **Gates on npm + Node, zero runtime.** Node 26 is installed, and `apps/web` requires
   `node >=22`. Node runs `.ts` natively by type stripping, so gates are TypeScript run with `node`
   and tested with `node --test`.

## Ground rules for execution

- Docs in English, present tense. Domain words stay in Spanish in backticks. Cite as
  `path:member(params)`, never by line number. Give no literal count of anything that grows. Read a
  file before describing it.
- **One owner per fact.** The second copy becomes a link. Owners are fixed in the table below.
- One commit per phase, or a few small ones. Messages follow `docs_guide.md` §4: a sentence about
  what the tree now does and why, written through `git commit -q -F - <<'MSG'`, and ending with the
  session's attribution lines.
- First commit: copy this plan to `docs/superpowers/2026-10-03-docs-refactor.md`, the repo
  convention. The last commit deletes it.
- Gate source follows the repo rule: no comments, one header of at most ten lines per script and
  test.

### Fact owners

| Fact | Owner | Others link to it |
|---|---|---|
| Kernel language, base KPIs, roles and grants, the clock's leaking views, `csv/` never overwritten | `data/AGENTS.md` | root, tools, `kpi-kernel.md`, `GENERATED.md` |
| Compiler, guards, kernel tools, base-KPI parity test, DSN env vars, masking, idempotency, MCP choice | `packages/tools/AGENTS.md` | data, evals, agents, challenge |
| Node schema, levels, ends, validator, registry, adding a node or metric | `packages/agents/arbol/AGENTS.md` (new) | parent, `decision-tree.md` |
| Agents, orchestrator runtime, routing, order, cost, Langfuse, models | `packages/agents/AGENTS.md` | challenge, evals |
| Skill format, including the `acciones.md` shape that code parses | `packages/agents/skills/AGENTS.md` | parent |
| Lifecycle, clock, endpoints (incl. those `apps/web` consumes), 409, 422, `request_changes` cap, `bitácora` | `apps/api/AGENTS.md` | web, agents, evals |
| Each gate, its maps, how to add one | `scripts/check/AGENTS.md` (new) | root rules name the gate holding each |
| Stack choices per part | each level | `docs/challenge` keeps only the brief's column |
| States of a claim | `docs/guide/chapters/status.md` | `start-here.md` |

## Phase 1 — `docs/superpowers/`

- Delete `2026-10-03-normative-foundations.md`, `-decision-tree.md`, `-kpi-kernel.md` and
  `-current-kpis-in-kernel.md`.
- In the three pending specs, rewrite the Status/Depends lines to cite the level pages that hold
  that content: `arbol/AGENTS.md`, `data/AGENTS.md` and `packages/tools/AGENTS.md`.
- Fix stale references, including `catalog_from_kernel(answer)`.

## Phase 2 — the gates (`docs_guide.md` §6 and §9, steps two and three)

They are built before the page rewrite, so their first red sweep is the worklist for Phases 3–8.

**Layout.** `scripts/check/` is a new level with its own `AGENTS.md`, linked from the router. The
manifest is a **root `package.json`** (`private`, `"type": "module"`, `engines.node >=22.18`). The
gates walk the whole tree, so its commands belong at the root, beside the router that names them.
This replaces the root's "There is no root manifest". The only devDependency is `typescript`, for
two jobs:

- `npm run typecheck`, through a `scripts/check/tsconfig.json` with `noEmit`,
  `allowImportingTsExtensions` and `erasableSyntaxOnly`;
- its scanner, which finds comments in `.ts`/`.tsx` without a hand-rolled lexer.

Imports use `.ts` extensions. The code uses no enums, namespaces or parameter properties, the
Node type-stripping limits.

**Scripts:**

```
"check":            "node scripts/check/check-all.ts",
"check:agents":     "node scripts/check/check-agents.ts",
"check:citations":  "node scripts/check/check-citations.ts",
"check:vocabulary": "node scripts/check/check-vocabulary.ts",
"check:docs":       "node scripts/check/check-docs.ts",
"check:generated":  "node scripts/check/check-generated.ts",
"check:routes":     "node scripts/check/check-routes.ts",
"test":             "node --test scripts/check/",
"typecheck":        "tsc -p scripts/check"
```

**Shared pieces** (the shape in §6):

- `tree.ts`: the **one walk**. It lists files with `git ls-files -co --exclude-standard`, follows
  symlinks as links, and holds the one `FOREIGN` set (`.claude`, `.superpowers`, `node_modules`,
  `.venv`, `dist`, `.git`). It also holds helpers:
  - `markdownProse(text)`, which drops fenced blocks;
  - `nearestManifest(path)`, which finds `package.json` or `pyproject.toml` walking up;
  - `slug(heading)`, which makes GitHub anchors.
- `gate.ts`: exit codes 0 pass, 1 fail, 2 cannot run (prints SKIP). It also holds the shared
  `zeroScanProblems` and `staleProblems(map, present)`, which every gate uses.
- `check-all.ts`: the `GATES` registry. It runs each gate as a child process, never stops at the
  first failure, and prints INCOMPLETE and fails when any gate skipped, because the repo is strict.
- Each gate exports pure `problems(root)` functions returning strings. Each reason-carrying map is
  `Map<string,string>`. Work sits behind `if (import.meta.main)`.

**Gates and the rule each holds:**

| Gate | Fails when | Maps |
|---|---|---|
| `check:agents` | an `AGENTS.md` that no chain of links from the root reaches; a `README.md` outside `SURVIVORS`; `CLAUDE.md` not a symlink to `AGENTS.md`; a manifest declaring entry points with no `AGENTS.md` beside it (the monorepo rule) | `SURVIVORS` (root README) |
| `check:citations` | a relative link or `#anchor` that does not resolve; a backticked path resolving neither from the root, beside the page nor from its nearest manifest's dir; a `file.py:member(...)` / `file.ts:member(...)` whose file declares no such member (Python `def`/`class`/top-level assignment, `Class.method`; TS `function`/`const`/`class`/`type`/`interface`/`export`); a citation `:<digits>` (line number) | `EXEMPT`: `docs_guide.md` (describes another tree, by its own last section), `docs/superpowers/` (dated process documents), plus any path a spec names before it exists |
| `check:vocabulary` | a code span `npm run X` / `npm X` not declared by the governing `package.json`; `uv run python -m mod` whose module is absent from the governing `pyproject.toml`'s package; `uv run <tool>` not in its dependency groups; `python path.py` whose path is missing. The governing manifest is the one nearest the page, or the one in a directory the same sentence names | `EXEMPT` |
| `check:docs` | a document over 60,000 characters without an `ALLOWANCES` entry (stale when it falls back under); a table cell over 2,000 characters; a comment in hand-written source: `.py` via `python3 -m tokenize` in a child process (exit 2 if `python3` is absent), `.ts/.tsx` via the TypeScript scanner. A script or test may carry one leading header of at most ten lines; a script is a file under `tests/`, `test_*.py`, `*.test.ts`, `scripts/`, or a file with a `__main__` guard | `ALLOWANCES`; `VENDORED` (kit files under `data/`, the root rule's exemption) |
| `check:generated` | a tracked `*.generated.*` file without a first-line banner naming a command; an `UNMARKED` entry (`uv.lock`s, `package-lock.json`s, `data/generator/csv/`) that the tree no longer holds; a generator output listed in `GENERATED.md`'s table that `UNMARKED` lacks, or the reverse | `UNMARKED` |
| `check:routes` | the router (`ENTRIES`) or a declared route costs more characters than its budget, or more than 15% under it (stale); a reason names a figure, says "raised"/"lowered", or runs long. A route is the router's rows, each stop a pathspec charged for the largest file it reaches, with branches charged their worst | `ENTRIES`, `ROUTES` |

The count assertion of §6 is not built. The root rule bans literal counts, so no document states
one for it to hold, and the plan says so in `scripts/check/AGENTS.md`. **The em-dash style rule is
not adopted**, because no rule in the tree states one.

**Suites** (`*.test.ts`, `node:test`):

- each plants one violation per rule in a temp fixture tree (`fs.mkdtemp`) and asserts it fires;
- each asserts every map by name, plus its stale-entry failure and its zero-scan failure;
- `check-all.test.ts` asserts `GATES` by literal value **and** equals the `check:*` scripts of
  `package.json`, so adding a gate is a two-file change.

**Also:**

- root `package-lock.json` is committed and added to `GENERATED.md`;
- `.gitignore` already ignores `node_modules/`;
- the root's verification item 6 (the shell link loop) is replaced by `npm run check`;
- budgets in `ROUTES` are set from measured sizes **after** Phase 8, each with a present-tense
  reason.

**Order inside the phase:**

1. Write `tree.ts` and `gate.ts`.
2. Write each gate with its suite. `npm test` goes green on the fixtures.
3. Run `npm run check` against the real tree and save its output in the scratchpad. That output is
   the worklist for Phases 3–8.

## Phase 3 — `packages/agents`

**New `packages/agents/arbol/AGENTS.md`.** It takes "The decision tree" (except the compile
paragraph), "The node", "The levels", "The ends", "The node `ejecutar.vigente`" and the registry
clause. It adds:

- a validator section naming `tests/test_validator.py:PLANTED` as the full list of refusals,
  replacing the incomplete bullets;
- a file table for `base.yaml` and `fundamentos.yaml`;
- **"Adding to the tree"** checklists:
  - **A metric:**
    1. the `kernel:` block in `data/metricas.yaml`, then regenerate per tools;
    2. the family's `en` in `detectar.<family>`; a new family also goes in
       `schema.py:FAMILIES`;
    3. the L3 branch;
    4. `skills/analista/<metric>.md`;
    5. its `acciones.md` row and its manual-review owner row;
    6. a `FIRING` row in `tests/test_detect.py`;
    7. `uv run pytest`.
  - **A node or predicate:** `state.py:STATE_FIELDS`, and `walk.py:read` for a derived field. L1
    changes only by pull request against `base.yaml`.
  - **An end:** `schema.py:ENDS` and `graph.py:end_node`.
  - **An orchestrator write:** `graph.py:effects` and `BOUND_NODES`.
  - **An agent decision:** `schema.py:AGENT_DECISIONS`, `graph.py:LEAF_OUTPUTS`,
    `graph.py:fallback`, the host leaf, and the skill.
  - **An action type:** `ejecutar.automatizable`'s `en`, plus its `acciones.md` row.
- `check:citations` verifies every member named.

**Rewrite `packages/agents/AGENTS.md`** (about 20 KB):

- What runs: the validator, walk, catalogue and graph compiler. What is decided and marked: model
  calls, retry, token cap, day run, de-duplication, order, cost, Langfuse, `AgentStep`, chat and
  self-expansion.
- The `detection` row becomes `metric`, `entity`, `path`, `row` (from `graph.py:start_alert`). Add
  `transitions`. Mark `queries` as unwritten.
- Copies of closed lists become citations of `schema.py:AGENT_DECISIONS`, `schema.py:ENDS` and
  `graph.py:REASONS`.
- Per agent, keep Question, Tools, Ceiling and Never. Input/Output points to the skill contracts.
- Move the universe table to `skills/analista/politicas.md` only.
- State `revision_manual` ownership one way. The host leaf comes first, with
  `graph.py:manual_review` as its fallback.
- Record these as limits, beside the rule each one qualifies:
  - severity has no definition;
  - `catalog_from_kernel` never fills `Kpi.thresholds`;
  - `earlier_alerts` is `{id: status}`;
  - the web's `Decision`/`ChatQuestion`/`AlertStatus` shapes differ from the graph's.
- Drop the copies of challenge facts and the phrases "during the hackathon" and "yet".
- Complete the file table: `catalog.py`, `failures.py`, `metrics.py`, `yaml_loader.py`, `arbol/`.

**`skills/AGENTS.md`:**

- State that code parses `acciones.md`: `validator.py:coverage_problems` and
  `graph.py:manual_owners`.
- Mark model loading as decided.
- Drop or mark the nonexistent `expandir.md` and `proponer_kpi.md`.
- Add an "Adding a skill" checklist.

**Skill prompt fixes:**

- `analista/margen_bruto_negativo.md`: the entity becomes `(pedido_id, linea_n)`.
- `analista/descuento_en_exceso.md`: the entity becomes `(vendedor_id, semana)`, and it gains a
  `no_evidence` path.
- `vigia/contrato.md`, rule 4: add the entity fields.
- `estratega/acciones.md`: remove the banned "only", keeping the parsed table and heading intact.
- `ejecutor/contrato.md`: add instructions for `nota_manual`.
- `analista/contrato.md`: input names match the state.
- Tool names stay as decided tools, consistent with the tools page.
- Run `uv run pytest`.

## Phase 4 — `packages/tools/AGENTS.md`

- The opening says what runs (the kernel: compiler, guards, kernel tools, generator) and marks
  what is decided: MCP, `bge-m3` policies, masking, `calcular_impacto`, actions, idempotency, and
  the approved-KPI file.
- Document `CENTINELA_LECTOR_DSN` and `CENTINELA_KERNEL_DSN`, which
  `kernel.py:kernel_from_env` requires.
- State that only the "returned" half of "logged and returned" runs.
- Fix the `kpi_validar` and `kpi_catalogo` callers, and the dangling MCP pointer.
- Complete the file table: `__init__.py`, `tests/support.py`, `conftest.py`, `test_roles.py`,
  `test_primitives.py`, `test_generate.py`. Name the tests that are gates.
- Own base-KPI parity.
- Add checklists for a KPI (edit `metricas.yaml` → `uv run python -m centinela_tools.generate` →
  commit `05_kpis.generated.sql` → the tree's steps), a guard (`refusal.py:GUARDS` plus a planted
  test) and a new tool.

## Phase 5 — `data/AGENTS.md`, `GENERATED.md`, `DOUBTS.md`

**`data/AGENTS.md`:**

- Add a `docker-compose.yml` row and its setup use.
- Clarify the `salida` row.
- Link to `acciones.md` instead of counting its tables.
- Remove the history phrasing.
- Remove the parity paragraph; it now links to tools.

**`GENERATED.md`:**

- Add `npm install` (both lockfiles), `npm run build` → `dist/`, and `publish.py --build-only`.
- Fix "Its default output directory".
- Retitle "What writes today".
- Turn the `SALIDA` warning into a link to data.
- Replace the derivation grep with a pointer to `check:generated`.

**`DOUBTS.md`:**

- Fix "The first five fail".
- Debts go on the level page first. `DOUBTS.md` gets only what no level can hold:
  `publish.py:inventory`'s hard-coded parts.

## Phase 6 — `apps/web`, `apps/api`, `evals`

**`apps/web/AGENTS.md`:**

- Add a file table (`src/screens`, `shell`, `common`, `state`, `api`, `api/fixtures`, `format.ts`,
  `actionParameters.ts`, `app.css`, `index.html`, `vite.config.ts`, `design/`).
- Describe the app as screens on a simulated API, not a scaffold.
- Add the `client.ts` functions beyond the minimal API, with their routes owned by `apps/api`.
- Move the 422 to `apps/api`.
- Rewrite the phone-width incident as a property.
- Drop "three tabs".
- Add an "Adding a screen" checklist: `src/screens/` → `App.tsx` → `client.ts`, fixture and
  `types.ts` → `common/` vs `shell/` → `npm run typecheck` and `npm run arena:audit`.
- **Fix** `design/identity.html`'s link to the nonexistent `../intro/styles.css`, after reading
  the file, and its "serve over HTTP" sentence.

**`apps/api/AGENTS.md`:**

- It stays all-decided, and says so.
- Add a planned layout (package path, manifest, models, migrations).
- Add an endpoint table: the minimal API, plus what `client.ts` consumes, plus a link to spec 6's
  `/kpis…`.
- Own 409, 422 and the `request_changes` cap, with one reason.
- Name the roles.
- Add an "Adding an endpoint" rule. Once code lands, its manifest must have this page beside it
  (`check:agents`).

**`evals/AGENTS.md`:**

- Only the CSV template exists. The runner, the attack fixture and the case ids are decided.
- Map the existing pytest checks (`test_orq.py`, `test_parity.py`).
- Resolve the official-vs-generated dataset contradiction.
- Cite `test_parity.py:DAYS` instead of "three days".
- Drop "before the close".
- Add an "Adding a case" section.

## Phase 7 — `docs/challenge`, `docs/guide`

- **`docs/challenge/AGENTS.md`:** drop the "Choice in this repository" column. First confirm each
  choice is on its level.
- **`docs/guide/AGENTS.md`:** `cp .env.example .env` applies only to a fresh instance, never over
  the tracked `.env`.
- **`status.md`:** fix the Implemented row and the tools row.
- **`start-here.md`:** remove the state-table copy and the false "built from the commit" sentence.
- **`decision-tree.md`:**
  - fix L1 ≠ stages;
  - repoint `Draws:` to `arbol/AGENTS.md`;
  - add the marker to "How the tree grows" and walkthrough steps 1–2;
  - remove "today" and "still".
- **`alert-journey.md`:** repoint renamed headings; turn restated rules into links.
- **`kpi-kernel.md`:** the opening and the grants sentence link to their owners.
- Run `python3 docs/guide/publish.py --build-only <scratchpad>`, which checks the `Draws:` headings
  through `publish.py:check_draws`.

## Phase 8 — root `AGENTS.md`, last

- **The vocabulary paragraph:**
  - which parts hold code, now including `scripts/check`;
  - `Vigía` reads `kpi_consultar`;
  - "one alert per metric and entity";
  - the kernel definition reduced to its link.
- **Router rows to add:**
  - a KPI, the kernel or a guard refusal → tools, then data;
  - a node, a leaf or the registry → `arbol/AGENTS.md`;
  - a skill or prompt → `skills/AGENTS.md`;
  - **one row per feature kind** (metric/KPI, node, agent decision, tool, endpoint, screen, eval
    case), each to the "Adding…" section that owns it;
  - **a gate failed, or a new gate** → `scripts/check/AGENTS.md`;
  - a spec, a plan or how a page is written → `docs_guide.md`.
- Remove the duplicated clock route.
- "Still undecided" loses MCP.
- **Commands:** `npm install` at the root, then `npm run check` before finishing, the completion
  gate of §6, plus `npm test` and `npm run typecheck` when changing a gate.
- **Rules:** each one names its holder. Examples:
  - `check:citations` holds the citation rule and "never by line number";
  - `check:docs` holds "no comments";
  - `check:agents` holds the symlink, the single README and "a level is linked";
  - `check:vocabulary` holds "commands spelled as the manifest declares";
  - `test_roles` holds no-write;
  - the validator holds the registry.
  Drop "no gates yet". Align the commit rule with §4.
- **Verification list:** item 6 becomes `npm run check`, and item 2 points to what evals can run.
- Keep the root under about 10 KB. `check:routes` `ENTRIES` holds it.
- Finally, set the `ROUTES`/`ENTRIES` budgets from measured sizes, each with a present-tense
  reason.

## Verification

1. **`npm test`**: every planted violation fires, every map is asserted, and the registry equals
   `package.json`.
2. **`npm run typecheck`** passes.
3. **Mutation check (§7)**: on a scratch copy of the tree, inject one defect per gate (a broken
   link, a missing member, an undeclared `npm run`, a `#` comment in a `.py`, an unlinked
   `AGENTS.md`, an oversized route). Confirm `npm run check` reports each one.
4. **`npm run check`** on the real tree prints no problems and no SKIP.
5. Run `uv run pytest` in `packages/agents` and `packages/tools`. Report any database-bound skips.
6. Run `npm run typecheck` in `apps/web`, and open `design/identity.html` over HTTP.
7. Run `git grep -nE '\b(yet|today|still|now|used to|no longer)\b' -- '*.md' ':!docs/superpowers'`
   and review each hit.
8. Run `python3 docs/guide/publish.py --build-only` into the scratchpad. Publishing to Docmost is
   person-run.
9. **Cold walk (§7)**: give three fresh Explore agents "add a metric `retraso_habito`", "add a
   settings endpoint" and "a screen shows a wrong total". Record the row each picks and the
   characters each reads.
10. Run `git status --short` against `GENERATED.md`, then do an end-to-end read of every touched
    page for tense and for any fact stated twice.
11. The final commit deletes `docs/superpowers/2026-10-03-docs-refactor.md`.
