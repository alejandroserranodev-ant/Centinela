# scripts/check: the gates that hold the documentation to the tree

Each gate states one claim about the tree and fails when the claim stops being true. A gate is
TypeScript that Node runs directly by type stripping, with no build step and no runtime besides
Node and npm. The manifest is the root [`package.json`](../../package.json), because the gates walk
the whole tree. The practice they port is section 6 of [`docs_guide.md`](../../docs_guide.md).

## Commands

All run from the root, after `npm install` there.

| Command | Does |
|---|---|
| `npm run check` | every gate in one sweep, which reports every problem and fails on any failure or skip. It is the completion gate: run it once, when a change is finished |
| `npm run check:agents`, `npm run check:citations`, … | one gate, while working |
| `npm test` | the suites, which plant one violation per rule in a temporary tree and assert every map by name |
| `npm run typecheck` | `tsc` over this directory, with the type-stripping limits as compiler options |

## The gates

| Gate | Fails when | Its maps |
|---|---|---|
| `check:agents` | an `AGENTS.md` that no chain of links from the root `AGENTS.md` reaches; a `README.md` other than the root's; `CLAUDE.md` is not a symlink to `AGENTS.md`; an npm or a uv manifest has no `AGENTS.md` beside it to name its commands | `SURVIVORS` |
| `check:citations` | a relative link or its `#anchor` resolves to nothing; a path in a code span resolves neither from the root, beside the page nor from the root of the package holding the page; a `path:member(parameters)` citation of a Python or TypeScript file names a member the file does not declare; code is cited by line number | `EXEMPT`, `EXEMPT_DOCUMENTS` |
| `check:vocabulary` | a page names an `npm run` script, a `uv run python -m` module, a `uv run` tool or test file, or a `python` script that the governing manifest does not declare or the tree does not hold. The governing manifest is the nearest one of its kind, a manifest in a directory the same paragraph names, or the directory a `cd` enters | `EXEMPT`, `EXEMPT_DOCUMENTS` |
| `check:docs` | a document passes its character cap or a table cell passes its own; hand-written source carries a comment other than one leading header of at most ten lines on a script, a test or a SQL file | `ALLOWANCES`, `VENDORED` |
| `check:generated` | a file named `.generated.` carries no banner naming its command; a lockfile is missing from `UNMARKED`; `GENERATED.md` does not name an output | `UNMARKED` |
| `check:contract` | `apps/web/src/api/schema.generated.ts` differs from what `npm run contract` writes from `apps/web/src/api/openapi.json`; its other half is `apps/api/tests/test_contrato.py`, which fails when that document differs from what the API exports. To fix: run `python -m centinela_api.contrato` in `apps/api`, then `npm run contract` in `apps/web` | none |
| `check:routes` | the router, or the route of one of its rows, costs more characters than its budget or more than 15% less; a budget's reason names a figure, tells its history or runs long | `ENTRIES`, `ROUTES` |

A route is what a reader pays past the router: the files the row's "Start at" cell links, each
charged whole. The stops are read from the router itself, so a route cannot name a stop the
router does not.

## Decisions

- **One walk.** `tree.ts:walk(root)` lists the tree with `git ls-files -co --exclude-standard` and
  drops the directories in `tree.ts:FOREIGN`. No gate spells its own skip set, so a worktree under a
  foreign directory is never read as a second copy of the tree.
- **A gate's logic is pure functions that return problem strings**, and the work sits behind
  `import.meta.main`. A suite imports a gate and calls it on a planted tree without running it.
- **Every map carries its reason as a string value, and a stale entry fails.** An exemption names
  the page and the span it excuses, so it dies with them. The sweep also fails a gate that walked
  nothing, because a gate over an empty tree passes every rule.
- **A gate that cannot run exits 2 and prints SKIP.** `check:docs` needs `python3` for Python's own
  tokenizer and `typescript` for its parser, because a hand-written lexer misreads a `//` inside a
  string or JSX. The sweep reports INCOMPLETE and fails, because this tree treats a skip as a
  failure.
- **`check-all.ts:GATES` is the registry**, and `check-all.test.ts` holds it equal by literal
  value to the `check:` scripts of the root manifest. A new gate is a change to both files, on
  purpose.
- **Dated process documents** under `docs/superpowers/` are skipped by the gates that read prose,
  because a spec or a plan is deleted once executed.
- **What no gate holds, on purpose.** There is no count assertion, because the root rule bans a
  literal count of what grows, so no document states one for it to hold. There is no prose style
  gate, because no style rule is stated.

## Adding a gate

1. Write `check-<name>.ts`. It exports `problems(root)` and its maps, and calls
   `gate.ts:runGate(problems)` under `import.meta.main`. It reads the tree only through `tree.ts`.
2. Write `check-<name>.test.ts`. Plant one violation per rule with `support.ts:plant(files)`,
   assert every map by name, and assert its stale-entry and zero-scan failures.
3. Add `check:<name>` to the root `package.json` and to `check-all.ts:GATES`, then add a row to
   the table above.
4. Run `npm test`, `npm run typecheck` and `npm run check`.
