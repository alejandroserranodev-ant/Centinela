# What a machine writes, and what you do

**Before you edit a file in this tree, know which half of it is yours.** An edit to a file a
generator writes survives until the generator runs again and then goes, and nothing fails in
between.

## A file is one of three things

**Written by a machine, and its name says so.** `<stem>.generated.<ext>`. Never edit one; the defect
is in its source.

**Written by a machine, and its name does not say so.** A file a generator writes whole carries a
banner on its first line naming the command that writes it, or it is listed below with the reason
it can carry neither.

**Written by a person, with a region a machine writes inside it.** Nothing reveals it from outside.
Read the file.

## The generators

| Generator | Writes | Why its output carries no mark |
|---|---|---|
| `data/generator/generar_dataset.py` | one CSV per table into `data/generator/csv/`, which git ignores, or into the directory `SALIDA` names; [`data/AGENTS.md`](./data/AGENTS.md#the-generator) says how to run it | CSV has no room for a banner, and the names must match the table names `data/sql/02_carga.sql` loads |
| `npm install`, run at the root and in `apps/web` | `package-lock.json` from the root `package.json`, and `apps/web/package-lock.json` from `apps/web/package.json` | npm writes each file whole and owns its format, and JSON has no room for a banner; the defect is in the `package.json` beside it |
| `arena-to-prod`, run by `npm run dev` and `npm run build` in `apps/web` | `apps/web/src/arena.generated.css` and `apps/web/src/icons.generated.css`, from `apps/web/arena.config.json` and `apps/web/design/centinela/` | none needed: the name says so, and git ignores both |
| `npm run build` in `apps/web` | `apps/web/dist/`, the built app | none needed: git ignores the directory, and nothing in the tree reads it |
| `uv sync` and `uv lock`, run in `packages/agents` and in `packages/tools` | `packages/agents/uv.lock` and `packages/tools/uv.lock`, from `packages/agents/pyproject.toml` and `packages/tools/pyproject.toml` | uv writes the file whole and owns its format; the defect is in the manifest beside it, and `uv lock` writes the file again |
| `uv run python -m centinela_tools.generate`, run in `packages/tools` | `data/sql/05_kpis.generated.sql`, from `data/kernel/fuentes.yaml`, `data/metricas.yaml` and the view names of `data/sql/03_capa_semantica.sql` and `data/sql/04_vistas_causa.sql` | none needed: the name says so, and its banner names the command; `packages/tools/tests/test_generate.py` fails when the file differs from what the generator writes |
| `python3 docs/guide/publish.py`, with no argument | the Docmost space `centinela`, whole, from `docs/guide/guide.json`; its zip goes to a temporary directory outside the tree | none possible: its output lives in Docmost, outside the tree, so an edit made there is lost on the next publish and its source is always in this repository |
| `python3 docs/guide/publish.py --build-only DIR` | the guide's Markdown tree into `DIR`, deleting whatever `DIR` held first | none needed: `DIR` is a directory you name, so point it outside the tree or at a path git ignores |

**`data/csv/` is written by no generator.** It is the official dataset, and the rule that keeps
`SALIDA` off it is [`data/AGENTS.md`](./data/AGENTS.md#rules-of-this-level)'s.

**Derive the generators from the tree, not from this table.** `npm run check:generated`, described
in [`scripts/check/AGENTS.md`](./scripts/check/AGENTS.md), fails when a file named `.generated.`
carries no banner naming its command, when a lockfile is missing from its list, and when this page
names no entry of that list in a code span. A generator that writes neither kind escapes it, which
is why the reading after a run below stays.

## After a run

`git status --short` is the list of what the generators decided to write. **A file you did not
expect means a generator you did not know reads what you edited. A file you expected and did not
get means your source is in the wrong place.**
