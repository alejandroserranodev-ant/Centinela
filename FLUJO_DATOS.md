# The data flow as built

This page sits at the root, against the rule that a fact lives on the page of the level that owns
it, because the team keeps the file structure as it is. It covers one thing no level page holds:
the path one simulated day, one decision and one chat question take through the code, across `apps/api` and
`packages/agents`. The design they are built toward is the root's
[How the parts connect](./AGENTS.md#how-the-parts-connect). Each level page owns the rules of its own
steps.

## Signing in

1. `POST /auth/login` reaches `apps/api/src/centinela_api/routers/auth.py:login(credenciales)`, which
   checks the email and password against the hashed profiles of `CENTINELA_USUARIOS` through
   `apps/api/src/centinela_api/auth.py:verificar(correo, clave)` and answers a token that
   `apps/api/src/centinela_api/auth.py:emitir(persona, ahora)` signs, with the person.
2. Every other route depends on
   `apps/api/src/centinela_api/auth.py:persona_actual(authorization)`, which reads the bearer token
   through `apps/api/src/centinela_api/auth.py:leer(token, ahora)` and answers 401 when it is
   missing, forged or expired. `GET /auth/sesion` answers the person a token names, which is how
   the web restores a session on load.

## One simulated day

1. `POST /simulacion/avanzar` reaches
   `apps/api/src/centinela_api/routers/simulacion.py:avanzar(dias, persona, conn)`, which answers 409
   when the day would pass the last day with data. The day moves in its own
   transaction, through `apps/api/src/centinela_api/simulacion.py:avanzar(conn, dias)`, before
   anything detects.
2. Detection runs in the API's process.
   The router reads the settings first, with
   `apps/api/src/centinela_api/configuracion.py:leer(conn)`, together with every stored
   alert and its entity, `apps/api/src/centinela_api/alertas.py:anteriores(conn)`. `apps/api/src/centinela_api/configuracion.py:umbrales(ajustes)` turns
   them into the thresholds the day uses, which
   `apps/api/src/centinela_api/agentes.py:with_thresholds(ctx, umbrales)` lays over the context and
   `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.use_thresholds(thresholds)` hands to the orchestrator, so a change saved by
   `PUT /configuracion` reaches the next day and no earlier one.
   `apps/api/src/centinela_api/agentes.py:get_context()` builds the walk's context once per
   process: the tree from `packages/agents/arbol/base.yaml`, the thresholds of
   [`data/metricas.yaml`](./data/metricas.yaml), and the kernel's catalogue and reader, which
   `apps/api/src/centinela_api/agentes.py:get_kernel()` reaches through
   `packages/agents/centinela_agents/catalog.py:connect_kernel(env)` with the DSNs of the root `.env`.
   `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.run_day(ctx, day, earlier, watched, limit, cause_rejections, proposal_rejections)`
   returns the day's run, a generator the router drives through `asyncio.to_thread`, so the event
   loop keeps serving the stream. It hands the run every stored alert as an `Earlier`, through
   `apps/api/src/centinela_api/agentes.py:earlier_of(alerta, entidad)`, the metrics
   `apps/api/src/centinela_api/agentes.py:metricas_del_dia(ajustes)` names, those of `API_METRICS`,
   because the API's `Alert` model accepts no other, that the settings leave watched, and the cap
   `CENTINELA_ALERTAS_POR_DIA`. The run detects with
   `packages/agents/centinela_agents/walk.py:detect(ctx, day)`, drops what an earlier alert
   covers, orders the rest and runs each alert in series.
3. Each step the run yields reaches the stream as a `step` event, an `AgentStep`: the detection's,
   then each leaf's start and end. The orchestrator comes from
   `apps/api/src/centinela_api/agentes.py:get_orchestrator()`, which builds it once per process
   with the model provider, the kernel's call, the four action stubs, an in-memory checkpointer
   and the tracer. Each leaf reads `kpi_consultar` in code and records each query in the state's
   `queries`. The run passes each alert the earlier alerts in `propuesta` and the day's
   detections not yet run, for `Analista` to name one as the same cause. When an alert's graph
   pauses or ends, the run yields its result, and the router answers with the verdict of what it
   recorded before the next alert runs.
4. `apps/api/src/centinela_api/agentes.py:state_to_alert(alert_id, state, detection, day_str)`
   turns the graph's state into the API's `Alert`.
   `apps/api/src/centinela_api/ciclo_vida.py:recorrer(estados)` checks the statuses the graph took
   it through, which `apps/api/src/centinela_api/agentes.py:status_path(alert_id, state)` reads
   from its `transitions`: a path that does not start at `new` or skips a transition is refused,
   logged, and answered with a verdict that it was not recorded, which ends that alert. One
   transaction, in
   `apps/api/src/centinela_api/routers/simulacion.py:_registrar(conn, corrida, dia, day_str, nota)`, then stores it with
   `apps/api/src/centinela_api/alertas.py:guardar(conn, alerta)` and writes one `alert` row, actor `vigia`, with
   `apps/api/src/centinela_api/bitacora.py:registrar(conn, alerta_id, tipo, actor, detalle, dia_simulado, query_id, figures)`,
   under the KPI's `queryId` and with the title's figures, then stores the alert's entity and its
   `cost` and writes one `evidence` row per query in `queries`. An alert the graph ends `unida` is
   stored `merged` into the alert that remains while that one is still `proposed`; otherwise the
   verdict names the refused target and the run starts the alert again without it. A detection
   it absorbed is stored `merged` without running, as the lifecycle in
   [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#the-alert-lifecycle) states.
5. Each stored alert goes out as an `alert` event carrying the `Alert` with the signed-in person's
   `decidedBy` and `canDecide`, the one that remains after a merge and each alert merged into it
   included, so a screen shows the alert before the day ends.
   Another `step`, of `estratega`, reports the proposal, and the stream closes with `end`, which carries the
   simulated day and the ids of the new alerts. `apps/api/src/centinela_api/sse.py:flujo(eventos)`
   writes each event's name on its `event:` line.

A second `POST /simulacion/avanzar` while a day runs is answered 409 and starts nothing, because
the router holds one lock for the whole stream. An alert whose graph raises is yielded as failed,
streamed as a `step` saying its analysis did not finish, and the day goes on. An error before the loop, such as a
provider with no `LLM_MODEL`, is logged too, and the stream still ends with no new alerts.

## One decision

1. `POST /alertas/{id}/decision` reaches
   `apps/api/src/centinela_api/routers/alertas.py:decidir(id, decision, persona, conn)`, whose
   person `apps/api/src/centinela_api/auth.py:persona_actual(authorization)` reads from the
   bearer token. The alert is read, the person is checked by
   `apps/api/src/centinela_api/permisos.py:puede_decidir(conn, persona, alerta)`, which reads the owner from the settings, and
   `apps/api/src/centinela_api/decisiones.py:aplicar(alerta, decision, autonomia)` checks the
   decision against the autonomy the settings give each action type and returns the alert as `approved` or `rejected`, or still `proposed` with its changes requested, together with its log event.
   An approval, an edit or a request for changes whose graph no longer waits at the gate,
   `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.is_awaiting_decision(alert_id)`,
   is answered 409 and recorded nowhere; a rejection is recorded and resumes nothing.
2. One transaction re-reads the alert with a row lock, runs `aplicar` on it again, stores the alert
   and writes the `decision` row, whose actor is the signed-in person's name and role, and commits
   before anything resumes.
3. The graph resumes with
   `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.resume(alert_id, decision)`,
   in a worker thread. On an approval or an edit, a state that carries an `executed_action` turns
   the alert `executed` through
   `apps/api/src/centinela_api/ciclo_vida.py:transicionar(actual, siguiente)`, and a `result` row with actor `ejecutor` is written; a state without one
   writes a `result` row saying why the action did not run, and the alert stays `approved`. A rejection resumes
   the graph and writes nothing more. A request for changes resumes it through
   `apps/api/src/centinela_api/routers/alertas.py:_reproponer(conn, alerta, motivo, ajustes, dia)`:
   the orchestrator receives the reason as `request_changes`, `Estratega` proposes again, and the
   alert keeps its status with the new actions, a `proposal` row and the queries the proposal added;
   a resume that fails or returns no actions writes a `proposal` row saying what the person can
   still do.
4. A failed approval resume writes a `result` row of `ejecutor` saying the action did not run, and
   the alert stays `approved`. A failed rejection resume is logged.

## One chat question

1. `POST /chat` reaches
   `apps/api/src/centinela_api/routers/chat.py:chat(pregunta, quien, conn)`, whose person
   `quien` comes from the bearer token.
   The question's length is checked by its Pydantic model, the day is read, and an `alertId`, when sent,
   must name a stored alert. One transaction writes the `question` row under the signed-in person,
   with no alert when none was sent.
2. `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.ask(question, day, alert)`
   runs in a worker thread. It screens the question in code, then walks the chat graph from
   `conversar.raiz`: a flagged question ends there; otherwise the leaf `clasificar` names an
   intent, the tree routes it, and the leaf `responder` reads the KPI through `kpi_consultar`, the
   path of `detectar` for the entity's row, or the anchored alert's cause or actions, before the
   model writes.
3. The stream sends one `step` per node the walk took, then one `end` with the `ChatMessage`.
   One transaction records each query in `api.consultas` and as an `evidence` row, then the
   `answer` or `refusal` row with its figures, then one `costo` row per model step, which the log
   never serves. No alert changes.
4. A figure of the answer opens its source through `GET /consultas/{queryId}`,
   `apps/api/src/centinela_api/routers/consultas.py:obtener(query_id, conn)`.

## The inbox totals

`GET /bandeja/resumen` reaches `apps/api/src/centinela_api/routers/bandeja.py:totales(conn)`, which
answers `apps/api/src/centinela_api/resumen.py:calcular(conn)`: the totals over the proposed alerts
as `Figure`s, each with a query over the alerts table that `GET /consultas/{queryId}` answers like
any other.

## Where this departs from the design

- **The agents run in the API's process**, not behind the `/interno/*` endpoints. Nothing calls
  those endpoints.
- **The `bitácora` gets an `alert` row and its `evidence` rows per alert from a day**, not the
  proposal rows the design lists.
- **The chat is its own agent on its own root of the tree**, not `Analista` in a chat mode.
