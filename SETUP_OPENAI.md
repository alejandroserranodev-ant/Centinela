# Configuring the model provider

This page says which model provider the agents call and where its settings come from. It sits at
the root, not in [`packages/agents`](./packages/agents/AGENTS.md#models), the level that owns the
provider, because the team keeps the file structure as it is; that page states what a provider
does, and this one only how it is configured.

## The variables the code reads

`packages/agents/centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)`
reads them when `apps/api` first builds the orchestrator, in
`apps/api/src/centinela_api/agentes.py:get_orchestrator()`. No other variable reaches a provider.

| Variable | Read by | Value |
|---|---|---|
| `LLM_PROVIDER` | `get_provider` | `ollama`, the default, or `openai`; `anthropic` raises `NotImplementedError` |
| `LLM_MODEL` | `get_provider` | the model's name, such as `qwen3:8b` or `gpt-4o-mini`; it has no default, and `get_provider` raises `ValueError` without it |
| `OPENAI_API_KEY` | `packages/agents/centinela_agents/openai_provider.py:OpenAIProvider` | required with `openai`; a key that does not start with `sk-` is logged as a warning, and the provider lists the account's models at construction, so a key OpenAI refuses fails there |
| `OLLAMA_API_URL`, then `OLLAMA_BASE_URL` | `packages/agents/centinela_agents/ollama_provider.py:OllamaProvider` | Ollama's address, `http://localhost:11434` when neither is set |

**`openai` is installed by `apps/api`'s manifest, not by `packages/agents`'s**, so the provider
imports only in the environment `apps/api` runs in; how that shows in the tests is
[`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#commands).

**With `openai`, the data leaves the machine.** Every prompt, with the figures and entity names of
the alert, goes to OpenAI's servers unmasked; the decision it departs from is in
[`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#models).

## Which `.env` file is loaded

`apps/api/src/centinela_api/config.py` calls `load_dotenv()` with no path when it is imported. It
loads the first `.env` it finds walking up from `apps/api/src/centinela_api/`, so an `apps/api/.env`
hides a `.env` at the root, and a variable already set in the shell wins over both.

- [`.env.example`](./.env.example), at the root, lists the provider's variables. Its `OLLAMA_MODEL`,
  `LOG_LEVEL` and `ENVIRONMENT` are read by no code.
- [`apps/api/.env.example`](./apps/api/.env.example) lists the API's own, `DSN_ADMIN` and
  `AGENT_SECRET_KEY`, and none of the provider's.

So with an `apps/api/.env`, the provider's variables go in it too, or are exported in the shell
that starts the API.

## Keeping the key secret

- **The key lives only in a `.env` or in the shell**: `.gitignore` ignores `.env`, and no file in
  the tree carries a real key.
- **A key that was pasted into a chat, a commit or a log is rotated** in OpenAI's console, because
  it can no longer be called secret.
- **The key gets the narrowest scope** OpenAI's console offers for chat completions.
