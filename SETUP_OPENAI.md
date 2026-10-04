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

**`openai` and `requests` are dependencies of `packages/agents`**, declared in its manifest, so
both providers import wherever the package is installed, `uv sync` alone included.

**With `openai`, the data leaves the machine.** Every prompt, with the figures and entity names of
the alert, goes to OpenAI's servers unmasked; the decision it departs from is in
[`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#models).

## Which `.env` file is loaded

The provider's variables live in the `.env` at the root, which is versioned, because the
competition's rules ask for it, and carries no secret: `LLM_PROVIDER=ollama`, `LLM_MODEL` and
`OLLAMA_API_URL`, with `OPENAI_API_KEY` empty. How `apps/api` loads it, and the `.env.local` that
overrides it, is [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#commands).

## Keeping the key secret

- **The key lives only in `.env.local` or in the shell**: `.gitignore` ignores `.env.local`, the
  versioned `.env` leaves `OPENAI_API_KEY` empty, and no file in the tree carries a real key.
- **A key that was pasted into a chat, a commit or a log is rotated** in OpenAI's console, because
  it can no longer be called secret.
- **The key gets the narrowest scope** OpenAI's console offers for chat completions.
