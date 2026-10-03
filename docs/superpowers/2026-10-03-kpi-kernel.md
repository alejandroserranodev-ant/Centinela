# Spec 4 of 6: the KPI kernel

**Status:** executed; kept while specs 5 and 6 build on it. **Depends on:** spec 1, `normative-foundations`, for the KPI
description fields (ISO 22400-2), the role of `Vigía` as owner of measurement (ISO 9001 §9.1), the
law that no agent changes a database, and the stage at which each agent consults the kernel.

## Why

The metrics of `metricas.yaml` are hand-written SQL views. They answer the brief's scenarios, but a
client whose decisions need another measure has no way to get one, and a hand-written view is
exactly the unbounded, injection-prone artefact the team refuses to let a person or a model write
at runtime. The kernel is a **workbench with a closed language**: it builds every current metric
(spec 5) and every future one (spec 6) from the same primitives, compiles them to SQL in code,
refuses anything it cannot bound in cost or in time, and is the one place every agent reads a
business measure from.

## Decisions

- **The kernel is a closed definition language plus a compiler, not a query generator.** A KPI is
  a JSON document of a schema the kernel owns; the compiler turns it into SQL with `psycopg.sql`
  composition, never by string interpolation. No path, for a person or a model, takes free SQL.
  The reason: what cannot be written cannot be injected.
- **The language belongs to `data`; the compiler and its tools belong to `packages/tools`.** The
  definition of a metric is `data`'s, as every metric's is today; running SQL is `packages/tools`'s,
  and only `packages/tools` reaches the database.
- **A KPI is a function of the simulated day, never a view.** A view cannot take the day, and the
  clock section of `data/AGENTS.md` shows what that costs: views that compute "today" from
  `fecha_corte()`, views that return the whole year, and filters that still leak. Compiled SQL that
  takes `dia` and applies it to every date column is correct on any simulated day by construction.
- **Two kinds of KPI, two homes, and no agent writes either:**

  | Kind | Defined in | Reaches the database | Executed as |
  |---|---|---|---|
  | base | its entry of `metricas.yaml`, in a `kernel:` block | when a person sets the database up: the compiler writes `data/sql/05_kpis.generated.sql`, one function `centinela.k_<metric>(dia date)` per metric, applied after `04_vistas_causa.sql` | the function, by the read-only user |
  | approved | `apps/api`'s catalogue, by the flow of spec 6 | never: nothing is created at runtime | its frozen compiled SQL, stored with its hash at approval, run as stored text with `dia` as a parameter |

  The reason for the split: the base keeps the brief's semantic layer as SQL in the database,
  inspectable in pgAdmin and callable from an eval's `verificacion_sql`; the approved kind adapts
  at runtime without any DDL, so the law of spec 1 holds absolutely. **An approved KPI that proves
  its worth is promoted by a person**: a pull request moves its definition into `metricas.yaml`,
  regenerates the SQL file, and retires the approved entry.
- **What runs is what was approved.** An approved KPI stores its compiled SQL, its hash and the
  compiler version that produced it; the kernel runs the stored text and refuses it if the hash
  does not match. A change to the compiler never changes an approved KPI; it changes a base KPI
  only through the regenerated file, which a person reviews in the diff.
- **`metricas.yaml` stays the single definition of every base metric.** Each entry gains the
  `kernel:` block and the ISO 22400-2 fields it lacks: `unidad`, `rango`, `tendencia`
  (`mayor_es_mejor` or `menor_es_mejor`), `temporalidad`, `audiencia`. The existing `formula` stays
  as the readable formula ISO 22400-2 asks for; the `kernel:` block is the one that runs.
- **A KPI with no `fuente_umbral` is descriptive**: evidence for `Analista` and `Estratega`, and an
  operand no `detectar` node may compare, because `data/AGENTS.md` admits no threshold a document
  does not state.

## The language

A `kernel:` block holds one KPI. Every key comes from this closed list; any other key is refused.

| Key | Holds | Bound |
|---|---|---|
| `fuente` | one source from `data/kernel/fuentes.yaml` | a closed list |
| `unir` | names of joins declared in `fuentes.yaml`, each along a foreign key of `sql/01_esquema.sql` | at most three |
| `abierto_al_dia` | a pair of date columns, start and end (end nullable): the rows open on `dia`, as an open invoice is emitted on or before `dia` and unpaid on `dia` | one per KPI |
| `ventana` | a date column and a number of days back from `dia` | at most 365 days |
| `filtro` | a column, an operator from `=`, `!=`, `<`, `<=`, `>`, `>=`, `en`, and a literal | at most five; never on a column `fuentes.yaml` marks `fuga` |
| `agrupar` | dimensions the source declares | at most three |
| `medida` | `sum`, `avg`, `count`, `min`, `max`, `mediana` over a column or one arithmetic expression of `+ - * /` over columns | expression depth two |
| `razon` | a `medida` over another `medida` | one |
| `linea_base` | the same `medida` over the N previous periods of `dia`, `semana` or `mes`, and the output `delta` or `delta_pct` | N at most 12 |
| `salida` | the output columns, each named, and the entity column | the entity column is required |

**A source is a table of `sql/01_esquema.sql`, never a `v_*` view**, because several views compute
"today" from `fecha_corte()` and the kernel cannot hand them the simulated day.
`data/kernel/fuentes.yaml` declares each source: its table, its date columns, its entity keys, its
dimensions, its joins, the columns the kernel may read, and its columns marked `fuga` with the
reason. `ordenes_compra.estado` and `pedidos.estado` are marked `fuga`, because the clock section
of `data/AGENTS.md` says they hold the end of the dataset. A column holding a person's name, such as
`vendedores.nombre`, is not readable, because personal data is masked before an agent sees it. A
test checks every source and column of `fuentes.yaml` against `sql/01_esquema.sql`, so the list
cannot name what the schema does not hold.

## Database roles

| Role | Granted | Used by |
|---|---|---|
| the read-only user of `data/AGENTS.md` | `SELECT` on the `v_*` views and `EXECUTE` on `centinela.k_*` | the SQL tool and `kpi_consultar` for base KPIs |
| `centinela_kernel` | `SELECT` on the readable columns of `fuentes.yaml` only, granted column by column and generated from that file; no `INSERT`, `UPDATE`, `DELETE`, `CREATE` or `TRUNCATE` anywhere | `kpi_dry_run` and `kpi_consultar` for approved KPIs, always inside a read-only transaction |

The base functions are `SECURITY DEFINER`, owned by the role that sets the database up, with a
fixed `search_path`, so the read-only user runs them without reading a table; they are created by
a person running the setup, never at runtime. No role an agent's tools hold can change a database,
which is the gate that holds spec 1's law.

## Clock safety

The compiler applies `dia` to every date column the KPI reaches, through `ventana`,
`abierto_al_dia` or a plain `<= dia`, and refuses a KPI it cannot do that for. Two leaks the clock
section names are refused by construction: a weekly `linea_base` uses only weeks with
`semana + 6 <= dia`, and a payment joins only when `fecha_pago <= dia`.

## Cost guards

Settings of the kernel, sized to the machine as Ollama's model is; each refusal states which guard
refused.

| Guard | Checked |
|---|---|
| the bounds of the language table | at validation, before any SQL exists |
| the planner's estimated cost under a cap | `EXPLAIN` on the compiled SQL, at validation |
| a run under `statement_timeout` | at dry run and on every call |
| groups under a cardinality cap | at dry run |

## The tools

All four are read-only; the kernel has no action.

| Tool | Who calls it | Does |
|---|---|---|
| `kpi_validar` | `Vigía`'s `proponer_kpi` (spec 6), the generator of `05_kpis.generated.sql`, the tests | checks a block against the language, `fuentes.yaml`, the clock rules and the planner's cost; returns the compiled SQL |
| `kpi_dry_run` | `Vigía`'s `proponer_kpi`, the tests | runs compiled SQL as `centinela_kernel` in a read-only transaction on a simulated day, under the timeout; returns the first rows, the row count and the time |
| `kpi_consultar` | the tree's nodes in code (`detectar`, `ejecutar.vigente`), `Analista`, `calcular_impacto` | runs a KPI by id on `dia`: a base KPI through `centinela.k_<metric>(dia)`, an approved one through its stored SQL after checking its hash; returns the rows with the query, as the SQL tool does |
| `kpi_catalogo` | every agent the tree gives the SQL tool | lists the client's KPIs, base and approved, with their ISO 22400-2 fields and whether each is descriptive |

The model names a KPI by id and never passes its SQL: the orchestrator, which is code, hands the
client's approved KPIs (id, stored SQL, hash) to the kernel as context of the run, as
`apps/api` hands them to the orchestrator.

## Generated file

`data/sql/05_kpis.generated.sql` is written by the compiler from `metricas.yaml` and carries a
banner naming the command that writes it. It is never edited by hand; the defect is in the
`kernel:` block.

## Pages this spec changes

| Page | Change |
|---|---|
| `data/AGENTS.md`, "Why each file exists" | rows for `kernel/fuentes.yaml`, for the `kernel:` block of `metricas.yaml`, and for `sql/05_kpis.generated.sql` |
| `data/AGENTS.md`, "Rules of this level" | "A metric is a `v_*` view in `sql/03_capa_semantica.sql` or `sql/04_vistas_causa.sql` and an entry in `metricas.yaml`" becomes "A base metric is an entry in `metricas.yaml` whose `kernel:` block compiles to `centinela.k_<metric>(dia)` in `sql/05_kpis.generated.sql`; the `v_*` views are the kit's reference and the cause views. An approved metric lives in `apps/api`'s catalogue and never in this schema" |
| `data/AGENTS.md`, "Rules of this level" | "Tools connect as a read-only database user granted only the `v_*` views" gains "and `EXECUTE` on `centinela.k_*`"; a sentence names `centinela_kernel`, its column grants, and that no role a tool holds may write |
| `data/AGENTS.md`, "Setting up the database" | a step: `psql -d centinela -f sql/05_kpis.generated.sql`, and the grants of both roles |
| `data/AGENTS.md`, "The simulated clock" | a paragraph: a kernel KPI takes the simulated day as its argument, so the leaks this section lists do not reach it |
| `packages/tools/AGENTS.md`, "Decisions" | the kernel as Python functions behind a JSON Schema contract, not a server, its four read-only tools, and the sentence "The kernel has no action: a KPI becomes active by `apps/api`'s record of an approval, never by a change to a database" |
| `GENERATED.md`, "What writes today" | a row: the kernel's compiler writes `data/sql/05_kpis.generated.sql` from `data/metricas.yaml`; its name says so |
| `data/docker-compose.yml` | the role `centinela_kernel` and the setup step for `05_kpis.generated.sql` |
| `docs/guide/chapters/kpi-kernel.md` | the sections on the language, the kinds of KPI, the guards, the roles and the tools shrink to a link to the level page this spec writes them into; the diagrams stay in the chapter, each captioned `Draws:` with that page's new section, and the chapter's warning box drops what this spec implements |

## Acceptance

- `kpi_validar` refuses one planted violation per bound of the language table, per guard, and per
  clock rule, each with the guard named.
- No public function of the compiler accepts a string that reaches SQL other than through
  `psycopg.sql` composition.
- The read-only user cannot `SELECT` a table of `centinela` and can `EXECUTE` `centinela.k_*`.
- `centinela_kernel` cannot read a column absent from `fuentes.yaml`'s readable list, and every
  `INSERT`, `UPDATE`, `DELETE` or `CREATE` it attempts fails.
- `kpi_consultar` refuses an approved KPI whose stored SQL does not match its hash.

## Amendments made while planning

Each item supersedes the line of this spec it names; the plan builds the amended version.

- **Scope is infrastructure only.** The plan builds the language, `fuentes.yaml`, the compiler, the guards, the roles, the generator, the four tools and their JSON Schema contract, and tests them with fixture blocks in `packages/tools/tests/fixtures/metricas.yaml`. No entry of `data/metricas.yaml` gains a `kernel:` block, because the table's metrics need primitives the language lacks: conditional sums (`saldo_vencido`), lag (`variacion_costo_pct`, `veces_intervalo_habitual`), `CASE` (`dias_retraso`) and a column-to-column comparison (`descuento_en_exceso`). Spec 5 adds each with its bound. The `DOUBTS.md` debt stays filed and says that `kpi_catalogo` exists and serves no base metric yet.
- **Each date column has a role in `fuentes.yaml`**, because applying `dia` to every date column breaks `fecha_vencimiento` and `fecha_esperada`, which are future by nature. `evento`: the row exists from that day, and the compiler adds `<= dia`. `plazo`: a promised date, read as is. `cierre`: an event that closes the row, such as `fecha_recibida`, read as `CASE WHEN c <= dia THEN c END`. `ventana`, `linea_base` and `abierto_al_dia.desde` take only an `evento` date; `agrupar ... por` takes an `evento` or a `plazo` date.
- **Only many-to-one joins.** A join reaches the whole primary key of its target along a `REFERENCES` of `01_esquema.sql`, or the PK of a `ref_*` table (`ref_topes_descuento` by `segmento`, `ref_margen_minimo_linea` by `linea`), which have no FK. Joins are `LEFT JOIN`, so a null FK (`clientes.vendedor_id`) never drops a row. A child table, such as `pagos` of an invoice, reaches a KPI only as a closing (`cierres:` of the source), and only inside `abierto_al_dia.hasta`, compiled to `NOT EXISTS (... fecha_pago <= dia)`. That is the spec's "a payment joins only when `fecha_pago <= dia`". The data holds one full payment per invoice, so "open" means no payment up to `dia`.
- **A source with no date of its own names the join that dates it.** `pedidos_detalle` declares `fechada_por: pedidos`, and a KPI over it without `unir: [pedidos]` is refused by `reloj`. The join's bound goes in `WHERE`, so its `LEFT JOIN` behaves as an inner one.
- **`pedidos.estado` is `fuga` except for values known when the row is created.** The generator decides `Cancelado` at creation (4% at random, never invoiced), and only `Pendiente de despacho` holds the end of the dataset. `fuga: {estado: {razon, conocidos_al_crear: [Cancelado]}}` admits `=`, `!=` or `en` on those values in a `filtro` and nothing else. `ordenes_compra.estado` has no known value, so no filter reads it. Without this, spec 5's parity with `v_ventas` breaks on every sales metric.
- **The base functions, and `fecha_corte()`, belong to `centinela_propietario`**, a `NOLOGIN` role that holds the same column-by-column `SELECT` grants as `centinela_kernel`, because an owner can drop or alter its functions and `centinela_kernel` is a login role a tool uses. They are `SECURITY DEFINER` with `SET search_path = pg_catalog, pg_temp` and fully qualified names, so a base KPI reads only the readable columns too. The setup superuser creates them and changes their owner with `ALTER FUNCTION ... OWNER TO`, which needs no `CREATE` for the owner role. `EXECUTE` is revoked from `PUBLIC` and granted to `centinela_lector`.
- **The read-only user is `centinela_lector`**, because `data/AGENTS.md` named no role and none existed. Both roles are `LOGIN` with the password equal to the name, the posture of the compose's `centinela/centinela` for the local dataset, and are created in an idempotent `DO` block.
- **`fecha_corte()` becomes `SECURITY DEFINER`, owned by `centinela_propietario`**, in `05`, because a view's function runs with the caller's privileges and `centinela_lector` reading `v_cartera_cliente` would fail on `inventario_diario`. The kit file `03` is not touched.
- **`05_kpis.generated.sql` holds the roles, the grants and the functions**, one file written by one command from `fuentes.yaml`, `metricas.yaml` and the view names of `03` and `04`, because the function needs the role and its grants first and the spec names one setup step. A test compares the committed file with what the generator writes.
- **The entity of a KPI is its `agrupar`** (one to three items). `salida` names only `valor`, plus `base` and `delta` with a `linea_base`, so one row per entity holds by construction. `dia` and `periodo` are reserved names.
- **One time frame per KPI**: at most one of `ventana`, `abierto_al_dia` and `linea_base`. With none, the compiler bounds every event date by `<= dia`. `linea_base` measures the last complete period before `dia` (for a week, the Monday `s` with `s + 6 <= dia`; for a month, the one whose last day is `<= dia`) and compares it against the mean of the N before it.
- **Language bounds the spec leaves open**: an `en` list of at most 20 literals; no `%` in a text literal, because psycopg would read it as a placeholder in an approved KPI's stored text; a literal of the column's type; text of at most 200 characters.
- **ISO 22400-2 fields**: `unidad` (text), `rango` (`{min, max}`, each a number or `null`), `tendencia` (`mayor_es_mejor` or `menor_es_mejor`), `temporalidad` (`diaria`, `semanal` or `mensual`) and `audiencia` (one or more of `operacion`, `supervision`, `gerencia`). They are required only on an entry that carries `kernel:`, and are defined in `$defs/ficha` of the same schema.
- **`kpi_validar` takes `dia`**, because `EXPLAIN` with a null day folds the plan to nothing. The generator explains each base KPI on `centinela.fecha_corte()` and needs `CENTINELA_DSN` only when an entry carries `kernel:`.
- **The tools receive a block, never SQL.** `kpi_dry_run` compiles the block it receives and `kpi_consultar` receives an id. The approved KPIs reach the kernel as a JSON file named by `CENTINELA_KPIS_APROBADOS`, which the orchestrator writes for the run; that is code, as the spec asks. The kernel is Python functions, `centinela_tools/kernel.py:Kernel.call(name, arguments)`, which checks the arguments against each tool's JSON Schema in `CONTRACT`; code calls it in its own process and a model reaches it through native function calling, and which agent is given which tool stays undecided in `packages/agents`.
- **Guard settings come from environment variables**, with defaults sized in the plan: `CENTINELA_KERNEL_COSTO_MAX`, `CENTINELA_KERNEL_TIMEOUT_MS`, `CENTINELA_KERNEL_GRUPOS_MAX` and `CENTINELA_KERNEL_MUESTRA`.
