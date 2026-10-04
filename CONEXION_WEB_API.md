# Running the web against the API

This page owns one procedure that crosses three levels: starting the database, `apps/api` and
`apps/web` on one machine so the screens talk to the real API. It sits at the root rather than on
a level's page, a departure from the rule that a fact lives on the level that owns it, because the
team keeps the file structure as it is. Every fact it does not own is linked to the page that does.

## The three processes

Each runs in its own terminal, in this order, because the API reads the database on its first
request and the web reads the API on load.

**1. The database**, from `data/`. The compose and what it loads on its first start are
[`data/AGENTS.md`](./data/AGENTS.md#setting-up-the-database). The API's own schema `api` is not
among them, so it is applied once, from `apps/api/`:

```bash
psql "postgresql://centinela:centinela@localhost:5432/centinela" -f sql/01_esquema.sql
```

**2. The API**, from `apps/api/`, in a Python 3.12 environment, because `packages/agents` asks for
it. `apps/api/pyproject.toml` declares `centinela-agents`, and pip finds it only at the path the
command names:

```bash
pip install -e ../../packages/agents -e ".[dev]"
cp .env.example .env
uvicorn centinela_api.main:app --reload
```

It listens on `http://localhost:8000` and serves its OpenAPI at `http://localhost:8000/docs`.
What it serves and refuses is [`apps/api/AGENTS.md`](./apps/api/AGENTS.md).

**3. The web**, from `apps/web/`:

```bash
npm install
cp .env.example .env
npm run dev
```

Vite serves it on `http://localhost:5173`. What the screens read from the API, and where the
fetch client and the API disagree, is [`apps/web/AGENTS.md`](./apps/web/AGENTS.md).

## Which `.env` each process reads

| Process | Reads | What it needs there |
|---|---|---|
| the web | `apps/web/.env`, through Vite | `VITE_API_URL`; without it the client calls `http://localhost:8000` |
| the API | the nearest `.env` found walking up from `apps/api/src/centinela_api/`, through `apps/api/src/centinela_api/config.py`'s call to `load_dotenv()` | `DSN_ADMIN` and `AGENT_SECRET_KEY`, and the model provider's variables of [`SETUP_OPENAI.md`](./SETUP_OPENAI.md) |

**`apps/api/.env` hides the root `.env`.** `load_dotenv()` stops at the first file it finds, so
once `apps/api/.env` exists, the root `.env` is not read, and the model provider's variables
belong in `apps/api/.env` too or in the shell. Without `LLM_MODEL`, a day run logs the
provider's error and ends with no new alerts, which looks like a quiet day.
