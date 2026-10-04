# The HTTP contract's JSON schema

This page holds the conventions that shape the JSON `apps/api` serves and the OpenAPI schema
FastAPI derives from it. They belong to [`apps/api/AGENTS.md`](./apps/api/AGENTS.md); the page sits at
the root, and not on that level, because the team keeps the tree's file structure as it is.
What each endpoint serves and refuses is the endpoint table of that page.

## The conventions

- **Every model extends `Esquema`** in
  [`apps/api/src/centinela_api/modelos.py`](./apps/api/src/centinela_api/modelos.py), whose
  config sets `alias_generator=to_camel`, `populate_by_name=True` and `extra="forbid"`. The
  Python fields are snake_case and the JSON is camelCase (`pesos_at_risk` travels as
  `pesosAtRisk`), so `apps/web/src/api/types.ts` mirrors the JSON field for field without a
  reshape. A request with a key the model does not declare is refused with 422; the snake_case
  name is accepted too, but the contract is the camelCase one.
- **Unions are discriminated by `kind`**: `Cause` (`identified`, `no_evidence`), `Actor` (`agent`,
  `person`) and `Decision` (`approve`, `edit`, `reject`), so the schema names which variant each
  body is.
- **Statuses are English inside and Spanish at the edge.** The `status` field speaks
  `AlertStatus`; the query parameter `estado` of `GET /alertas` speaks `AlertEstadoEnum`, the
  brief's Spanish names, which `apps/api/src/centinela_api/ciclo_vida.py:ESTADO_A_STATUS` maps. An
  unknown `estado` is refused by the enum's validation with FastAPI's own 422 body.
- **Every field carries a `Field(description=...)`**, and some carry an `example`, so the schema
  explains itself. Pydantic warns that `example` as a keyword is deprecated in favour of
  `json_schema_extra`.
- **Every JSON route declares its `response_model`**, so the schema names its response. The SSE
  routes (`/simulacion/avanzar`, `/chat`) return a `StreamingResponse` and declare none; the
  models of their events are `AgentStep` and `ChatMessage`, except the `end` event of
  `avanzar`, a plain dictionary the schema does not describe.
- **Query parameters carry a description**, and the endpoint's docstring is its description in
  the schema.
- **Routers are tagged** where the schema groups them: `alerts` for `/alertas` and `internal` for
  `/interno`. The other routers carry no tag.

## Reading the schema

While uvicorn runs (the commands are on [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#commands)),
Swagger UI is served at `/docs` and the raw schema at `/openapi.json`.

## Adding to the contract

1. Write the model in `apps/api/src/centinela_api/modelos.py`, extending `Esquema`, with a
   description on every field.
2. Use a `Literal` or an `Enum` for a closed set of values, so the schema lists them.
3. Set `response_model` on the route, and a description on each query parameter.
4. Mirror the camelCase JSON in `apps/web/src/api/types.ts`.
