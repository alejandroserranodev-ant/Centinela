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

## What writes today

| Generator | Writes | Why its output carries no mark |
|---|---|---|
| `data/generator/generar_dataset.py` | one CSV per table into `data/generator/csv/` by default, or into `SALIDA` | CSV has no room for a banner, and the names must match the table names `data/sql/02_carga.sql` loads |
| `arena-to-prod`, run by `npm run dev` and `npm run build` in `apps/web` | `apps/web/src/arena.generated.css` and `apps/web/src/icons.generated.css`, from `apps/web/arena.config.json` and `apps/web/design/centinela/` | none needed: the name says so, and git ignores both |
| `uv sync` and `uv lock`, run in `packages/agents` and in `packages/tools` | `packages/agents/uv.lock` and `packages/tools/uv.lock`, each from the `pyproject.toml` beside it | uv writes the file whole and owns its format; the defect is in the `pyproject.toml` files, and `uv lock` writes the file again |
| `docs/guide/publish.py` | the Docmost space `centinela`, whole, from `docs/guide/guide.json`; its zip goes to a temporary directory outside the tree | none possible: its output lives in Docmost, outside the tree, so an edit made there is lost on the next publish and its source is always in this repository |

Its default output directory is ignored by git. **Never point `SALIDA` at `data/csv/`**: that is the
official evaluation dataset, written by the kit and by no generator in this tree. How to run it is
[`data/AGENTS.md`](./data/AGENTS.md).

List the generators from the tree rather than from this table:
`grep -rl 'to_csv\|write_text\|open(.*"w"' --include='*.py' --include='*.ts' . | grep -v node_modules`.

## After a run

`git status --short` is the list of what the generators decided to write. **A file you did not
expect means a generator you did not know reads what you edited. A file you expected and did not
get means your source is in the wrong place.**
