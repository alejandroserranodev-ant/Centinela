# Output validation and the second orchestrator

This page covers `centinela_agents/output_validator.py` and `centinela_agents/orchestrator_v2.py`.
The file keeps its historical name and sits beside [`AGENTS.md`](./AGENTS.md) because the team
keeps the file structure; `AGENTS.md` is the level page and links here.

**Nothing outside the tests imports `centinela_agents/orchestrator_v2.py`.** `apps/api` builds the orchestrator of
[`PHASE_5_SETUP.md`](./PHASE_5_SETUP.md), so neither the validator nor the counters of
[`PHASE_7_SETUP.md`](./PHASE_7_SETUP.md) run on a real alert.

## The validator

`centinela_agents/output_validator.py:OutputValidator(strict)` validates one agent output at a
time: `validate_cause`, `validate_action`, `validate_executed_action`, `validate_decision` and
`validate_rejection_classifier`, each taking the output dict. A check fails in one of three
categories, carried by `OutputValidationError(category, message, output)`:

- **schema**: the dict does not build the model of [`PHASE_2_SETUP.md`](./PHASE_2_SETUP.md);
- **security**: a text field holds an unfilled `{placeholder}`, an SQL keyword followed by a space,
  or a word such as `ignore`, `override` or `bypass`, which also refuses ordinary Spanish or
  English prose that contains them;
- **domain**: an identified cause has no evidence or a sentence too short.

With `strict` true a failure raises; with it false the validator logs a warning and returns
`None`. The decision and classifier checks raise in either mode.

## The second orchestrator

`centinela_agents/orchestrator_v2.py:CentinelaOrchestratorV2` subclasses
`CentinelaOrchestrator` with a `strict_validation` flag, and adds `start_with_metrics(...)` and
`resume_with_metrics(alert_id, decision, collector)`, which validate the outputs in the state and
record each agent's call. It estimates tokens from latency instead of reading the provider's
`usage`, so the cost it records is not measured.

## Tests

`uv run pytest tests/test_integration_phase9.py`.
