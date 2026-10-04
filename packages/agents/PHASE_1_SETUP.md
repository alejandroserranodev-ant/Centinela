# The model providers

This page covers how `packages/agents` reaches a language model: the provider interface, its
two implementations and the factory that picks one. The file keeps its historical name and sits
beside [`AGENTS.md`](./AGENTS.md) because the team keeps the file structure; `AGENTS.md` is the
level page, states the level's rules and links here. How to configure a provider (variables,
`.env`, keys) is [`../../SETUP_OPENAI.md`](../../SETUP_OPENAI.md).

## The interface

`centinela_agents/llm_provider.py:LLMProvider(config)` is the abstract class every provider
implements: `health_check()`, `generate_text(request)` and `generate_structured(request)`. A
request carries a system prompt, a user prompt, an optional temperature and `top_p`, a `thinking`
flag and an optional token cap; `LLMStructuredRequest` adds the JSON schema the answer must
follow. A response carries the text, the stop reason, the model and a `usage` dict with
`prompt_tokens` and `completion_tokens`; `LLMStructuredResponse` adds the parsed dict.
`centinela_agents/llm_provider.py:ModelConfig` holds the provider, the model, the sampling
defaults (temperature 0, `top_p` 1), `thinking` and `timeout_seconds`.

The provider does not retry. Whoever calls it decides what a failure means, and the agent leaves
catch every exception themselves ([`PHASE_4_SETUP.md`](./PHASE_4_SETUP.md)).

## The implementations

- **`centinela_agents/ollama_provider.py:OllamaProvider(config)`** posts to `/api/chat` with
  `requests`, at `OLLAMA_API_URL`, else `OLLAMA_BASE_URL`, else `http://localhost:11434`. Its
  constructor lists `/api/tags` and raises `ValueError` when the server is down or the model is
  not pulled, so constructing one fails without a running Ollama; `health_check()` asks the same
  and answers `False` instead. A request sends `temperature`, `top_p` and the token cap
  `num_predict` under `options`, and the thinking flag as `think`, always, because a `qwen3` model
  thinks when `think` is absent. A structured request sends the schema as Ollama's `format`. It
  reads the stop reason from `done_reason` and token counts from `prompt_eval_count` and
  `eval_count`.
- **`centinela_agents/openai_provider.py:OpenAIProvider(config, skip_health_check)`** uses the
  `openai` client with `OPENAI_API_KEY` and calls `models.list()` on construction unless told to
  skip it. A structured request sends the schema as a non-strict `json_schema` response format,
  leaving the system prompt the skill alone. It ignores the thinking flag, which OpenAI's chat
  models do not take. Its client waits `timeout_seconds` of the config, and a call past it raises
  `TimeoutError`. It is the provider the agents run on, for the reason
  [`AGENTS.md`](./AGENTS.md#models) gives.

## The factory

`centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)` reads
`LLM_PROVIDER` (default `ollama`) and `LLM_MODEL` (required, `ValueError` without it) unless the
arguments override them, and returns the matching provider. `anthropic` raises
`NotImplementedError`. The module imports both implementations at load time, and `pyproject.toml`
declares both clients, `openai` and `requests`. `apps/api` calls it once to build the orchestrator
([`PHASE_5_SETUP.md`](./PHASE_5_SETUP.md)).

## Tests

`uv run pytest tests/test_providers.py` runs the provider tests with mocked HTTP.
`tests/test_manifest.py` fails when a module of the package imports a distribution the manifest
does not declare.
