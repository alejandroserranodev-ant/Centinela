# The data flow as built

This page sits at the root, against the rule that a fact lives on the page of the level that owns
it, because the team keeps the file structure as it is. It covers one thing no level page holds:
the path one simulated day and one decision take through the code, across `apps/api` and
`packages/agents`. The design they are built toward is the root's
[How the parts connect](./AGENTS.md#how-the-parts-connect). Each level page owns the rules of its own
steps.

## One simulated day

1. `POST /simulacion/avanzar` reaches
   `apps/api/src/centinela_api/routers/simulacion.py:avanzar(dias, conn)`. The day moves in its own
   transaction, through `apps/api/src/centinela_api/simulacion.py:avanzar(conn, dias)`, before
   anything detects.
2. Detection runs in the API's process.
   `apps/api/src/centinela_api/agentes.py:get_context()` builds the walk's context once per
   process: the tree from `packages/agents/arbol/base.yaml`, the thresholds of
   [`data/metricas.yaml`](./data/metricas.yaml), and the kernel's catalogue and reader, which
   `apps/api/src/centinela_api/agentes.py:get_kernel()` reaches through
   `packages/agents/centinela_agents/catalog.py:connect_kernel(env)` with the DSNs of the root `.env`.
   `packages/agents/centinela_agents/walk.py:detect(ctx, day)` walks the detection nodes over the
   rows `kpi_consultar` returns for the simulated day.
   `apps/api/src/centinela_api/agentes.py:prioritized(detections, known)` keeps the detections
   whose metric is in `API_METRICS`, because the API's `Alert` model accepts no other, drops those
   whose alert already exists, and keeps the `CENTINELA_ALERTAS_POR_DIA` with the most `pesos_en_riesgo`.
3. For each detection the stream sends a `step` event, an `AgentStep` of `vigia`. Then
   `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.start(detection, alert_id, day, earlier_alerts, cause_rejections, proposal_rejections)`
   runs the graph in a worker thread, through `asyncio.to_thread`, so the event loop keeps
   serving the stream. It runs until the approval interrupt or an end. The orchestrator comes from
   `apps/api/src/centinela_api/agentes.py:get_orchestrator()`, which builds it once per process
   with the model provider, the kernel's call, the four action stubs and an in-memory checkpointer.
   Each leaf reads `kpi_consultar` in code and records each query in the state's `queries`. The
   router passes no earlier alerts and no rejection reasons.
4. `apps/api/src/centinela_api/agentes.py:state_to_alert(alert_id, state, detection, day_str)`
   turns the graph's state into the API's `Alert`.
   `apps/api/src/centinela_api/ciclo_vida.py:recorrer(estados)` checks the statuses the graph took
   it through, which `apps/api/src/centinela_api/agentes.py:status_path(alert_id, state)` reads
   from its `transitions`: a path that does not start at `new` or skips a transition is refused,
   and the alert is logged and skipped. One transaction then stores it with
   `apps/api/src/centinela_api/alertas.py:guardar(conn, alerta)` and writes one `alert` row, actor `vigia`, with
   `apps/api/src/centinela_api/bitacora.py:registrar(conn, alerta_id, tipo, actor, detalle, dia_simulado, query_id)`,
   under the KPI's `queryId`, then one `evidence` row per query in `queries`, its SQL as the detail.
5. Another `step`, of `estratega`, reports the proposal, and the stream closes with `end`, which carries the
   simulated day and the ids of the new alerts. `apps/api/src/centinela_api/sse.py:flujo(eventos)`
   writes each event's name on its `event:` line.

An error in one detection is logged and skips that alert. An error before the loop, such as a
provider with no `LLM_MODEL`, is logged too, and the stream still ends with no new alerts.

## One decision

1. `POST /alertas/{id}/decision` reaches
   `apps/api/src/centinela_api/routers/alertas.py:decidir(id, decision, x_user_name, x_user_role, conn)`.
   The role is checked against `ROLES_CON_DECISION`, and
   `apps/api/src/centinela_api/decisiones.py:aplicar(alerta, decision)` checks the decision and
   returns the alert as `approved` or `rejected`, together with its log event.
2. One transaction stores the alert and writes the `decision` row, whose actor is the person named
   by the headers.
3. The graph resumes with
   `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.resume(alert_id, decision)`,
   in a worker thread. On an approval or an edit, a state that carries an `executed_action` turns
   the alert `executed` through
   `apps/api/src/centinela_api/ciclo_vida.py:transicionar(actual, siguiente)`, and a `result` row with actor `ejecutor` is written. A rejection resumes
   the graph and writes nothing more.
4. A failed approval resume writes a `result` row of `ejecutor` saying the action did not run. That
   includes the state the in-memory checkpointer loses when the process restarts, so the alert
   stays `approved`. A failed rejection resume is logged.

## Where this departs from the design

- **The agents run in the API's process**, not behind the `/interno/*` endpoints. Nothing calls
  those endpoints.
- **The `bitácora` gets an `alert` row and its `evidence` rows per alert from a day**, not the
  proposal rows the design lists.
