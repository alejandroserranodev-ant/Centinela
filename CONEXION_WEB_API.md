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
it; why pip needs the paths is [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#commands). The agents
call OpenAI with the key of `.env.local` at the root, as [`SETUP_OPENAI.md`](./SETUP_OPENAI.md) says:

```bash
pip install -e ../../packages/tools -e ../../packages/agents -e ".[dev]"
uvicorn centinela_api.main:app --reload
```

It listens on `http://localhost:8000` and serves its OpenAPI at `http://localhost:8000/docs`.
Without `AUTH_SECRET_KEY` in `.env.local` it signs with a random key, so a restart signs everyone
out; why the key is never versioned is [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#decisions-and-roles).

**3. The web**, from `apps/web/`:

```bash
npm install
npm run dev
```

Vite serves it on `http://localhost:5173`; where the fetch client and the API disagree is
[`apps/web/AGENTS.md`](./apps/web/AGENTS.md).

## Which `.env` each process reads

| Process | Reads | What it needs there |
|---|---|---|
| the web | `apps/web/.env`, through Vite | `VITE_API_URL`; without it the client calls `http://localhost:8000` |
| the API | the versioned `.env` at the root, then `.env.local` over it, as [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#commands) says | `DSN_ADMIN`, `AGENT_SECRET_KEY`, `CENTINELA_USUARIOS`, `AUTH_SECRET_KEY` only in `.env.local`, the kernel's DSNs and the model provider's variables of [`SETUP_OPENAI.md`](./SETUP_OPENAI.md) |

Both files are versioned with local values and no secret, so a clone runs with no copying. Without
`LLM_MODEL`, a day run logs the provider's error and ends with no new alerts, which looks like a
quiet day.

## Signing in

Each profile of `CENTINELA_USUARIOS`, in the root `.env`, signs in with the demo password `HackathonByPass`:

| Email | Role · area |
|---|---|
| gerente@andina.test | `gerente` |
| comercial@andina.test | `lider_proceso` · `Comercial` |
| cartera@andina.test | `lider_proceso` · `Analista de cartera` |
| compras@andina.test | `lider_proceso` · `Compras` |
| analista@andina.test | `analista` |
| auditoria@andina.test | `auditor` |

The password is shared and public on purpose, because the `.env` is versioned and the team signs in during the hackathon. To change it, hash the new one and replace the `clave` of every profile in `CENTINELA_USUARIOS`, or of only the profiles that should differ:

```
echo NuevaClave | python -m centinela_api.auth hash
```

For a private password, put the whole `CENTINELA_USUARIOS` in `.env.local`, which is not versioned and wins over `.env`.
