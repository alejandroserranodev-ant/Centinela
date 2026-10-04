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
  constructor calls `health_check()`, which lists `/api/tags` and raises `ValueError` when the
  server is down or the model is not pulled, so constructing one fails without a running Ollama.
  A structured request sends the schema as Ollama's `format`. It reads token counts from
  `prompt_eval_count` and `eval_count`. It sends `temperature`, `top_p` and `thinking` as
  top-level fields rather than under `options` and as `think`, and reads `stop_reason` rather than
  Ollama's `done_reason`, so Ollama ignores the sampling settings and the thinking flag.
- **`centinela_agents/openai_provider.py:OpenAIProvider(config, skip_health_check)`** uses the
  `openai` client with `OPENAI_API_KEY` and calls `models.list()` on construction unless told to
  skip it. A structured request asks for `response_format` `json_object` with the schema in the
  prompt, not a strict JSON schema. Its timeout messages name `self.timeout`, which the class
  never sets. Importing the module raises `ImportError` when `openai` is not installed, and
  `pyproject.toml` does not declare `openai`. This provider sends the prompt off the machine,
  against the level's rule that models run locally ([`AGENTS.md`](./AGENTS.md)).

## The factory

`centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)` reads
`LLM_PROVIDER` (default `ollama`) and `LLM_MODEL` (required, `ValueError` without it) unless the
arguments override them, and returns the matching provider. `anthropic` raises
`NotImplementedError`. The module imports both implementations at load time, so `openai` must be
installed even to use Ollama. `apps/api` calls it once to build the orchestrator
([`PHASE_5_SETUP.md`](./PHASE_5_SETUP.md)).

## Tests

`uv run pytest tests/test_providers.py` runs the provider tests with mocked HTTP. Collection fails
unless `openai` is installed in the environment, because the manifest does not declare it.
