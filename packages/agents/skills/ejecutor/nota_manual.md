# Ejecutor: the manual note

`action.type` is none of the types that have a tool, so a person does the step by hand.

1. Write one sentence in Spanish that names the manual step: what `action.title` says, for whom
   `action.parameters` names.
2. Write no figure: no amount, percentage, count of days or count of units. The only digits
   allowed are in identifiers copied from `action.parameters`.
3. Return exactly this JSON, and nothing else: `{ "actionId": "<action.id>", "result": "<the
   sentence>" }`.
