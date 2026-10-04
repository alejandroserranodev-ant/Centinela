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
| `LLM_MODEL` | `get_provider` | the model's name, `qwen3:4b-instruct` in the versioned `.env`, or one such as `gpt-4o-mini`; it has no default, and `get_provider` raises `ValueError` without it. Which model a machine runs is [`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#models) |
| `CENTINELA_CACHE_RESPUESTAS` | `packages/agents/centinela_agents/provider_factory.py:cached(provider)` | how many model answers the process keeps, 256 by default; `0` turns the cache off |
| `LLM_MODEL_RAZONA` | `packages/agents/centinela_agents/provider_factory.py:get_reasoning_provider()` | a second model for `Analista` and `Estratega`; empty, they use `LLM_MODEL` |
| `OPENAI_API_KEY` | `packages/agents/centinela_agents/openai_provider.py:OpenAIProvider` | required with `openai`; a key that does not start with `sk-` is logged as a warning, and the provider lists the account's models at construction, so a key OpenAI refuses fails there |
| `OLLAMA_API_URL`, then `OLLAMA_BASE_URL` | `packages/agents/centinela_agents/ollama_provider.py:OllamaProvider` | Ollama's address, `http://localhost:11434` when neither is set |

**`openai` and `requests` are dependencies of `packages/agents`**, declared in its manifest, so
both providers import wherever the package is installed, `uv sync` alone included.

**The agents run on `openai`, with `gpt-4o-mini`.** Every prompt, with the figures and entity
identifiers of the alert, goes to OpenAI's servers. Why the cloud and not a local model, and what
a machine that runs Ollama sets instead, is [`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#models).

## Which `.env` file is loaded

The provider's variables live in the `.env` at the root, which is versioned, because the
competition's rules ask for it, and carries no secret: `LLM_PROVIDER=openai`, `LLM_MODEL` and an
empty `LLM_MODEL_RAZONA`, with `OPENAI_API_KEY` empty. The key goes in `.env.local`, as one line
`OPENAI_API_KEY=sk-...`. How `apps/api` loads it, and the `.env.local` that
overrides it, is [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#commands).

## Keeping the key secret

- **The key lives only in `.env.local` or in the shell**: `.gitignore` ignores `.env.local`, the
  versioned `.env` leaves `OPENAI_API_KEY` empty, and no file in the tree carries a real key.
- **A key that was pasted into a chat, a commit or a log is rotated** in OpenAI's console, because
  it can no longer be called secret.
- **The key gets the narrowest scope** OpenAI's console offers for chat completions.
