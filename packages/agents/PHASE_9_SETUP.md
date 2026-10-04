# Output validation

This page covers `centinela_agents/output_validator.py`. The file keeps its historical name and sits
beside [`AGENTS.md`](./AGENTS.md) because the team keeps the file structure; `AGENTS.md` is the
level page and links here.

**Nothing outside the tests runs the validator.** Each leaf builds its own output with the models
of [`PHASE_2_SETUP.md`](./PHASE_2_SETUP.md) and refuses what does not build, as
[`AGENTS.md`](./AGENTS.md#models) says.

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

## Tests

`uv run pytest tests/test_integration_phase9.py`.
