# docs/guide: the guide a developer reads in Docmost

This level holds the guide to Centinela that a developer new to it reads top to bottom, and the
Docmost instance it is read in. The guide is not a second copy of the tree's pages: Docmost holds
nothing written there, only what `publish.py` builds from this repository.

## Why each file exists

| Path | Why it exists |
|---|---|
| `guide.json` | the manifest: the page tree and the reading order, each page a repo file, a generated page, or a title with a one-line intro |
| `chapters/` | the pages only this guide owns: the reading order, the journey of one alert, the decision tree and the KPI kernel as decided, and the status map |
| `publish.py` | builds the zip from the manifest and imports it into Docmost as the space `centinela` |
| `docker-compose.yml` | Docmost with its own Postgres and Redis |
| `.env.example` | every setting the compose and `publish.py` read; the template a fresh instance starts from |
| `.env` | the settings of the team's instance, versioned on purpose so every member signs in to Docmost with the same admin credentials; the instance listens only on localhost and holds nothing but the published guide |

## Decisions

- **Docmost holds a projection, never a source.** Every run of `publish.py` deletes the space and
  imports it again, and the default group reads it and cannot write it, because a page edited in
  Docmost would be a copy of a fact that goes stale and fails nothing.
- **A page is imported, a chapter, or generated, and never a restatement.** A level page and the
  root companions are copied verbatim, so the guide repeats no fact they own. A chapter owns only
  what no level page states. The code inventory is derived from `git ls-tree` of the published
  commit, so "what is code" cannot go stale.
- **The tree and kernel chapters own their design until the specs that build it execute.** Each
  pending spec names the chapter section it moves into a level page, and that section then shrinks
  to a link. A chapter never links into `docs/superpowers/`, because a spec is deleted once executed.
- **A diagram of a level page's fact lives in a chapter, captioned `Draws:` with the page and the
  heading it draws**, and `publish.py:check_draws(text, source)` refuses the build when that heading
  is gone. A diagram in a level page would cost every agent reading that route; the caption is what
  sends a change to the page back to its diagram. The check sees a heading vanish, not a table
  change under it.
- **Docmost `0.96.0`, Postgres `18.6` and Redis `8.10.2` are pinned**, because `publish.py` relies on
  the import behaviour of that version: a page is titled by its first heading, siblings are ordered
  by file name, a relative `.md` link becomes an internal link only without a `#fragment`, and a
  ` ```mermaid ` block renders as a diagram. A change of version is re-verified against those four.
- **`publish.py` signs in as the UI does**, through `/api/auth/setup` on a fresh instance and
  `/api/auth/login` after, because Docmost gives API keys to its enterprise edition only.
- **Docmost listens on `DOCMOST_PORT`, 3100 by default, and its Postgres and Redis expose no host
  port**, so it runs beside `data/docker-compose.yml`. The compose project is `centinela-guide`, so
  removing its volumes never touches the dataset's.
- **A link to a repo file the guide does not import points to that file on GitHub at the published
  commit**, derived from `git remote get-url origin`, because Docmost has no copy of it.
- **The guide is written in English** like every page of the tree, so imported pages and chapters
  read in one language.

## Commands

Run from this directory, with Python 3 and Docker Compose:

| Command | What it does |
|---|---|
| `cp .env.example .env` | then fill `APP_SECRET` with `openssl rand -hex 32`, and both passwords |
| `docker compose up -d` | starts Docmost at `APP_URL`; `curl -fsS "$APP_URL/api/health"` answers once it is ready |
| `python publish.py` | builds the guide and replaces the space `centinela`; prints its address |
| `python publish.py --build-only DIR` | writes the guide's Markdown tree to `DIR` and touches no Docmost |

## Rules of this level

- **A correction goes into the repository and is published**, never into Docmost.
- **A chapter states only what no level page owns**, and links the page that owns anything else.
  *No gate holds this.*
- **A section describing a design with no code opens with `> **Decided, not implemented.**`**,
  which `publish.py` turns into a warning box. *No gate holds this.*
- **A new page enters through `guide.json`**, and a repo page it links that the manifest does not
  import reaches the reader as a GitHub link.

## Verified by a person

After a change to a chapter, to `guide.json`, or to a page the guide imports or a diagram draws:
publish, open each changed page in Docmost, and check that every diagram renders as a drawing and
not as code, and that each internal link opens a Docmost page.
