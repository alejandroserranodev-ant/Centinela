# The output schemas

This page covers the Pydantic models an agent's model output is validated against, in
`centinela_agents/schema.py` after the decision tree's own models. The file keeps its historical
name and sits beside [`AGENTS.md`](./AGENTS.md) because the team keeps the file structure;
`AGENTS.md` is the level page and links here. The tree's models above them (`Tree`, `Node`,
`Leaf`) are [`arbol/AGENTS.md`](./arbol/AGENTS.md)'s.

## The models

Every model forbids extra fields, so an answer with an invented key fails validation.

- **`Figure`**: `value`, `unit` and `queryId`. A figure names the query that produced it.
- **`Sentence`** and **`Evidence`**: a text (`text` or `claim`) and the figures it cites.
- **`Confidence`**: a `level` of `high`, `medium` or `low` and a list of `assumptions`, not a
  score.
- **`Cause`**: the union of `CauseIdentified` (`kind` `identified`, a `sentence`, at least one
  `evidence`, an optional `same_cause_as`) and `CauseNoEvidence` (`kind` `no_evidence`, a `reason`,
  the `queriesReviewed`). The union is plain, and callers pick the member by reading `kind`.
- **`Action`**: `id`, `title`, `description`, a `type` from the closed list `email_draft`, `task`,
  `purchase_order_draft`, `price_change_draft`, its `parameters`, an `impact` figure that is `null`
  when the action type has no formula, and a `confidence`.
- **`InsufficientCause`**: what `Estratega` returns when the cause supports no action.
- **`ExecutedAction`**: what `Ejecutor` returns, with `nota_manual` added to the action types.
- **`Decision`**: `approve`, `edit`, `reject` or `request_changes`, with the action, the edited
  parameters or the reason.
- **`RejectionClassifierOutput`**: the `destino` of a rejection reason, `causa`, `propuesta`,
  `ambos` or `ninguno`.

## Against the API's models

`apps/api` declares its own contract in `apps/api/src/centinela_api/modelos.py`, and the two
differ: there a figure's key is `query_id` (camelCase only on the wire), a cause's `sentence` is a
`Sentence` rather than a string, and `Cause` is a union discriminated by `kind`.
`apps/api/src/centinela_api/agentes.py:state_to_alert(alert_id, state, detection, day_str)`
converts an agent's output to the API's models; a change to either side is a change to that
converter.

## Tests

`uv run pytest tests/test_schemas.py` checks these models; `tests/test_schema.py` checks the
tree's.
