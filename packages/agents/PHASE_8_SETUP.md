# The schema and security checks in `tests/test_evals.py`

This page covers `tests/test_evals.py`. The file keeps its historical name and sits beside
[`AGENTS.md`](./AGENTS.md) because the team keeps the file structure; `AGENTS.md` is the level page
and links here.

Despite its name, the module holds unit tests, not evaluation cases: it calls no model, no agent
and no API. The evaluation cases that drive the system and check its answers against the data are
[`../../evals/AGENTS.md`](../../evals/AGENTS.md)'s.

## What it checks

- **Domain**: the output models of [`PHASE_2_SETUP.md`](./PHASE_2_SETUP.md) accept a well-formed
  cause, action, executed action, decision and classifier output.
- **Security**: `centinela_agents/security.py` masks the same value the same way twice, finds API
  keys, SQL and injection phrases, and leaves no placeholder unfilled
  ([`PHASE_6_SETUP.md`](./PHASE_6_SETUP.md)).
- **Hallucination**: the models refuse a missing required field, an action type or confidence
  level outside the closed lists, and a cause without evidence.
- **Regression**: boundary values, such as an action with zero impact or a cause with no queries
  reviewed, still validate.

Each check runs against the models and functions directly, so it says what they accept, not what a
model produces.

## Tests

`uv run pytest tests/test_evals.py`.
