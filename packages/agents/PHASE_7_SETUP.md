# Cost and latency counters

This page covers `centinela_agents/observability.py`. The file keeps its historical name and sits
beside [`AGENTS.md`](./AGENTS.md) because the team keeps the file structure; `AGENTS.md` is the
level page, owns what an alert's cost and trace are decided to be, and links here.

Only `centinela_agents/orchestrator_v2.py` uses this module, and nothing uses that one
([`PHASE_9_SETUP.md`](./PHASE_9_SETUP.md)). No running path records cost or latency.

## What it holds

- `TOKEN_COSTS`: the providers' prices in dollars per thousand input and output tokens, per
  provider and model it knows; Ollama, and a model missing from the table, cost zero.
- `centinela_agents/observability.py:TokenUsage` holds one call's tokens; `cost()` multiplies each
  count by its rate and divides by `TOKENS_PER_RATE`, the thousand tokens a rate prices.
- `AgentMetrics` and `AlertMetrics` add calls, retries, failures, tokens and latency per agent and
  per alert; `AlertMetrics.to_dict()` returns them as one record.
- `centinela_agents/observability.py:MetricsCollector(alert_id, metric, entity, day)` is what a
  caller drives: `record_agent_call(agent, usage, latency_ms)`, `record_retry(agent)`,
  `record_failure(agent)`, `finish(status)`, `get_summary()`.
- `centinela_agents/observability.py:LangfuseTracer(api_key, enabled)` is enabled only with an API
  key and the `langfuse` package, and even then only writes log lines: it sends nothing to
  Langfuse.
- `setup_logging(level)` configures the package's logger.

## Tests

`uv run pytest tests/test_observability.py` checks the counters and the pricing.
