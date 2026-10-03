# Current KPIs in the kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild every metric of `data/metricas.yaml` as a base KPI of the kernel, `centinela.k_<metric>(dia)`, prove each one agrees with its kit view on `fecha_corte()` and with a hand-written as-of query on earlier simulated days, and make the decision tree read the catalogue the kernel serves.

**Architecture:** The kernel's closed language grows by the primitives the current metrics need (conditional measures, the last value by date, column-to-column conditions, more output columns, a taken KPI, derived columns, rounding, a row filter on outputs). Each grows the JSON Schema in `data/kernel/lenguaje.schema.json` and the compiler in `packages/tools/centinela_tools/compiler.py`, which now wraps every KPI in an outer `nucleo` layer where derived columns, rounding and the row filter apply. Each entry of `metricas.yaml` gains a `kernel:` block and the ISO 22400-2 fields, the generator writes ten `k_` functions into `data/sql/05_kpis.generated.sql`, a `db` test checks parity in two halves, and `packages/agents` builds its catalogue and its reader from the kernel's tools.

**Tech Stack:** Python ≥ 3.12, uv, psycopg ≥ 3.2 (`psycopg.sql` composition), jsonschema ≥ 4.23 (Draft 2020-12), PyYAML, pytest, LangGraph (unchanged). PostgreSQL 16 in the disposable container `centinela-kernel-test` for the `db` tests.

**Spec:** `docs/superpowers/2026-10-03-current-kpis-in-kernel.md`. Read it whole, with the section "Amendments made while planning" that Task 1 adds. It builds on spec 4, `docs/superpowers/2026-10-03-kpi-kernel.md`: read its "The language", "Clock safety" and "Amendments made while planning". The language as it stands is `data/AGENTS.md` § "The kernel's language", and the kernel's tools are `packages/tools/AGENTS.md` § "The KPI kernel".

## Global Constraints

- Code is English. The words the data and the specs name keep their Spanish: every YAML and JSON key of the language (`fuente`, `unir`, `abierto_al_dia`, `ventana`, `filtro`, `agrupar`, `medida`, `razon`, `linea_base`, `salida`, and the new `columnas`, `tomar`, `derivadas`, `decimales`, `tener`, `si`, `contra`, `menos_dias`, `menos_meses`, `por`, `ultimo`, `anterior`, `caida`, `mayor`, `menor`, `dias_habiles`, `compara`, `existe`, `participacion`, `periodo_anterior`, `cuando`, `entonces`, `sino`, `umbral`), the guard names, the tool names and the ISO 22400-2 fields.
- The guards stay a closed list, `refusal.GUARDS = ("lenguaje", "fuente", "reloj", "costo", "tiempo", "cardinalidad", "hash", "catalogo")`. Every refusal raises `Refused(guard, detail)` with an English detail. No new guard is added.
- **No fragment of SQL is built from a string at runtime.** Every `sql.SQL(...)` in `centinela_tools/` takes one string constant; identifiers come only from `fuentes.yaml` or the block through `sql.Identifier`, values only through `sql.Literal` or `sql.Placeholder`. `tests/test_compiler.py:test_every_sql_fragment_of_the_package_is_a_constant` holds this.
- **No metric of `metricas.yaml` is dropped or renamed**, and no existing key of an entry is renamed or removed; the only existing value that changes is `dias_pago_prom`'s `descripcion` (decision 15). The list is `grep -oP '^  \K[a-z_]+(?=:)' data/metricas.yaml`.
- **No test, comment or page names an entity a seeded scenario affects, or says when one happens**, because `data/AGENTS.md` § "The scenarios" keeps them out of the tree on purpose. A test compares the kernel with a view or a query for every row; it never asserts which SKU, customer or seller breaks a rule.
- **A failing parity test is fixed in the `kernel:` block or in the compiler, never by loosening its assertion or its query.** The as-of queries are the reference; each was checked against its view on `fecha_corte()` while this plan was written, except `dias_pago_prom`'s, which measures by month of payment and has no view that does (decision 14).
- `data/csv/` and `data/sql/01` to `04` are not touched. `data/sql/05_kpis.generated.sql` is never edited by hand; it is written by `uv run python -m centinela_tools.generate` and committed.
- The `db` tests use only the disposable container `centinela-kernel-test` on port 55432, never the compose's volume. `packages/tools/AGENTS.md` § "Commands" starts it.
- **Hand-written source carries no comments**, except one header of at most ten lines on a test file.
- Documentation is English, present tense, and states each fact on one page. **No permanent page cites a spec or a plan.** No literal count of anything that grows. Prose cites code as `path/to/file.py:member(parameters)`.
- Commit messages are short sentences that carry the reason, written through `git commit -q -F - <<'MSG'`, and end with the `Co-Authored-By:` and `Claude-Session:` lines of the session. **No commit is made without asking the user first.** Nothing merges to `main`; the branch is `feat/current-kpis-refactor`.
- A link inside text this plan quotes for another page is written `](<path>)`, relative to that page, so the link check of `CLAUDE.md` skips it here. Drop the angle brackets when pasting.
- Python commands run with `uv` from the package directory they name. If `uv` is not on `PATH`, it is `~/.local/bin/uv`.

## Decisions taken while planning

Task 1 writes each into the spec's section "Amendments made while planning", and Task 5 writes each onto the page that owns it.

1. **The language grows by these primitives, each with its bound.** Every one was needed by at least one metric; none takes free SQL.
   - `medida.si`: up to three conditions of the `filtro` form that only this measure applies, compiled to `FILTER (WHERE ...)`. A `sum` with `si` over no row is 0, as an empty period of a baseline is for `sum` and `count`, so `saldo_vencido` is 0, not null, for a customer whose open invoices are not yet due, which is the view's value.
   - `ultimo` and `anterior`: the value at the latest, or the one before it, ordered by `por`, an `evento` date. `variacion_costo_pct` needs the cost in force and the one before it; `cobertura_dias` needs the stock on the last day of its window; the price in force is `ultimo` over `lista_precios`.
   - Expression operands: a number and `dia`, besides a column, at depth three (it was two). `max_dias_vencido` is `dia - fecha_vencimiento`; `margen_pct` is `(valor_neto - cantidad * costo_unitario) * 100` over `valor_neto`.
   - `filtro` and `si` take `contra` in place of `valor`: another column or `dia`, less `menos_dias` (at most 365) or `menos_meses` (at most 12) when it is a date, never both, and never with `en`. `descuento_en_exceso` compares `descuento_pct` with the segment's cap; the six months before a customer's last purchase are `fecha > ultima_compra - 6 months`.
   - `columnas`: up to eight more named measures over the same rows. With a `linea_base`, each is measured on the last complete period, as `valor` is.
   - `tomar`: up to two other KPIs, each written inline as a block and joined many-to-one on its whole entity (`por` maps each entity column to a column of this KPI), compiled on the same `dia`, read as `<name>.<column>`. A taken KPI takes at most one more level. This is the "join" that brings a price in force, the pending orders, a customer's open balance or units sold into a KPI over another table, and it keeps the clock, because the taken KPI is compiled by the same rules. It is inline, not named by id, so a block stays self-contained and an approved KPI can take one with no base KPI behind it.
   - `derivadas`: up to six named expressions computed after the measures, over the output columns before them, four operations deep: `+ - * /`, `mayor` and `menor` of two, `dias_habiles` (Monday to Friday after `desde` up to `hasta`), `compara`, `existe`, `si` with `cuando`, `entonces` and `sino`, `participacion` (the percent of a column's total over every row), and `periodo_anterior` (a column of the same entity one period before, which needs exactly one `{columna, por}` in `agrupar`). Operands are columns, numbers, `dia` and `{umbral: <column>}`, read from the entry's own `umbrales`, so a `pesos_en_riesgo` that needs the class minimum coverage reads the one place it is written.
   - `decimales`: the decimals (0 to 4) of an output column, rounded only on the way out, so a derived column reads the unrounded value, as the kit's views do.
   - `tener`: up to three conditions `{columna, op, valor}` on output columns, the only rows the KPI returns. `margen_bruto_negativo` is the lines below cost, by its own definition.
   - `linea_base.salida` gains `caida`, the base minus the value, because `margen_pct`'s threshold is a drop in points.

   How the spec's expected cases resolved: `margen_pct` needed `caida`, `columnas` and the join to `ref_margen_minimo_linea`, which `fuentes.yaml` already declares. "No price change within 10 business days" is `dias_habiles` over a taken KPI of `lista_precios`. "Two consecutive weeks of the same seller" is `periodo_anterior`. `veces_intervalo_habitual` needs no lag: the mean of the gaps between consecutive orders is `(last - first) / (n - 1)`.
2. **The compiler wraps every KPI in an outer `nucleo` layer**, where `derivadas`, `decimales` and `tener` apply, and raises `COMPILER_VERSION` to `"2"`, because the compiled text of every KPI changes. No approved KPI exists yet, so none is affected.
3. **The generator writes `DROP FUNCTION IF EXISTS` before each `CREATE FUNCTION`**, because `CREATE OR REPLACE FUNCTION` cannot change the columns a function returns, and a KPI that gains a column must still re-apply over a database that holds its earlier shape. The grants that follow are written again after the drop.
4. **Each KPI outputs what is read from it, not every column of its view**: its entity; the columns the tree reads (`grep -o 'kpi\.[a-z0-9_]*\.[a-z0-9_]*' packages/agents/arbol/base.yaml | sort -u`); the columns its `umbrales` names; `pesos_en_riesgo`; the columns `calcular_impacto` reads; and the view's own columns that parity compares. `Analista` still reads the views. The entity of `margen_pct` is `linea` and of `dias_pago_prom` is `cliente_id`, because the period is the baseline's current one; every other entity is its view's.
5. **`cobertura_dias.pedidos_pendientes` counts the orders that hold the SKU, placed by `dia`, not cancelled and not invoiced by `dia`, across both warehouses.** An order is invoiced on its day or the next, and a pending order at the end of the dataset has no invoice, so "not invoiced by `dia`" is pending dispatch. It is a closing, `facturada`, on the source `pedidos_detalle`, matched on `pedido_id`, which `pedidos_detalle` shares with `facturas` through `pedidos`; `tests/test_sources.py` admits a closing whose child references the table that dates the source. It is per SKU, not per warehouse, because the map from a city to its warehouse is written only in `v_cobertura_inventario`'s text, in no table.
6. **`calcular_impacto`'s figures are KPI columns, and it reads no view.** `traslado_costo` reads `costo_unitario`, `costo_anterior`, `precio_lista` and `unidades_mes_prom` of `variacion_costo_pct`; `precio_a_margen_minimo` reads `ventas_mes_prom` of `margen_pct`, each `_mes_prom` the last 90 days over 3, the mean of a month over the last three. `compra_recuperada` is `veces_intervalo_habitual`'s `pesos_en_riesgo`. `venta_bajo_costo` reads `margen_bruto_negativo`'s `fecha` and `sku`. This supersedes the spec's "plus `v_precio_sku` and `v_costo_sku` where it needs a price or a cost in force": those views compute `vigente` from `fecha_corte()`, so on an earlier day they name the price of the year's end. `variacion_costo_pct` takes the price in force on `dia` as an `ultimo` in its `tomar: precio`, and `cobertura_dias` already outputs `precio_lista`, so every price and cost a formula needs is a KPI column on `dia`.
7. **Parity compares a view's own columns, and three comparisons depart.** On `fecha_corte()` each KPI's rows equal its view's rows on the columns the view holds; the columns no view holds (`pesos_en_riesgo`, bases, derived columns) are checked by the as-of query. `descuento_en_exceso` agrees with its view within half a peso per line, because the kit rounds each line and the kernel rounds the week. `margen_pct` and `dias_pago_prom` are compared on the entities measured in the current period, because a view has no row for a week or month with no sale or payment, while the kernel frames every entity of its baseline window. `dias_pago_prom` has no view half at all: it measures by month of payment (decision 14), and its view by month of invoice, so only its as-of query checks it.
8. **The as-of days are 2025-12-15, 2026-04-08 and 2026-09-15**, spread over the period, and every KPI returns rows on at least one of them. A day on which a KPI returns no row proves nothing about it, so `test_every_kpi_returns_rows_on_some_as_of_day` fails when a KPI returns none on all three, as it would on a dataset of another seed.
9. **The tree's tests validate the base against the catalogue the kernel serves.** `packages/tools` becomes a development dependency of `packages/agents`, which the chain `packages/agents` → `packages/tools` allows. `centinela_agents/catalog.py:catalog_from_kernel(kpis)` builds the catalogue from `kpi_catalogo`'s answer, and `centinela_agents/catalog.py:kernel_reader(call)` builds the reader from `kpi_consultar`, raising on a refusal. The tests' hand-written `VIEW_CATALOG` is replaced by `KERNEL_CATALOG`, and the `DOUBTS.md` debt "The base tree reads KPI columns no kernel builds" is paid and deleted: the startup check it names belongs to `apps/api`, which holds no code yet.
10. **No `VIG-` case exists in the tree**: `evals/` holds only the template. The spec's acceptance "the `VIG-` cases pass with `Vigía` reading the kernel" is checked as far as code exists: the base validates against the kernel's catalogue and the walk of `detectar` runs on it (`packages/agents` tests). `evals/AGENTS.md` keeps saying the `VIG-` cases run unchanged.
11. **The ISO 22400-2 fields follow written rules, and a person reviews them in Task 2's diff**: `unidad` is `%`, `COP`, `días` or `veces`; `rango` bounds what the measure can take, so `margen_bruto_negativo`, which returns only lines below cost, has `max: 0`; `tendencia` follows the threshold's direction; `temporalidad` is `semanal` for `margen_pct` and `descuento_en_exceso`, `mensual` for `dias_pago_prom` and `diaria` otherwise. `audiencia` is derived from every `owner` the two tables of `packages/agents/skills/estratega/acciones.md` name for the metric: `operacion` is who executes (`Compras`, `Analista de cartera`, a `vendedor_id`), `supervision` who supervises (`Jefe de cartera`, `Control Comercial`, `Comercial`), and `gerencia` `Dirección Financiera` and `Gerencia Comercial`. `data/AGENTS.md` states the rule.
12. **The second line of `metricas.yaml`'s header says `Vigía` reads the metrics through the kernel and `Analista` also through the views**, because it said "through the views", which stops being true for detection, and "through the kernel" alone would be false for `Analista`.
13. **`descuento_en_exceso` and `margen_bruto_negativo` return the whole history up to `dia`**, as their views do, with no `ventana`. Parity compares them with the whole view, and the tree's rule of one alert per metric and entity keeps an old week or line from alerting twice; `calcular_impacto` applies its four weeks when it reads the rows. A clock that starts late raises the history at once, which a person sees on the first day run.
14. **`dias_pago_prom` measures by month of payment**: the mean days from invoice to payment of the payments made in the last complete month, against the mean of the 12 months before (`linea_base.columna: pagos.fecha_pago`). The view groups by month of invoice, whose last months hold only the invoices already paid: on `fecha_corte()` it measures 37 of the 406 customers invoiced in September, at 23.9 days against a mean near 42, so a slow payer never reaches the threshold of `FIN-POL-004` §5 and one who stops paying has no row. By month of payment it measures 408, at 42.8. A customer who pays nothing still has no row; `saldo_vencido` covers that case. The departure from the view is decision 7's third.
15. **`dias_pago_prom`'s `descripcion` becomes "Días promedio entre factura y pago, por mes de pago"**, because `kpi_catalogo` serves it as the KPI's card and "por mes de factura" would contradict decision 14. The key is unchanged.

## Review Focus

1. **A simulated day before the dataset starts.** Expected: every KPI returns no rows and raises nothing, including the baselines and the taken KPIs. Task 3 pins it with `test_a_day_before_the_dataset_returns_no_rows`.
2. **A customer with a single order.** Expected: `intervalo_prom_dias` and `veces_intervalo_habitual` are null, with no division error, so no `detectar` node fires on them. Task 3 pins it with `test_a_customer_with_one_order_has_no_interval_and_raises_nothing`.
3. **The tenth and the eleventh business day after a cost change, and a weekend.** Expected: Friday to the Friday two weeks later counts 10, to the Monday after counts 11, a Saturday to a Sunday counts 0, so the threshold `> 10` fires on the eleventh business day. Task 3 pins it with `test_business_days_count_monday_to_friday_after_the_start`.
4. **Re-applying `05` over a database that holds an earlier `k_` function with other columns.** Expected: the setup applies, because each function is dropped before it is created. Task 2 pins the drop with `test_a_function_reads_its_argument_and_belongs_to_the_owner_role`, and every `db` session re-applies the file over the previous one.
5. **A refused reading reaching the tree.** Expected: the reader raises with the guard, never returns an empty list that reads as "no alert". Task 4 pins it with `test_a_refusal_of_the_kernel_raises_instead_of_reading_as_no_rows`.
6. **A month whose invoices are mostly unpaid when it ends.** Expected: `dias_pago_prom` measures the payments made in that month, whatever month they invoice, so a payment that arrives late counts in the month it arrives. Task 3 pins it with `test_a_kpi_agrees_with_an_as_of_query_on_an_earlier_day[...-dias_pago_prom]`, whose query groups by `date_trunc('month', pg.fecha_pago)`.
7. **A KPI that returns no row on any as-of day.** Expected: the suite fails, naming the KPI, instead of passing three empty comparisons. Task 3 pins it with `test_every_kpi_returns_rows_on_some_as_of_day`.

## File structure

| Path | Responsibility | Task |
|---|---|---|
| `docs/superpowers/2026-10-03-current-kpis-in-kernel.md` | the spec, renamed, with its amendments | 1 |
| `data/kernel/lenguaje.schema.json` | the language with its new primitives | 2 |
| `data/kernel/fuentes.yaml` | the closing `facturada` of `pedidos_detalle` | 2 |
| `data/metricas.yaml` | a `kernel:` block and the ISO 22400-2 fields on every entry | 2 |
| `data/sql/05_kpis.generated.sql` | regenerated: ten `k_` functions | 2 |
| `packages/tools/centinela_tools/compiler.py` | the new primitives, the `nucleo` layer, `thresholds`, the drop before create | 2 |
| `packages/tools/centinela_tools/tools.py`, `generate.py` | hand each entry's `umbrales` to the compiler | 2 |
| `packages/tools/tests/test_primitives.py` | one refusal per new bound and the SQL of each primitive | 2 |
| `packages/tools/tests/test_language.py`, `test_compiler.py`, `test_sources.py`, `test_generate.py` | adjusted to depth three, version 2, the closing, the drop | 2 |
| `packages/tools/tests/conftest.py` | applies the real KPIs with the fixture ones | 3 |
| `packages/tools/tests/test_parity.py` | the `KER-` cases: parity on `fecha_corte()`, as-of on three days, the review-focus cases | 3 |
| `packages/agents/centinela_agents/catalog.py` | `catalog_from_kernel`, `kernel_reader` | 4 |
| `packages/agents/pyproject.toml`, `packages/agents/uv.lock` | `centinela-tools` as a development dependency | 4 |
| `packages/agents/tests/support.py`, `packages/agents/tests/*.py` | `KERNEL_CATALOG` in place of `VIEW_CATALOG` | 4 |
| `packages/agents/tests/test_kernel.py` | the two kernel inputs of the tree | 4 |
| `DOUBTS.md` | the paid debt deleted | 4 |
| `data/AGENTS.md`, `packages/tools/AGENTS.md`, `packages/agents/AGENTS.md`, `packages/agents/skills/vigia/contrato.md`, `evals/AGENTS.md` | the level pages | 5 |
| `docs/guide/chapters/kpi-kernel.md`, `docs/guide/chapters/status.md` | the guide | 6 |

---

### Task 1: Rename the spec now that its plan exists, and write the amendments into it

**Files:**
- Rename: `docs/superpowers/2026-10-03-current-kpis-in-kernel-pending-5.md` → `docs/superpowers/2026-10-03-current-kpis-in-kernel.md`
- Create: `docs/superpowers/2026-10-03-current-kpis-in-kernel-plan.md` (this plan)

**Interfaces:**
- Consumes: none.
- Produces: the spec at the path this plan's header names, with the section "Amendments made while planning".

- [ ] **Step 1: Find every citation of the old path**

Run: `grep -rn "current-kpis-in-kernel-pending-5" --include='*.md' . | grep -v node_modules`
Expected: only lines of this plan. Any other hit is a file to update in Step 4.

- [ ] **Step 2: Rename**

Run: `git mv docs/superpowers/2026-10-03-current-kpis-in-kernel-pending-5.md docs/superpowers/2026-10-03-current-kpis-in-kernel.md`

- [ ] **Step 3: Update the status line**

Replace `**Status:** pending its plan. **Depends on:**` with
``**Status:** planned in `2026-10-03-current-kpis-in-kernel-plan.md`. **Depends on:**``

- [ ] **Step 4: Append the amendments**

At the end of the spec, add `## Amendments made while planning`, opening with "Each item supersedes the line of this spec it names; the plan builds the amended version." Then add one bullet per item 1 to 15 of this plan's "Decisions taken while planning", each with its reason. Shorten the wording, but keep every key, bound, column name and date. Also delete the parenthesis `(at ... until Task 1 renames it)` from this plan's `**Spec:**` line.

- [ ] **Step 5: Verify**

Run: `git status --short`
Expected: `R` from the old path to the new one, `M` on it, and `?? docs/superpowers/2026-10-03-current-kpis-in-kernel-plan.md`. Nothing else.

- [ ] **Step 6: Ask the user, then commit**

```bash
git add docs/superpowers/
git commit -q -F - <<'MSG'
Plan the current KPIs in the kernel and rename their spec, with the primitives the metrics forced written into it

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 2: The language grows, and every metric gets its `kernel:` block

**Files:**
- Modify: `data/metricas.yaml` (whole file), `data/kernel/lenguaje.schema.json` (whole file), `data/kernel/fuentes.yaml`
- Modify: `packages/tools/centinela_tools/compiler.py` (whole file), `packages/tools/centinela_tools/tools.py`, `packages/tools/centinela_tools/generate.py`
- Create: `packages/tools/tests/test_primitives.py`
- Modify: `packages/tools/tests/test_language.py`, `test_compiler.py`, `test_sources.py`, `test_generate.py`
- Regenerate: `data/sql/05_kpis.generated.sql`

**Interfaces:**
- Consumes: `centinela_tools/sources.py:Table`, `Join`, `Source`, `Sources` and `load_sources()`, unchanged; `centinela_tools/language.py:check_block(block)`, unchanged.
- Produces:
  - `compiler.compile_kpi(block, sources, day=sql.Placeholder("dia"), thresholds=None) -> Compiled`, where `thresholds` is the entry's `umbrales` mapping or `None`; `Compiled(query, columns, entity)` keeps its fields.
  - `compiler.function_definition(metric, block, sources, thresholds=None) -> sql.Composable`, which now opens with `DROP FUNCTION IF EXISTS "centinela"."k_<metric>"(date);` and uses `CREATE FUNCTION`.
  - `compiler.COMPILER_VERSION == "2"` and `compiler.BUSINESS_DAYS`, the composition Task 3's test runs.
  - `tools.catalogue_of(entries, sources, approved)` compiles each base KPI with its `umbrales`; its signature is unchanged.
  - The columns of each base KPI, which Tasks 3 and 4 read:

    | KPI | Entity | Other columns, in order |
    |---|---|---|
    | `margen_pct` | `linea` | `margen_pct`, `margen_pct_base`, `caida_pts`, `ventas`, `margen_minimo_pct`, `ventas_mes_prom`, `pesos_en_riesgo` |
    | `saldo_vencido` | `cliente_id` | `saldo_vencido`, `saldo_abierto`, `max_dias_vencido`, `cupo_credito`, `pesos_en_riesgo` |
    | `concentracion_vencida_pct` | `cliente_id` | `saldo_vencido`, `concentracion_vencida_pct`, `pesos_en_riesgo` |
    | `dias_pago_prom` | `cliente_id` | `dias_pago_prom`, `dias_pago_prom_base`, `aumento_pct`, `pesos_en_riesgo` |
    | `cobertura_dias` | `sku`, `bodega_id` | `demanda_prom_30d`, `existencia`, `clase_abc`, `precio_lista`, `pedidos_por_despachar`, `cobertura_dias`, `pedidos_pendientes`, `pesos_en_riesgo` |
    | `variacion_costo_pct` | `sku` | `costo_unitario`, `costo_anterior`, `fecha_vigencia`, `ultimo_cambio_precio`, `precio_lista`, `unidades_desde_vigencia`, `unidades_mes_prom`, `variacion_pct`, `dias_habiles_sin_traslado`, `pesos_en_riesgo` |
    | `dias_retraso` | `oc_id` | `fecha_recibida`, `fecha_esperada`, `pesos_en_riesgo`, `recibida`, `dias_retraso` |
    | `descuento_en_exceso` | `vendedor_id`, `semana` | `descuento_en_exceso`, `exceso_semana_anterior`, `pesos_en_riesgo` |
    | `margen_bruto_negativo` | `pedido_id`, `linea_n` | `margen_bruto`, `sku`, `fecha`, `pesos_en_riesgo` |
    | `veces_intervalo_habitual` | `cliente_id` | `pedidos`, `ultima_compra`, `primera_compra`, `pesos_en_riesgo`, `intervalo_prom_dias`, `dias_sin_comprar`, `veces_intervalo_habitual` |

- [ ] **Step 1: Write the metrics**

Replace `data/metricas.yaml` with the file below. Every existing key of every entry is kept, and every value but `dias_pago_prom`'s `descripcion` (decision 15); each entry gains the ISO 22400-2 fields and a `kernel:` block, and the header's second line changes (decision 12).

```yaml
# Centinela · definición única de las métricas (capa semántica)
# Vigía lee estas métricas a través del kernel, centinela.k_<métrica>(dia), y el Analista además a través de las vistas SQL; nunca se recalculan con el modelo de lenguaje.
moneda: COP
fecha_corte: "máximo de inventario_diario.fecha (o el día del reloj simulado)"
metricas:
  margen_pct:
    descripcion: Margen bruto sobre ventas netas
    formula: 1 - sum(costo_total) / sum(valor_neto)
    vista: v_margen_semanal_linea
    dimensiones: [semana, linea]
    umbral_alerta: "caída > 3 puntos vs. promedio de las 8 semanas previas, o margen bajo ref_margen_minimo_linea"
    umbrales: { caida_pts: 3, margen_pct: { columna: margen_minimo_pct } }
    fuente_umbral: "kit; margen mínimo en OPE-POL-007 §4 (vista v_margen_minimo_linea)"
    pesos_en_riesgo: "(max(promedio 8 semanas previas, margen_minimo_pct) - margen_pct) / 100 * ventas de la semana"
    unidad: "%"
    rango: { min: null, max: 100 }
    tendencia: mayor_es_mejor
    temporalidad: semanal
    audiencia: [supervision]
    kernel:
      fuente: pedidos_detalle
      unir: [pedidos, productos, margen_minimo]
      filtro:
        - { columna: pedidos.estado, op: "!=", valor: Cancelado }
      agrupar: [productos.linea]
      razon:
        numerador:
          agregado: sum
          de: { op: "*", izq: { op: "-", izq: pedidos_detalle.valor_neto, der: { op: "*", izq: pedidos_detalle.cantidad, der: pedidos_detalle.costo_unitario } }, der: 100 }
        denominador: { agregado: sum, de: pedidos_detalle.valor_neto }
      linea_base: { columna: pedidos.fecha, periodo: semana, n: 8, salida: caida }
      columnas:
        ventas: { agregado: sum, de: pedidos_detalle.valor_neto }
        margen_minimo_pct: { agregado: max, de: margen_minimo.margen_minimo_pct }
        ventas_mes_prom: { agregado: max, de: trimestre.ventas_mes_prom }
      tomar:
        trimestre:
          por: { linea: productos.linea }
          kpi:
            fuente: pedidos_detalle
            unir: [pedidos, productos]
            ventana: { columna: pedidos.fecha, dias: 90 }
            filtro:
              - { columna: pedidos.estado, op: "!=", valor: Cancelado }
            agrupar: [productos.linea]
            medida: { agregado: sum, de: pedidos_detalle.valor_neto }
            derivadas:
              ventas_mes_prom: { op: "/", izq: ventas_90d, der: 3 }
            salida: { valor: ventas_90d }
      derivadas:
        pesos_en_riesgo: { op: "*", izq: { op: "/", izq: { op: "-", izq: { mayor: [margen_pct_base, margen_minimo_pct] }, der: margen_pct }, der: 100 }, der: ventas }
      decimales: { margen_pct: 2, margen_pct_base: 2, caida_pts: 2, ventas_mes_prom: 0, pesos_en_riesgo: 0 }
      salida: { valor: margen_pct, base: margen_pct_base, delta: caida_pts }
  saldo_vencido:
    descripcion: Valor de facturas abiertas con fecha de vencimiento anterior al corte
    vista: v_cartera_cliente
    umbral_alerta: "max_dias_vencido > 15 (política de crédito) o saldo_abierto > cupo_credito"
    umbrales: { max_dias_vencido: 15, saldo_abierto: { columna: cupo_credito } }
    fuente_umbral: "FIN-POL-004 §3 y §4"
    tramos: "FIN-POL-004 §4 por max_dias_vencido: tramo_1 de 1 a 15, tramo_2 de 16 a 30, tramo_3 de 31 a 60, tramo_4 más de 60"
    pesos_en_riesgo: "saldo_vencido"
    unidad: COP
    rango: { min: 0, max: null }
    tendencia: menor_es_mejor
    temporalidad: diaria
    audiencia: [operacion, supervision, gerencia]
    kernel:
      fuente: facturas
      unir: [clientes]
      abierto_al_dia: { desde: facturas.fecha_factura, hasta: pagada }
      agrupar: [facturas.cliente_id]
      medida:
        agregado: sum
        de: facturas.valor_total
        si:
          - { columna: facturas.fecha_vencimiento, op: "<", contra: dia }
      columnas:
        saldo_abierto: { agregado: sum, de: facturas.valor_total }
        max_dias_vencido: { agregado: max, de: { op: "-", izq: dia, der: facturas.fecha_vencimiento } }
        cupo_credito: { agregado: max, de: clientes.cupo_credito }
      derivadas:
        pesos_en_riesgo: saldo_vencido
      salida: { valor: saldo_vencido }
  concentracion_vencida_pct:
    descripcion: Participación del cliente en la cartera vencida total
    formula: saldo_vencido del cliente / sum(saldo_vencido) de todos los clientes
    vista: v_cartera_cliente
    umbral_alerta: "> 10% de la cartera vencida total"
    umbrales: { concentracion_vencida_pct: 10 }
    fuente_umbral: "FIN-POL-004 §5"
    pesos_en_riesgo: "saldo_vencido"
    unidad: "%"
    rango: { min: 0, max: 100 }
    tendencia: menor_es_mejor
    temporalidad: diaria
    audiencia: [operacion, supervision]
    kernel:
      fuente: facturas
      abierto_al_dia: { desde: facturas.fecha_factura, hasta: pagada }
      agrupar: [facturas.cliente_id]
      medida:
        agregado: sum
        de: facturas.valor_total
        si:
          - { columna: facturas.fecha_vencimiento, op: "<", contra: dia }
      derivadas:
        concentracion_vencida_pct: { participacion: saldo_vencido }
        pesos_en_riesgo: saldo_vencido
      decimales: { concentracion_vencida_pct: 2 }
      salida: { valor: saldo_vencido }
  dias_pago_prom:
    descripcion: Días promedio entre factura y pago, por mes de pago
    vista: v_dias_pago_mensual
    umbral_alerta: "aumento > 50% frente al promedio histórico del cliente"
    umbrales: { aumento_pct: 50 }
    fuente_umbral: "FIN-POL-004 §5"
    pesos_en_riesgo: "saldo_abierto del cliente en v_cartera_cliente"
    unidad: días
    rango: { min: 0, max: null }
    tendencia: menor_es_mejor
    temporalidad: mensual
    audiencia: [operacion]
    kernel:
      fuente: pagos
      unir: [facturas]
      agrupar: [facturas.cliente_id]
      medida: { agregado: avg, de: { op: "-", izq: pagos.fecha_pago, der: facturas.fecha_factura } }
      linea_base: { columna: pagos.fecha_pago, periodo: mes, n: 12, salida: delta_pct }
      columnas:
        pesos_en_riesgo: { agregado: max, de: cartera.saldo_abierto }
      tomar:
        cartera:
          por: { cliente_id: facturas.cliente_id }
          kpi:
            fuente: facturas
            abierto_al_dia: { desde: facturas.fecha_factura, hasta: pagada }
            agrupar: [facturas.cliente_id]
            medida: { agregado: sum, de: facturas.valor_total }
            salida: { valor: saldo_abierto }
      decimales: { dias_pago_prom: 1, dias_pago_prom_base: 1 }
      salida: { valor: dias_pago_prom, base: dias_pago_prom_base, delta: aumento_pct }
  cobertura_dias:
    descripcion: Existencia / demanda promedio diaria de los últimos 30 días
    vista: v_cobertura_inventario
    umbral_alerta: "< 10 días en clase A (política de inventario); crítico < 5 días con pedidos pendientes"
    umbrales: { cobertura_dias: { por: clase_abc, valores: { A: 10, B: 7 } } }
    fuente_umbral: "OPE-POL-007 §2; clase B < 7 días; clase C sin acción automática, no alerta"
    pesos_en_riesgo: "demanda_prom_30d * (cobertura mínima de la clase - cobertura_dias) * precio_lista vigente en v_precio_sku"
    unidad: días
    rango: { min: 0, max: null }
    tendencia: mayor_es_mejor
    temporalidad: diaria
    audiencia: [operacion]
    kernel:
      fuente: inventario_diario
      unir: [productos]
      ventana: { columna: inventario_diario.fecha, dias: 30 }
      agrupar: [inventario_diario.sku, inventario_diario.bodega_id]
      medida: { agregado: avg, de: inventario_diario.salidas }
      columnas:
        existencia: { agregado: ultimo, de: inventario_diario.existencia_final, por: inventario_diario.fecha }
        clase_abc: { agregado: max, de: productos.clase_abc }
        precio_lista: { agregado: max, de: precio.precio_lista }
        pedidos_por_despachar: { agregado: max, de: pendientes.pedidos }
      tomar:
        precio:
          por: { sku: inventario_diario.sku }
          kpi:
            fuente: lista_precios
            agrupar: [lista_precios.sku]
            medida: { agregado: ultimo, de: lista_precios.precio_lista, por: lista_precios.fecha_vigencia }
            salida: { valor: precio_lista }
        pendientes:
          por: { sku: inventario_diario.sku }
          kpi:
            fuente: pedidos_detalle
            unir: [pedidos]
            abierto_al_dia: { desde: pedidos.fecha, hasta: facturada }
            filtro:
              - { columna: pedidos.estado, op: "!=", valor: Cancelado }
            agrupar: [pedidos_detalle.sku]
            medida: { agregado: count }
            salida: { valor: pedidos }
      derivadas:
        cobertura_dias: { op: "/", izq: existencia, der: demanda_prom_30d }
        pedidos_pendientes: { mayor: [pedidos_por_despachar, 0] }
        pesos_en_riesgo: { op: "*", izq: { op: "*", izq: demanda_prom_30d, der: { op: "-", izq: { umbral: cobertura_dias }, der: cobertura_dias } }, der: precio_lista }
      decimales: { demanda_prom_30d: 1, cobertura_dias: 1, pesos_en_riesgo: 0 }
      salida: { valor: demanda_prom_30d }
  variacion_costo_pct:
    descripcion: Variación del costo unitario de un SKU frente a su costo anterior
    vista: v_costo_sku
    umbral_alerta: "> 5% sin un cambio de precio_lista en v_precio_sku dentro de 10 días hábiles"
    umbrales: { variacion_pct: 5, dias_habiles_sin_traslado: 10 }
    fuente_umbral: "OPE-POL-007 §4"
    pesos_en_riesgo: "(costo_unitario - costo_anterior) * unidades vendidas del SKU desde fecha_vigencia en v_ventas"
    unidad: "%"
    rango: { min: null, max: null }
    tendencia: menor_es_mejor
    temporalidad: diaria
    audiencia: [supervision]
    kernel:
      fuente: costos_proveedor
      agrupar: [costos_proveedor.sku]
      medida: { agregado: ultimo, de: costos_proveedor.costo_unitario, por: costos_proveedor.fecha_vigencia }
      columnas:
        costo_anterior: { agregado: anterior, de: costos_proveedor.costo_unitario, por: costos_proveedor.fecha_vigencia }
        fecha_vigencia: { agregado: max, de: costos_proveedor.fecha_vigencia }
        ultimo_cambio_precio: { agregado: max, de: precio.ultimo_cambio_precio }
        precio_lista: { agregado: max, de: precio.precio_lista }
        unidades_desde_vigencia: { agregado: max, de: ventas.unidades_desde_vigencia }
        unidades_mes_prom: { agregado: max, de: ventas.unidades_mes_prom }
      tomar:
        precio:
          por: { sku: costos_proveedor.sku }
          kpi:
            fuente: lista_precios
            agrupar: [lista_precios.sku]
            medida: { agregado: max, de: lista_precios.fecha_vigencia }
            columnas:
              precio_lista: { agregado: ultimo, de: lista_precios.precio_lista, por: lista_precios.fecha_vigencia }
            salida: { valor: ultimo_cambio_precio }
        ventas:
          por: { sku: costos_proveedor.sku }
          kpi:
            fuente: pedidos_detalle
            unir: [pedidos]
            filtro:
              - { columna: pedidos.estado, op: "!=", valor: Cancelado }
            agrupar: [pedidos_detalle.sku]
            medida:
              agregado: sum
              de: pedidos_detalle.cantidad
              si:
                - { columna: pedidos.fecha, op: ">=", contra: vigencia.fecha_vigencia }
            columnas:
              unidades_90d:
                agregado: sum
                de: pedidos_detalle.cantidad
                si:
                  - { columna: pedidos.fecha, op: ">", contra: dia, menos_dias: 90 }
            tomar:
              vigencia:
                por: { sku: pedidos_detalle.sku }
                kpi:
                  fuente: costos_proveedor
                  agrupar: [costos_proveedor.sku]
                  medida: { agregado: max, de: costos_proveedor.fecha_vigencia }
                  salida: { valor: fecha_vigencia }
            derivadas:
              unidades_mes_prom: { op: "/", izq: unidades_90d, der: 3 }
            salida: { valor: unidades_desde_vigencia }
      derivadas:
        variacion_pct: { op: "*", izq: { op: "-", izq: { op: "/", izq: costo_unitario, der: costo_anterior }, der: 1 }, der: 100 }
        dias_habiles_sin_traslado:
          si:
            cuando: { compara: { izq: ultimo_cambio_precio, op: ">=", der: fecha_vigencia } }
            entonces: 0
            sino: { dias_habiles: { desde: fecha_vigencia, hasta: dia } }
        pesos_en_riesgo: { op: "*", izq: { op: "-", izq: costo_unitario, der: costo_anterior }, der: unidades_desde_vigencia }
      decimales: { variacion_pct: 2, unidades_mes_prom: 1, pesos_en_riesgo: 0 }
      salida: { valor: costo_unitario }
  dias_retraso:
    descripcion: Días entre la fecha esperada de una orden de compra y su recepción o el corte
    vista: v_ordenes_compra
    umbral_alerta: "> 0 en una orden no recibida"
    umbrales: { dias_retraso: 0, recibida: false }
    fuente_umbral: "OPE-POL-007 §3"
    pesos_en_riesgo: "cantidad * costo_unitario de la orden"
    unidad: días
    rango: { min: 0, max: null }
    tendencia: menor_es_mejor
    temporalidad: diaria
    audiencia: [operacion]
    kernel:
      fuente: ordenes_compra
      agrupar: [ordenes_compra.oc_id]
      medida: { agregado: max, de: ordenes_compra.fecha_recibida }
      columnas:
        fecha_esperada: { agregado: max, de: ordenes_compra.fecha_esperada }
        pesos_en_riesgo: { agregado: sum, de: { op: "*", izq: ordenes_compra.cantidad, der: ordenes_compra.costo_unitario } }
      derivadas:
        recibida: { existe: fecha_recibida }
        dias_retraso:
          si:
            cuando: { existe: fecha_recibida }
            entonces: { mayor: [{ op: "-", izq: fecha_recibida, der: fecha_esperada }, 0] }
            sino: { mayor: [{ op: "-", izq: dia, der: fecha_esperada }, 0] }
      salida: { valor: fecha_recibida }
  descuento_en_exceso:
    descripcion: Descuento otorgado por encima del tope del segmento sin aprobación especial
    vista: v_descuentos_fuera_politica
    umbral_alerta: "cualquier línea; agrupar por vendedor y semana"
    umbrales: { descuento_en_exceso: 0 }
    fuente_umbral: "COM-POL-002 §2 y §3; dos semanas consecutivas del mismo vendedor escala según §5"
    pesos_en_riesgo: "sum(descuento_en_exceso)"
    unidad: COP
    rango: { min: 0, max: null }
    tendencia: menor_es_mejor
    temporalidad: semanal
    audiencia: [supervision, gerencia]
    kernel:
      fuente: pedidos_detalle
      unir: [pedidos, clientes, topes]
      filtro:
        - { columna: pedidos.estado, op: "!=", valor: Cancelado }
        - { columna: pedidos_detalle.aprobacion_especial, op: "=", valor: "N" }
        - { columna: pedidos_detalle.descuento_pct, op: ">", contra: topes.tope_descuento_pct }
      agrupar: [pedidos.vendedor_id, { columna: pedidos.fecha, por: semana }]
      medida:
        agregado: sum
        de: { op: "/", izq: { op: "*", izq: { op: "*", izq: pedidos_detalle.cantidad, der: pedidos_detalle.precio_unitario }, der: { op: "-", izq: pedidos_detalle.descuento_pct, der: topes.tope_descuento_pct } }, der: 100 }
      derivadas:
        exceso_semana_anterior: { periodo_anterior: descuento_en_exceso }
        pesos_en_riesgo: descuento_en_exceso
      decimales: { descuento_en_exceso: 0, exceso_semana_anterior: 0, pesos_en_riesgo: 0 }
      salida: { valor: descuento_en_exceso }
  margen_bruto_negativo:
    descripcion: Líneas de pedido vendidas por debajo del costo
    vista: v_ventas
    umbral_alerta: "margen_bruto < 0"
    umbrales: { margen_bruto: 0 }
    fuente_umbral: "COM-POL-002 §4; los datos no registran la aprobación escrita de Gerencia General"
    pesos_en_riesgo: "-sum(margen_bruto)"
    unidad: COP
    rango: { min: null, max: 0 }
    tendencia: mayor_es_mejor
    temporalidad: diaria
    audiencia: [gerencia]
    kernel:
      fuente: pedidos_detalle
      unir: [pedidos]
      filtro:
        - { columna: pedidos.estado, op: "!=", valor: Cancelado }
      agrupar: [pedidos_detalle.pedido_id, pedidos_detalle.linea_n]
      medida: { agregado: sum, de: { op: "-", izq: pedidos_detalle.valor_neto, der: { op: "*", izq: pedidos_detalle.cantidad, der: pedidos_detalle.costo_unitario } } }
      columnas:
        sku: { agregado: max, de: pedidos_detalle.sku }
        fecha: { agregado: max, de: pedidos.fecha }
      derivadas:
        pesos_en_riesgo: { op: "-", izq: 0, der: margen_bruto }
      tener:
        - { columna: margen_bruto, op: "<", valor: 0 }
      salida: { valor: margen_bruto }
  veces_intervalo_habitual:
    descripcion: Días sin comprar / intervalo habitual entre pedidos del cliente
    vista: v_actividad_cliente
    umbral_alerta: "> 3 veces el intervalo habitual en clientes con 10 o más pedidos"
    umbrales: { pedidos: 10, veces_intervalo_habitual: 3 }
    fuente_umbral: "kit"
    pesos_en_riesgo: "valor_neto promedio por mes del cliente en v_ventas, últimos 6 meses hasta ultima_compra"
    unidad: veces
    rango: { min: 0, max: null }
    tendencia: menor_es_mejor
    temporalidad: diaria
    audiencia: [operacion]
    kernel:
      fuente: pedidos
      filtro:
        - { columna: pedidos.estado, op: "!=", valor: Cancelado }
      agrupar: [pedidos.cliente_id]
      medida: { agregado: count }
      columnas:
        ultima_compra: { agregado: max, de: pedidos.fecha }
        primera_compra: { agregado: min, de: pedidos.fecha }
        pesos_en_riesgo: { agregado: max, de: compras.valor_mes_prom }
      tomar:
        compras:
          por: { cliente_id: pedidos.cliente_id }
          kpi:
            fuente: pedidos_detalle
            unir: [pedidos]
            filtro:
              - { columna: pedidos.estado, op: "!=", valor: Cancelado }
            agrupar: [pedidos.cliente_id]
            medida:
              agregado: sum
              de: pedidos_detalle.valor_neto
              si:
                - { columna: pedidos.fecha, op: ">", contra: ultima.ultima_compra, menos_meses: 6 }
            tomar:
              ultima:
                por: { cliente_id: pedidos.cliente_id }
                kpi:
                  fuente: pedidos
                  filtro:
                    - { columna: pedidos.estado, op: "!=", valor: Cancelado }
                  agrupar: [pedidos.cliente_id]
                  medida: { agregado: max, de: pedidos.fecha }
                  salida: { valor: ultima_compra }
            derivadas:
              valor_mes_prom: { op: "/", izq: valor_6m, der: 6 }
            salida: { valor: valor_6m }
      derivadas:
        intervalo_prom_dias: { op: "/", izq: { op: "-", izq: ultima_compra, der: primera_compra }, der: { op: "-", izq: pedidos, der: 1 } }
        dias_sin_comprar: { op: "-", izq: dia, der: ultima_compra }
        veces_intervalo_habitual: { op: "/", izq: dias_sin_comprar, der: intervalo_prom_dias }
      decimales: { intervalo_prom_dias: 1, veces_intervalo_habitual: 1, pesos_en_riesgo: 0 }
      salida: { valor: pedidos }
```

- [ ] **Step 2: Write the tests of the primitives**

Create `packages/tools/tests/test_primitives.py`:

```python
# The primitives the current metrics need, with no database: one planted violation per new bound of
# the language and per new refusal of the compiler, each with its guard, and the SQL each primitive
# compiles to. The blocks come from data/metricas.yaml, because they are the KPIs these primitives
# exist for.
import copy

import pytest

from centinela_tools.compiler import compile_kpi
from centinela_tools.language import check_block
from centinela_tools.paths import METRICAS
from centinela_tools.refusal import Refused
from centinela_tools.sources import load_sources
from centinela_tools.tools import load_entries

SOURCES = load_sources()
ENTRIES = load_entries(METRICAS)
SUM = {"agregado": "sum", "de": "facturas.valor_total"}


def block(metric, change=lambda b: None):
    copied = copy.deepcopy(ENTRIES[metric]["kernel"])
    change(copied)
    return copied


def text(metric, change=lambda b: None):
    return compile_kpi(block(metric, change), SOURCES, thresholds=ENTRIES[metric].get("umbrales")).query.as_string()


def refused(metric, change, thresholds=None):
    with pytest.raises(Refused) as caught:
        compile_kpi(block(metric, change), SOURCES, thresholds=ENTRIES[metric].get("umbrales") if thresholds is None else thresholds)
    return caught.value


def nested(depth):
    inner = {"fuente": "facturas", "agrupar": ["facturas.cliente_id"], "medida": SUM, "salida": {"valor": "v"}}
    for _ in range(depth):
        inner = {**inner, "tomar": {"t": {"kpi": copy.deepcopy(inner), "por": {"cliente_id": "facturas.cliente_id"}}}}
    return inner


def deep(levels):
    node = "saldo_vencido"
    for _ in range(levels):
        node = {"op": "+", "izq": node, "der": 1}
    return node


@pytest.mark.parametrize(
    "change, path",
    [
        pytest.param(lambda b: b.update(columnas={f"c{i}": SUM for i in range(9)}), "columnas", id="nine-columns"),
        pytest.param(lambda b: b.update(derivadas={f"d{i}": "saldo_vencido" for i in range(7)}), "derivadas", id="seven-derived"),
        pytest.param(lambda b: b.update(decimales={"saldo_vencido": 5}), "decimales/saldo_vencido", id="five-decimals"),
        pytest.param(lambda b: b.update(tener=[{"columna": "saldo_vencido", "op": ">", "valor": i} for i in range(4)]), "tener", id="four-having"),
        pytest.param(lambda b: b.update(tomar={f"t{i}": {"kpi": nested(0), "por": {"cliente_id": "facturas.cliente_id"}} for i in range(3)}), "tomar", id="three-taken"),
        pytest.param(lambda b: b["medida"].update(si=[{"columna": "facturas.fecha_vencimiento", "op": "<", "contra": "dia"}] * 4), "medida/si", id="four-conditions"),
        pytest.param(lambda b: b["medida"]["si"][0].update(menos_dias=1, menos_meses=1), "medida/si/0", id="days-and-months"),
        pytest.param(lambda b: b["medida"]["si"][0].update(menos_dias=366), "medida/si/0/menos_dias", id="days-past-365"),
        pytest.param(lambda b: b["medida"]["si"][0].update(menos_meses=13), "medida/si/0/menos_meses", id="months-past-12"),
        pytest.param(lambda b: b["medida"]["si"][0].update(op="en"), "medida/si/0/op", id="en-against-a-column"),
        pytest.param(lambda b: b.update(medida={"agregado": "ultimo", "de": "facturas.valor_total"}), "medida", id="last-without-order"),
        pytest.param(lambda b: b.update(medida={**SUM, "por": "facturas.fecha_factura"}), "medida", id="order-on-a-sum"),
        pytest.param(lambda b: b.update(derivadas={"d": {"raiz": "saldo_vencido"}}), "derivadas/d", id="unknown-operation"),
        pytest.param(lambda b: b.update(derivadas={"d": {"mayor": ["saldo_vencido"]}}), "derivadas/d", id="greatest-of-one"),
    ],
)
def test_a_new_bound_of_the_language_is_refused(change, path):
    with pytest.raises(Refused) as caught:
        check_block(block("saldo_vencido", change))
    assert caught.value.guard == "lenguaje"
    assert caught.value.detail.startswith(path), caught.value.detail


@pytest.mark.parametrize(
    "metric, change, guard, words",
    [
        pytest.param("saldo_vencido", lambda b: b.update(tomar={"t": {"kpi": nested(2), "por": {"cliente_id": "facturas.cliente_id"}}}), "lenguaje", "at most 2 levels", id="taken-three-deep"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": deep(5)}), "lenguaje", "at most 4 operations", id="derived-five-deep"),
        pytest.param("variacion_costo_pct", lambda b: b["tomar"]["precio"].update(por={"sku": "costos_proveedor.sku", "otro": "costos_proveedor.proveedor_id"}), "fuente", "whole entity", id="taken-by-part-of-a-key"),
        pytest.param("saldo_vencido", lambda b: b.update(tomar={"clientes": {"kpi": nested(0), "por": {"cliente_id": "facturas.cliente_id"}}}), "fuente", "already the name", id="taken-named-as-a-join"),
        pytest.param("variacion_costo_pct", lambda b: b["tomar"]["precio"].update(por={"sku": "costos_proveedor.fecha_vigencia"}), "lenguaje", "joins", id="taken-by-another-type"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": "saldo_cero"}), "lenguaje", "no column", id="derived-from-nothing"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": {"umbral": "saldo_vencido"}}), "lenguaje", "umbral", id="threshold-not-in-umbrales"),
        pytest.param("variacion_costo_pct", lambda b: b.update(decimales={"fecha_vigencia": 1}), "lenguaje", "decimales", id="decimals-of-a-date"),
        pytest.param("variacion_costo_pct", lambda b: b.update(tener=[{"columna": "fecha_vigencia", "op": ">", "valor": 0}]), "lenguaje", "tener", id="having-on-a-date"),
        pytest.param("saldo_vencido", lambda b: b["medida"]["si"][0].update(contra="facturas.valor_total"), "lenguaje", "cannot be compared", id="date-against-a-number"),
        pytest.param("saldo_vencido", lambda b: b["medida"]["si"][0].update(columna="facturas.valor_total", contra="clientes.cupo_credito", menos_dias=3), "lenguaje", "no date", id="days-back-from-a-number"),
        pytest.param("margen_bruto_negativo", lambda b: b["medida"].update(si=[{"columna": "pedidos.estado", "op": "=", "contra": "pedidos.canal"}]), "fuente", "end of the dataset", id="fuga-against-a-column"),
        pytest.param("variacion_costo_pct", lambda b: b.update(medida={"agregado": "ultimo", "de": "costos_proveedor.costo_unitario", "por": "costos_proveedor.sku"}), "reloj", "not a date of an event", id="last-by-a-non-event"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": {"dias_habiles": {"desde": "saldo_abierto", "hasta": "dia"}}}), "lenguaje", "two dates", id="business-days-of-a-number"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": {"si": {"cuando": "saldo_abierto", "entonces": 1, "sino": 0}}}), "lenguaje", "cuando", id="if-on-a-number"),
        pytest.param("dias_retraso", lambda b: b.update(derivadas={"d": {"participacion": "fecha_esperada"}}), "lenguaje", "participacion", id="share-of-a-date"),
        pytest.param("saldo_vencido", lambda b: b.update(derivadas={"d": {"periodo_anterior": "saldo_vencido"}}), "lenguaje", "exactly one", id="previous-period-without-a-period"),
    ],
)
def test_a_new_primitive_the_kernel_cannot_bound_is_refused(metric, change, guard, words):
    refusal = refused(metric, change)
    assert refusal.guard == guard and words in refusal.detail, refusal


def test_a_condition_on_a_measure_is_a_filter_and_an_empty_sum_is_zero():
    assert 'coalesce(sum("facturas"."valor_total") FILTER (WHERE "facturas"."fecha_vencimiento" < CAST(%(dia)s AS date)), 0)::numeric' in text("saldo_vencido")


def test_dia_is_an_operand_of_an_expression():
    assert '(CAST(%(dia)s AS date) - "facturas"."fecha_vencimiento")' in text("saldo_vencido")


def test_a_filter_compares_two_columns():
    assert '"pedidos_detalle"."descuento_pct" > "topes"."tope_descuento_pct"' in text("descuento_en_exceso")


def test_a_condition_reaches_back_from_a_date_by_months():
    assert "(\"ultima\".\"ultima_compra\" - interval '1 month' * 6)::date" in text("veces_intervalo_habitual")


def test_the_last_and_the_previous_value_follow_an_event_date():
    query = text("variacion_costo_pct")
    assert '(array_agg("costos_proveedor"."costo_unitario" ORDER BY "costos_proveedor"."fecha_vigencia" DESC))[1]' in query
    assert '(array_agg("costos_proveedor"."costo_unitario" ORDER BY "costos_proveedor"."fecha_vigencia" DESC))[2]' in query


def test_a_taken_kpi_joins_on_its_whole_entity_and_reads_the_same_day():
    query = text("cobertura_dias")
    assert ') AS "precio" ON "precio"."sku" = "inventario_diario"."sku"' in query
    assert '"lista_precios"."fecha_vigencia" <= CAST(%(dia)s AS date)' in query
    assert query.count("LEFT JOIN (SELECT") == 2


def test_a_taken_kpi_is_many_to_one_by_construction():
    taken = compile_kpi(block("cobertura_dias")["tomar"]["precio"]["kpi"], SOURCES)
    assert taken.entity == ("sku",)


def test_a_derived_column_reads_the_unrounded_value_and_only_the_output_is_rounded():
    query = text("cobertura_dias")
    assert 'round(("nucleo"."existencia"::numeric / NULLIF("nucleo"."demanda_prom_30d"::numeric, 0))::numeric, 1)::numeric AS "cobertura_dias"' in query
    assert 'round("nucleo"."demanda_prom_30d"::numeric, 1)::numeric AS "demanda_prom_30d"' in query


def test_a_threshold_by_a_dimension_is_read_from_umbrales():
    assert "(CASE \"nucleo\".\"clase_abc\" WHEN 'A' THEN 10 WHEN 'B' THEN 7 END)" in text("cobertura_dias")


def test_business_days_compile_to_a_count_of_monday_to_friday():
    assert "generate_series(\"nucleo\".\"fecha_vigencia\" + 1, CAST(%(dia)s AS date), interval '1 day') AS habil(d) WHERE extract(isodow FROM habil.d) < 6" in text("variacion_costo_pct")


def test_a_share_divides_by_the_total_of_every_row():
    assert '(100 * "nucleo"."saldo_vencido"::numeric / NULLIF(sum("nucleo"."saldo_vencido") OVER (), 0))' in text("concentracion_vencida_pct")


def test_having_keeps_only_the_rows_it_names():
    assert text("margen_bruto_negativo").endswith('AS kpi WHERE "kpi"."margen_bruto" < 0')


def test_a_drop_is_the_base_minus_the_value():
    current = "date_trunc('week', CAST(%(dia)s AS date) - 6)::date"
    assert f"(avg(marco.valor) FILTER (WHERE marco.periodo < {current})::numeric - max(marco.valor) FILTER (WHERE marco.periodo = {current})::numeric)::numeric AS \"caida_pts\"" in text("margen_pct")


def test_a_column_of_a_baseline_kpi_is_measured_on_the_current_period():
    current = "date_trunc('week', CAST(%(dia)s AS date) - 6)::date"
    query = text("margen_pct")
    assert f'max("marco"."ventas") FILTER (WHERE marco.periodo = {current})::numeric AS "ventas"' in query
    assert 'coalesce("periodos"."ventas", 0) AS "ventas"' in query


def test_a_kpi_with_no_threshold_cannot_read_one():
    refusal = refused("cobertura_dias", lambda b: None, thresholds={})
    assert refusal.guard == "lenguaje" and "umbral cobertura_dias" in refusal.detail


def test_the_previous_period_is_the_same_entity_one_period_before():
    expected = (
        'max("nucleo"."descuento_en_exceso") OVER (PARTITION BY "nucleo"."vendedor_id" ORDER BY "nucleo"."semana" '
        "RANGE BETWEEN interval '1 week' PRECEDING AND interval '1 week' PRECEDING)"
    )
    assert expected in text("descuento_en_exceso")
```

- [ ] **Step 3: Run them to see them fail**

Run: `cd packages/tools && uv run pytest tests/test_primitives.py -q`
Expected: FAIL. The SQL tests fail with a `lenguaje` refusal such as `kernel: Additional properties are not allowed ('columnas', ...)` or `medida: Additional properties are not allowed ('si' ...)`, because the schema does not know the new keys yet.

- [ ] **Step 4: Write the language**

Replace `data/kernel/lenguaje.schema.json` with:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "kernel",
  "type": "object",
  "additionalProperties": false,
  "required": ["fuente", "agrupar", "salida"],
  "properties": {
    "fuente": { "$ref": "#/$defs/nombre" },
    "unir": { "type": "array", "maxItems": 3, "uniqueItems": true, "items": { "$ref": "#/$defs/nombre" } },
    "abierto_al_dia": {
      "type": "object", "additionalProperties": false, "required": ["desde", "hasta"],
      "properties": {
        "desde": { "$ref": "#/$defs/columna" },
        "hasta": { "anyOf": [{ "$ref": "#/$defs/columna" }, { "$ref": "#/$defs/nombre" }] }
      }
    },
    "ventana": {
      "type": "object", "additionalProperties": false, "required": ["columna", "dias"],
      "properties": { "columna": { "$ref": "#/$defs/columna" }, "dias": { "type": "integer", "minimum": 1, "maximum": 365 } }
    },
    "filtro": { "type": "array", "maxItems": 5, "items": { "$ref": "#/$defs/filtro" } },
    "agrupar": {
      "type": "array", "minItems": 1, "maxItems": 3,
      "items": { "anyOf": [{ "$ref": "#/$defs/columna" }, { "$ref": "#/$defs/periodo" }] }
    },
    "medida": { "$ref": "#/$defs/medida" },
    "razon": {
      "type": "object", "additionalProperties": false, "required": ["numerador", "denominador"],
      "properties": { "numerador": { "$ref": "#/$defs/medida" }, "denominador": { "$ref": "#/$defs/medida" } }
    },
    "linea_base": {
      "type": "object", "additionalProperties": false, "required": ["columna", "periodo", "n", "salida"],
      "properties": {
        "columna": { "$ref": "#/$defs/columna" },
        "periodo": { "enum": ["semana", "mes"] },
        "n": { "type": "integer", "minimum": 1, "maximum": 12 },
        "salida": { "enum": ["delta", "delta_pct", "caida"] }
      }
    },
    "columnas": { "type": "object", "maxProperties": 8, "propertyNames": { "$ref": "#/$defs/nombre" }, "additionalProperties": { "$ref": "#/$defs/medida" } },
    "tomar": {
      "type": "object", "maxProperties": 2, "propertyNames": { "$ref": "#/$defs/nombre" },
      "additionalProperties": {
        "type": "object", "additionalProperties": false, "required": ["kpi", "por"],
        "properties": {
          "kpi": { "$ref": "#" },
          "por": { "type": "object", "minProperties": 1, "maxProperties": 3, "propertyNames": { "$ref": "#/$defs/nombre" }, "additionalProperties": { "$ref": "#/$defs/columna" } }
        }
      }
    },
    "derivadas": { "type": "object", "maxProperties": 6, "propertyNames": { "$ref": "#/$defs/nombre" }, "additionalProperties": { "$ref": "#/$defs/derivada" } },
    "decimales": { "type": "object", "maxProperties": 12, "propertyNames": { "$ref": "#/$defs/nombre" }, "additionalProperties": { "type": "integer", "minimum": 0, "maximum": 4 } },
    "tener": {
      "type": "array", "maxItems": 3,
      "items": {
        "type": "object", "additionalProperties": false, "required": ["columna", "op", "valor"],
        "properties": { "columna": { "$ref": "#/$defs/nombre" }, "op": { "$ref": "#/$defs/comparacion" }, "valor": { "type": "number" } }
      }
    },
    "salida": {
      "type": "object", "additionalProperties": false, "required": ["valor"],
      "properties": { "valor": { "$ref": "#/$defs/nombre" }, "base": { "$ref": "#/$defs/nombre" }, "delta": { "$ref": "#/$defs/nombre" } }
    }
  },
  "oneOf": [{ "required": ["medida"] }, { "required": ["razon"] }],
  "not": {
    "anyOf": [
      { "required": ["ventana", "abierto_al_dia"] },
      { "required": ["ventana", "linea_base"] },
      { "required": ["abierto_al_dia", "linea_base"] }
    ]
  },
  "if": { "required": ["linea_base"] },
  "then": { "properties": { "salida": { "required": ["valor", "base", "delta"] } } },
  "else": { "properties": { "salida": { "properties": { "base": false, "delta": false } } } },
  "$defs": {
    "nombre": { "type": "string", "pattern": "^[a-z][a-z0-9_]{0,62}$" },
    "columna": { "type": "string", "pattern": "^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$" },
    "comparacion": { "enum": ["=", "!=", "<", "<=", ">", ">="] },
    "periodo": {
      "type": "object", "additionalProperties": false, "required": ["columna", "por"],
      "properties": { "columna": { "$ref": "#/$defs/columna" }, "por": { "enum": ["semana", "mes"] } }
    },
    "literal": {
      "anyOf": [
        { "type": "string", "maxLength": 200, "pattern": "^[^%\\u0000]*$" },
        { "type": "number" },
        { "type": "boolean" }
      ]
    },
    "filtro": {
      "if": { "required": ["contra"] },
      "then": { "$ref": "#/$defs/filtro_contra" },
      "else": { "$ref": "#/$defs/filtro_valor" }
    },
    "filtro_valor": {
      "type": "object", "additionalProperties": false, "required": ["columna", "op", "valor"],
      "properties": {
        "columna": { "$ref": "#/$defs/columna" },
        "op": { "enum": ["=", "!=", "<", "<=", ">", ">=", "en"] },
        "valor": true
      },
      "if": { "properties": { "op": { "const": "en" } } },
      "then": { "properties": { "valor": { "type": "array", "minItems": 1, "maxItems": 20, "items": { "$ref": "#/$defs/literal" } } } },
      "else": { "properties": { "valor": { "$ref": "#/$defs/literal" } } }
    },
    "filtro_contra": {
      "type": "object", "additionalProperties": false, "required": ["columna", "op", "contra"],
      "properties": {
        "columna": { "$ref": "#/$defs/columna" },
        "op": { "$ref": "#/$defs/comparacion" },
        "contra": { "anyOf": [{ "$ref": "#/$defs/columna" }, { "const": "dia" }] },
        "menos_dias": { "type": "integer", "minimum": 1, "maximum": 365 },
        "menos_meses": { "type": "integer", "minimum": 1, "maximum": 12 }
      },
      "not": { "required": ["menos_dias", "menos_meses"] }
    },
    "operando": { "anyOf": [{ "$ref": "#/$defs/columna" }, { "type": "number" }, { "const": "dia" }] },
    "operacion_1": {
      "type": "object", "additionalProperties": false, "required": ["op", "izq", "der"],
      "properties": { "op": { "enum": ["+", "-", "*", "/"] }, "izq": { "$ref": "#/$defs/operando" }, "der": { "$ref": "#/$defs/operando" } }
    },
    "operacion_2": {
      "type": "object", "additionalProperties": false, "required": ["op", "izq", "der"],
      "properties": {
        "op": { "enum": ["+", "-", "*", "/"] },
        "izq": { "anyOf": [{ "$ref": "#/$defs/operando" }, { "$ref": "#/$defs/operacion_1" }] },
        "der": { "anyOf": [{ "$ref": "#/$defs/operando" }, { "$ref": "#/$defs/operacion_1" }] }
      }
    },
    "operacion_3": {
      "type": "object", "additionalProperties": false, "required": ["op", "izq", "der"],
      "properties": {
        "op": { "enum": ["+", "-", "*", "/"] },
        "izq": { "anyOf": [{ "$ref": "#/$defs/operando" }, { "$ref": "#/$defs/operacion_1" }, { "$ref": "#/$defs/operacion_2" }] },
        "der": { "anyOf": [{ "$ref": "#/$defs/operando" }, { "$ref": "#/$defs/operacion_1" }, { "$ref": "#/$defs/operacion_2" }] }
      }
    },
    "expresion": {
      "anyOf": [{ "$ref": "#/$defs/columna" }, { "$ref": "#/$defs/operacion_1" }, { "$ref": "#/$defs/operacion_2" }, { "$ref": "#/$defs/operacion_3" }]
    },
    "medida": {
      "type": "object", "additionalProperties": false, "required": ["agregado"],
      "properties": {
        "agregado": { "enum": ["sum", "avg", "count", "min", "max", "mediana", "ultimo", "anterior"] },
        "de": { "$ref": "#/$defs/expresion" },
        "por": { "$ref": "#/$defs/columna" },
        "si": { "type": "array", "minItems": 1, "maxItems": 3, "items": { "$ref": "#/$defs/filtro" } }
      },
      "allOf": [
        { "if": { "properties": { "agregado": { "not": { "const": "count" } } } }, "then": { "required": ["de"] } },
        {
          "if": { "properties": { "agregado": { "enum": ["ultimo", "anterior"] } } },
          "then": { "required": ["por"] },
          "else": { "not": { "required": ["por"] } }
        }
      ]
    },
    "derivada": {
      "anyOf": [
        { "$ref": "#/$defs/nombre" },
        { "type": "number" },
        { "type": "object", "additionalProperties": false, "required": ["umbral"], "properties": { "umbral": { "$ref": "#/$defs/nombre" } } },
        {
          "type": "object", "additionalProperties": false, "required": ["op", "izq", "der"],
          "properties": { "op": { "enum": ["+", "-", "*", "/"] }, "izq": { "$ref": "#/$defs/derivada" }, "der": { "$ref": "#/$defs/derivada" } }
        },
        { "type": "object", "additionalProperties": false, "required": ["mayor"], "properties": { "mayor": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "$ref": "#/$defs/derivada" } } } },
        { "type": "object", "additionalProperties": false, "required": ["menor"], "properties": { "menor": { "type": "array", "minItems": 2, "maxItems": 2, "items": { "$ref": "#/$defs/derivada" } } } },
        {
          "type": "object", "additionalProperties": false, "required": ["dias_habiles"],
          "properties": {
            "dias_habiles": {
              "type": "object", "additionalProperties": false, "required": ["desde", "hasta"],
              "properties": { "desde": { "$ref": "#/$defs/derivada" }, "hasta": { "$ref": "#/$defs/derivada" } }
            }
          }
        },
        {
          "type": "object", "additionalProperties": false, "required": ["compara"],
          "properties": {
            "compara": {
              "type": "object", "additionalProperties": false, "required": ["izq", "op", "der"],
              "properties": { "izq": { "$ref": "#/$defs/derivada" }, "op": { "$ref": "#/$defs/comparacion" }, "der": { "$ref": "#/$defs/derivada" } }
            }
          }
        },
        { "type": "object", "additionalProperties": false, "required": ["existe"], "properties": { "existe": { "$ref": "#/$defs/nombre" } } },
        { "type": "object", "additionalProperties": false, "required": ["participacion"], "properties": { "participacion": { "$ref": "#/$defs/nombre" } } },
        { "type": "object", "additionalProperties": false, "required": ["periodo_anterior"], "properties": { "periodo_anterior": { "$ref": "#/$defs/nombre" } } },
        {
          "type": "object", "additionalProperties": false, "required": ["si"],
          "properties": {
            "si": {
              "type": "object", "additionalProperties": false, "required": ["cuando", "entonces", "sino"],
              "properties": { "cuando": { "$ref": "#/$defs/derivada" }, "entonces": { "$ref": "#/$defs/derivada" }, "sino": { "$ref": "#/$defs/derivada" } }
            }
          }
        }
      ]
    },
    "ficha": {
      "type": "object",
      "required": ["descripcion", "unidad", "rango", "tendencia", "temporalidad", "audiencia"],
      "properties": {
        "descripcion": { "type": "string", "minLength": 1 },
        "unidad": { "type": "string", "minLength": 1 },
        "rango": {
          "type": "object", "additionalProperties": false, "required": ["min", "max"],
          "properties": { "min": { "type": ["number", "null"] }, "max": { "type": ["number", "null"] } }
        },
        "tendencia": { "enum": ["mayor_es_mejor", "menor_es_mejor"] },
        "temporalidad": { "enum": ["diaria", "semanal", "mensual"] },
        "audiencia": { "type": "array", "minItems": 1, "uniqueItems": true, "items": { "enum": ["operacion", "supervision", "gerencia"] } }
      }
    }
  }
}
```

- [ ] **Step 5: Write the compiler**

Replace `packages/tools/centinela_tools/compiler.py` with the file below. What changes against the current one: `AGGREGATE` is split from its cast so a `FILTER` can follow the call; `Scope` holds a table per alias, so a taken KPI reads as a table; `operand`, `against`, `arithmetic`, `taken_join`, `build`, `threshold`, `unify`, `derived`, `previous` and `finish` are new; `baseline` measures `columnas` on the current period; `function_definition` drops before it creates.

```python
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from psycopg import sql

from .language import check_block
from .refusal import Refused
from .sources import Join, Source, Sources, Table

COMPILER_VERSION = "2"
NAME = re.compile(r"^[a-z][a-z0-9_]{0,60}$")
NUMERIC = frozenset({"integer", "bigint", "numeric"})
RESERVED = frozenset({"dia", "periodo"})
LITERALS = {"text": (str,), "integer": (int,), "bigint": (int,), "numeric": (int, float), "boolean": (bool,), "date": (str,)}
TYPES = {
    "text": sql.SQL("text"),
    "integer": sql.SQL("integer"),
    "bigint": sql.SQL("bigint"),
    "numeric": sql.SQL("numeric"),
    "date": sql.SQL("date"),
    "boolean": sql.SQL("boolean"),
}
COMPARE = {
    "=": sql.SQL("{} = {}"),
    "!=": sql.SQL("{} <> {}"),
    "<": sql.SQL("{} < {}"),
    "<=": sql.SQL("{} <= {}"),
    ">": sql.SQL("{} > {}"),
    ">=": sql.SQL("{} >= {}"),
}
ARITH = {
    "+": sql.SQL("({}::numeric + {}::numeric)"),
    "-": sql.SQL("({}::numeric - {}::numeric)"),
    "*": sql.SQL("({}::numeric * {}::numeric)"),
    "/": sql.SQL("({}::numeric / NULLIF({}::numeric, 0))"),
}
AGGREGATE = {
    "sum": sql.SQL("sum({})"),
    "avg": sql.SQL("avg({})"),
    "mediana": sql.SQL("percentile_cont(0.5) WITHIN GROUP (ORDER BY {})"),
    "min": sql.SQL("min({})"),
    "max": sql.SQL("max({})"),
    "count": sql.SQL("count({})"),
    "ultimo": sql.SQL("array_agg({} ORDER BY {} DESC)"),
    "anterior": sql.SQL("array_agg({} ORDER BY {} DESC)"),
}
FILTERED = sql.SQL("{} FILTER (WHERE {})")
PICK = {"ultimo": sql.SQL("({})[1]"), "anterior": sql.SQL("({})[2]")}
ZERO = sql.SQL("coalesce({}, 0)")
AS_NUMERIC = sql.SQL("{}::numeric")
ORDERED = frozenset({"ultimo", "anterior"})
DAYS_BACK = sql.SQL("({} - {})")
MONTHS_BACK = sql.SQL("({} - interval '1 month' * {})::date")
BUSINESS_DAYS = sql.SQL("(SELECT count(*) FROM generate_series({} + 1, {}, interval '1 day') AS habil(d) WHERE extract(isodow FROM habil.d) < 6)::integer")
GREATEST = {"mayor": sql.SQL("greatest({}, {})"), "menor": sql.SQL("least({}, {})")}
EXISTS = sql.SQL("({} IS NOT NULL)")
SHARE = sql.SQL("(100 * {x}::numeric / NULLIF(sum({x}) OVER (), 0))")
PREVIOUS = sql.SQL("max({x}) OVER ({partition}ORDER BY {period} RANGE BETWEEN {step} PRECEDING AND {step} PRECEDING)")
PARTITION = sql.SQL("PARTITION BY {} ")
WHEN = sql.SQL("(CASE WHEN {} THEN {} ELSE {} END)")
ROUND = sql.SQL("round({}::numeric, {})")
BY_VALUE = sql.SQL("(CASE {} {} END)")
WHEN_VALUE = sql.SQL("WHEN {} THEN {}")
MAX_TAKEN_DEPTH = 2
MAX_DERIVED_DEPTH = 4
TRUNC = {"semana": sql.SQL("date_trunc('week', {})::date"), "mes": sql.SQL("date_trunc('month', {})::date")}
LAST = {"semana": sql.SQL("date_trunc('week', {} - 6)::date"), "mes": sql.SQL("(date_trunc('month', {} + 1) - interval '1 month')::date")}
START = {"semana": sql.SQL("({} - 7 * {})"), "mes": sql.SQL("({} - interval '1 month' * {})::date")}
END = {"semana": sql.SQL("({} + 7)"), "mes": sql.SQL("({} + interval '1 month')::date")}
STEP = {"semana": sql.SQL("interval '1 week'"), "mes": sql.SQL("interval '1 month'")}
ZERO_WHEN_EMPTY = frozenset({"sum", "count"})
DELTA = {
    "delta": sql.SQL("({valor} - {base})::numeric"),
    "caida": sql.SQL("({base} - {valor})::numeric"),
    "delta_pct": sql.SQL("round(100 * ({valor} / NULLIF({base}, 0) - 1), 2)"),
}


@dataclass(frozen=True)
class Compiled:
    query: sql.Composable
    columns: tuple[tuple[str, str], ...]
    entity: tuple[str, ...]


@dataclass(frozen=True)
class Frozen:
    sql: str
    hash: str
    compiler_version: str


@dataclass(frozen=True)
class Taken:
    name: str
    compiled: Compiled
    on: Mapping[str, str]


@dataclass(frozen=True)
class Scope:
    sources: Sources
    source: Source
    tables: Mapping[str, Table]
    day: sql.Composable

    def table_of(self, alias: str) -> Table:
        return self.tables[alias]

    def column(self, ref: str) -> tuple[str, str, str]:
        alias, _, name = ref.partition(".")
        if alias not in self.tables:
            raise Refused("fuente", f"{ref}: {alias} is neither the source nor a join or a taken KPI this KPI names")
        table = self.table_of(alias)
        if name in table.excluded:
            raise Refused("fuente", f"{ref} is not readable: {table.excluded[name]}")
        if name not in table.columns:
            raise Refused("fuente", f"{ref} is not a column fuentes.yaml lets the kernel read")
        return alias, name, table.columns[name]

    def role(self, ref: str) -> str | None:
        alias, name, _ = self.column(ref)
        return self.table_of(alias).dates.get(name)

    def raw(self, alias: str, name: str) -> sql.Composable:
        column = sql.Identifier(alias, name)
        if self.table_of(alias).dates.get(name) == "cierre":
            return sql.SQL("(CASE WHEN {c} <= {d} THEN {c} END)").format(c=column, d=self.day)
        return column

    def read(self, ref: str) -> tuple[sql.Composable, str]:
        alias, name, kind = self.column(ref)
        if name in self.table_of(alias).leaks:
            raise Refused("fuente", f"{ref} holds the end of the dataset; only a filter on a value known when the row is created reads it")
        return self.raw(alias, name), kind


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def freeze(compiled: Compiled) -> Frozen:
    text = compiled.query.as_string()
    return Frozen(text, digest(text), COMPILER_VERSION)


def taken_table(taken: Taken) -> Table:
    return Table(taken.name, taken.compiled.entity, dict(taken.compiled.columns), {}, {}, {})


def scope_of(block: Mapping[str, Any], sources: Sources, day: sql.Composable, taken: list[Taken]) -> tuple[Scope, list[Join]]:
    source = sources.sources.get(block["fuente"])
    if source is None:
        raise Refused("fuente", f"fuente: {block['fuente']} is not a source fuentes.yaml declares")
    tables = {source.name: sources.tables[source.name]}
    joins = []
    for name in block.get("unir", []):
        join = source.joins.get(name)
        if join is None:
            raise Refused("fuente", f"unir: {name} is not a join fuentes.yaml declares for {source.name}")
        if join.origin not in tables:
            raise Refused("fuente", f"unir: {name} joins from {join.origin}, which unir does not name before it")
        tables[name] = sources.tables[join.table]
        joins.append(join)
    if source.dated_by is not None and source.dated_by not in tables:
        raise Refused("reloj", f"{source.name} has no date of its own; unir must name {source.dated_by}, which dates it")
    for item in taken:
        if item.name in tables:
            raise Refused("fuente", f"tomar: {item.name} is already the name of the source or of a join")
        tables[item.name] = taken_table(item)
    return Scope(sources, source, tables, day), joins


def event_bounds(scope: Scope, alias: str) -> list[sql.Composable]:
    dates = scope.table_of(alias).dates
    return [sql.SQL("{} <= {}").format(sql.Identifier(alias, column), scope.day) for column, role in dates.items() if role == "evento"]


def taken_join(item: Taken, scope: Scope) -> sql.Composable:
    if set(item.on) != set(item.compiled.entity):
        raise Refused("fuente", f"tomar: {item.name} joins by {sorted(item.on)}, and must join by the whole entity {list(item.compiled.entity)} of the KPI it takes")
    kinds = dict(item.compiled.columns)
    on = []
    for remote, local in item.on.items():
        column, kind = scope.read(local)
        if kind != kinds[remote]:
            raise Refused("lenguaje", f"tomar: {item.name} joins {local}, a {kind}, to {remote}, a {kinds[remote]}")
        on.append(sql.SQL("{} = {}").format(sql.Identifier(item.name, remote), column))
    return sql.SQL("LEFT JOIN ({}) AS {} ON {}").format(item.compiled.query, sql.Identifier(item.name), sql.SQL(" AND ").join(on))


def from_clause(scope: Scope, joins: list[Join], taken: list[Taken]) -> sql.Composable:
    parts = [sql.SQL("FROM {} AS {}").format(sql.Identifier("centinela", scope.source.name), sql.Identifier(scope.source.name))]
    for join in joins:
        on = [sql.SQL("{} = {}").format(sql.Identifier(join.origin, local), sql.Identifier(join.name, remote)) for local, remote in join.on.items()]
        on += event_bounds(scope, join.name)
        parts.append(sql.SQL("LEFT JOIN {} AS {} ON {}").format(sql.Identifier("centinela", join.table), sql.Identifier(join.name), sql.SQL(" AND ").join(on)))
    parts += [taken_join(item, scope) for item in taken]
    return sql.SQL(" ").join(parts)


def event_column(scope: Scope, ref: str, key: str) -> sql.Composable:
    alias, name, _ = scope.column(ref)
    if scope.table_of(alias).dates.get(name) != "evento":
        raise Refused("reloj", f"{key}: {ref} is not a date of an event, so dia cannot bound it")
    return sql.Identifier(alias, name)


def open_on_day(spec: Mapping[str, str], scope: Scope) -> list[sql.Composable]:
    start = event_column(scope, spec["desde"], "abierto_al_dia.desde")
    bounds = [sql.SQL("{} <= {}").format(start, scope.day)]
    end = spec["hasta"]
    if "." in end:
        alias, name, _ = scope.column(end)
        if scope.table_of(alias).dates.get(name) != "cierre":
            raise Refused("reloj", f"abierto_al_dia.hasta: {end} is not a date that closes a row")
        column = sql.Identifier(alias, name)
        return [*bounds, sql.SQL("({c} IS NULL OR {c} > {d})").format(c=column, d=scope.day)]
    closing = scope.source.closings.get(end)
    if closing is None:
        raise Refused("reloj", f"abierto_al_dia.hasta: {end} is neither a closing date nor a closing fuentes.yaml declares for {scope.source.name}")
    match = [sql.SQL("{} = {}").format(sql.Identifier(closing.name, child), sql.Identifier(scope.source.name, parent)) for child, parent in closing.on.items()]
    match.append(sql.SQL("{} <= {}").format(sql.Identifier(closing.name, closing.date), scope.day))
    exists = sql.SQL("NOT EXISTS (SELECT 1 FROM {} AS {} WHERE {})").format(
        sql.Identifier("centinela", closing.table), sql.Identifier(closing.name), sql.SQL(" AND ").join(match)
    )
    return [*bounds, exists]


def clock(block: Mapping[str, Any], scope: Scope) -> list[sql.Composable]:
    conditions = event_bounds(scope, scope.source.name)
    if scope.source.dated_by is not None:
        conditions += event_bounds(scope, scope.source.dated_by)
    if "ventana" in block:
        column = event_column(scope, block["ventana"]["columna"], "ventana")
        conditions.append(sql.SQL("{} > {} - {}").format(column, scope.day, sql.Literal(block["ventana"]["dias"])))
    if "abierto_al_dia" in block:
        conditions += open_on_day(block["abierto_al_dia"], scope)
    return conditions


def literal(value: Any, kind: str, ref: str) -> sql.Composable:
    if isinstance(value, bool) != (kind == "boolean") or not isinstance(value, LITERALS[kind]):
        raise Refused("lenguaje", f"filtro: {value!r} is not a {kind}, the type of {ref}")
    if kind == "date" and not is_date(value):
        raise Refused("lenguaje", f"filtro: {value!r} is not a date YYYY-MM-DD")
    return sql.Literal(value)


def is_date(value: str) -> bool:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def comparable(left: str, right: str) -> bool:
    return left == right or (left in NUMERIC and right in NUMERIC)


def against(spec: Mapping[str, Any], scope: Scope) -> sql.Composable:
    left, left_kind = scope.read(spec["columna"])
    right, right_kind = (scope.day, "date") if spec["contra"] == "dia" else scope.read(spec["contra"])
    if "menos_dias" in spec or "menos_meses" in spec:
        if right_kind != "date":
            raise Refused("lenguaje", f"filtro: {spec['contra']} is no date, so it has no days or months to subtract")
        back = DAYS_BACK if "menos_dias" in spec else MONTHS_BACK
        right = back.format(right, sql.Literal(spec.get("menos_dias", spec.get("menos_meses"))))
    if not comparable(left_kind, right_kind):
        raise Refused("lenguaje", f"filtro: {spec['columna']}, a {left_kind}, cannot be compared with {spec['contra']}, a {right_kind}")
    return COMPARE[spec["op"]].format(left, right)


def condition(spec: Mapping[str, Any], scope: Scope) -> sql.Composable:
    if "contra" in spec:
        return against(spec, scope)
    ref, operator, value = spec["columna"], spec["op"], spec["valor"]
    alias, name, kind = scope.column(ref)
    known = scope.table_of(alias).leaks.get(name)
    values = value if operator == "en" else [value]
    if known is not None and (operator not in ("=", "!=", "en") or not set(values) <= set(known)):
        raise Refused("fuente", f"filtro: {ref} holds the end of the dataset; only =, != or en on {list(known)} reads it")
    column = scope.raw(alias, name)
    if operator == "en":
        return sql.SQL("{} IN ({})").format(column, sql.SQL(", ").join(literal(item, kind, ref) for item in values))
    return COMPARE[operator].format(column, literal(value, kind, ref))


def operand(node: Any, scope: Scope) -> tuple[sql.Composable, str]:
    if node == "dia":
        return scope.day, "date"
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return sql.Literal(node), "integer" if isinstance(node, int) else "numeric"
    return scope.read(node)


def arithmetic(operator: str, left: sql.Composable, left_kind: str, right: sql.Composable, right_kind: str) -> tuple[sql.Composable, str]:
    if operator == "-" and left_kind == right_kind == "date":
        return sql.SQL("({} - {})").format(left, right), "integer"
    if left_kind in NUMERIC and right_kind in NUMERIC:
        return ARITH[operator].format(left, right), "numeric"
    raise Refused("lenguaje", f"{operator} does not apply to {left_kind} and {right_kind}")


def expression(node: Any, scope: Scope) -> tuple[sql.Composable, str]:
    if not isinstance(node, Mapping):
        return operand(node, scope)
    left, left_kind = expression(node["izq"], scope)
    right, right_kind = expression(node["der"], scope)
    return arithmetic(node["op"], left, left_kind, right, right_kind)


def measure(spec: Mapping[str, Any], scope: Scope) -> tuple[sql.Composable, str]:
    aggregate = spec["agregado"]
    if "de" in spec:
        expr, kind = expression(spec["de"], scope)
    else:
        expr, kind = sql.SQL("*"), "bigint"
    if aggregate in ("sum", "avg", "mediana") and kind not in NUMERIC:
        raise Refused("lenguaje", f"{aggregate} needs a number, and {spec['de']} is {kind}")
    if aggregate in ORDERED:
        call = AGGREGATE[aggregate].format(expr, event_column(scope, spec["por"], aggregate))
    else:
        call = AGGREGATE[aggregate].format(expr)
    if "si" in spec:
        call = FILTERED.format(call, sql.SQL(" AND ").join(condition(item, scope) for item in spec["si"]))
    if aggregate in ORDERED:
        return PICK[aggregate].format(call), kind
    if aggregate == "count":
        return call, "bigint"
    if aggregate == "sum" and "si" in spec:
        call = ZERO.format(call)
    if aggregate in ("min", "max"):
        return call, kind
    return AS_NUMERIC.format(call), "numeric"


def value(block: Mapping[str, Any], scope: Scope) -> tuple[sql.Composable, str]:
    if "medida" in block:
        return measure(block["medida"], scope)
    numerator, numerator_kind = measure(block["razon"]["numerador"], scope)
    denominator, denominator_kind = measure(block["razon"]["denominador"], scope)
    if numerator_kind not in NUMERIC or denominator_kind not in NUMERIC:
        raise Refused("lenguaje", "razon: both measures must be numbers")
    return sql.SQL("({}::numeric / NULLIF({}::numeric, 0))").format(numerator, denominator), "numeric"


def dimension(item: Any, scope: Scope) -> tuple[str, sql.Composable, str]:
    if isinstance(item, str):
        scope.column(item)
        if item not in scope.source.dimensions:
            raise Refused("fuente", f"agrupar: {item} is not a dimension fuentes.yaml declares for {scope.source.name}")
        expr, kind = scope.read(item)
        return item.partition(".")[2], expr, kind
    ref, period = item["columna"], item["por"]
    if scope.role(ref) not in ("evento", "plazo"):
        raise Refused("reloj", f"agrupar: {ref} is not a date of an event or a term, so it has no {period}")
    expr, _ = scope.read(ref)
    return period, TRUNC[period].format(expr), "date"


def output_names(block: Mapping[str, Any], dims: list) -> list[str]:
    names = [name for name, _, _ in dims] + list(block["salida"].values()) + list(block.get("columnas", {})) + list(block.get("derivadas", {}))
    if len(set(names)) != len(names) or RESERVED & set(names):
        raise Refused("lenguaje", f"agrupar, salida, columnas and derivadas name {names}: each output column needs a unique name other than dia or periodo")
    return names


def compile_kpi(block: Mapping[str, Any], sources: Sources, day: sql.Composable = sql.Placeholder("dia"), thresholds: Mapping[str, Any] | None = None) -> Compiled:
    check_block(block)
    return build(block, sources, sql.SQL("CAST({} AS date)").format(day), thresholds or {}, 0)


def build(block: Mapping[str, Any], sources: Sources, day: sql.Composable, thresholds: Mapping[str, Any], depth: int) -> Compiled:
    if depth > MAX_TAKEN_DEPTH:
        raise Refused("lenguaje", f"tomar nests at most {MAX_TAKEN_DEPTH} levels of KPIs")
    taken = [Taken(name, build(spec["kpi"], sources, day, {}, depth + 1), spec["por"]) for name, spec in block.get("tomar", {}).items()]
    scope, joins = scope_of(block, sources, day, taken)
    dims = [dimension(item, scope) for item in block["agrupar"]]
    output_names(block, dims)
    measured, kind = value(block, scope)
    extras = [(name, *measure(spec, scope), spec["agregado"]) for name, spec in block.get("columnas", {}).items()]
    conditions = clock(block, scope) + [condition(spec, scope) for spec in block.get("filtro", [])]
    source = from_clause(scope, joins, taken)
    if "linea_base" in block:
        core = baseline(block, scope, dims, measured, kind, extras, conditions, source)
    else:
        selected = [sql.SQL("{}::{} AS {}").format(expr, TYPES[k], sql.Identifier(name)) for name, expr, k in dims]
        selected.append(sql.SQL("{}::{} AS {}").format(measured, TYPES[kind], sql.Identifier(block["salida"]["valor"])))
        selected += [sql.SQL("{}::{} AS {}").format(expr, TYPES[k], sql.Identifier(name)) for name, expr, k, _ in extras]
        query = sql.SQL("SELECT {} {} WHERE {} GROUP BY {}").format(
            sql.SQL(", ").join(selected),
            source,
            sql.SQL(" AND ").join(conditions or [sql.SQL("TRUE")]),
            sql.SQL(", ").join(expr for _, expr, _ in dims),
        )
        columns = tuple((name, k) for name, _, k in dims) + ((block["salida"]["valor"], kind),) + tuple((name, k) for name, _, k, _ in extras)
        core = Compiled(query, columns, tuple(name for name, _, _ in dims))
    return finish(block, core, scope.day, thresholds)


def baseline(block, scope, dims, measured, kind, extras, conditions, source) -> Compiled:
    spec = block["linea_base"]
    if kind not in NUMERIC:
        raise Refused("lenguaje", "linea_base: the measure must be a number")
    if any(not isinstance(item, str) for item in block["agrupar"]):
        raise Refused("lenguaje", "linea_base groups by its own period; agrupar may not hold another")
    period = spec["periodo"]
    column = event_column(scope, spec["columna"], "linea_base")
    current = LAST[period].format(scope.day)
    bounds = [
        sql.SQL("{} >= {}").format(column, START[period].format(current, sql.Literal(spec["n"]))),
        sql.SQL("{} < {}").format(column, END[period].format(current)),
    ]
    truncated = TRUNC[period].format(column)
    inner = sql.SQL("SELECT {dims}, {period} AS periodo, {value} AS valor{extras} {source} WHERE {where} GROUP BY {group}").format(
        dims=sql.SQL(", ").join(sql.SQL("{} AS {}").format(expr, sql.Identifier(name)) for name, expr, _ in dims),
        period=truncated,
        value=measured,
        extras=sql.SQL("").join(sql.SQL(", {} AS {}").format(expr, sql.Identifier(name)) for name, expr, _, _ in extras),
        source=source,
        where=sql.SQL(" AND ").join(conditions + bounds),
        group=sql.SQL(", ").join([expr for _, expr, _ in dims] + [truncated]),
    )
    names = [name for name, _, _ in dims]
    same = sql.SQL(" AND ").join(
        sql.SQL("{} IS NOT DISTINCT FROM {}").format(sql.Identifier("periodos", name), sql.Identifier("entidades", name)) for name in names
    )
    filled = "medida" in block and block["medida"]["agregado"] in ZERO_WHEN_EMPTY
    out = block["salida"]
    value_now = sql.SQL("max(marco.valor) FILTER (WHERE marco.periodo = {})::numeric").format(current)
    base_before = sql.SQL("avg(marco.valor) FILTER (WHERE marco.periodo < {})::numeric").format(current)
    query = sql.SQL(
        "WITH periodos AS ({inner}), entidades AS (SELECT DISTINCT {entity} FROM periodos), "
        "marco AS (SELECT {framed}, serie.periodo, {fill} AS valor{extra_fill} "
        "FROM entidades CROSS JOIN (SELECT generate_series({first}, {current}, {step})::date AS periodo) AS serie "
        "LEFT JOIN periodos ON {same} AND periodos.periodo = serie.periodo) "
        "SELECT {dims}, {value_now} AS {valor}, {base_before} AS {base}, {delta} AS {delta_name}{extra_now} "
        "FROM marco GROUP BY {group}"
    ).format(
        inner=inner,
        entity=sql.SQL(", ").join(sql.Identifier(name) for name in names),
        framed=sql.SQL(", ").join(sql.Identifier("entidades", name) for name in names),
        fill=sql.SQL("coalesce(periodos.valor, 0)") if filled else sql.SQL("periodos.valor"),
        extra_fill=sql.SQL("").join(
            sql.SQL(", {} AS {}").format(ZERO.format(sql.Identifier("periodos", name)) if aggregate in ZERO_WHEN_EMPTY else sql.Identifier("periodos", name), sql.Identifier(name))
            for name, _, _, aggregate in extras
        ),
        same=same,
        first=START[period].format(current, sql.Literal(spec["n"])),
        current=current,
        step=STEP[period],
        dims=sql.SQL(", ").join(sql.SQL("{}::{} AS {}").format(sql.Identifier("marco", name), TYPES[k], sql.Identifier(name)) for name, _, k in dims),
        value_now=value_now,
        valor=sql.Identifier(out["valor"]),
        base_before=base_before,
        base=sql.Identifier(out["base"]),
        delta=DELTA[spec["salida"]].format(valor=value_now, base=base_before),
        delta_name=sql.Identifier(out["delta"]),
        extra_now=sql.SQL("").join(
            sql.SQL(", max({}) FILTER (WHERE marco.periodo = {})::{} AS {}").format(sql.Identifier("marco", name), current, TYPES[k], sql.Identifier(name))
            for name, _, k, _ in extras
        ),
        group=sql.SQL(", ").join(sql.Identifier("marco", name) for name in names),
    )
    columns = tuple((name, k) for name, _, k in dims) + ((out["valor"], "numeric"), (out["base"], "numeric"), (out["delta"], "numeric")) + tuple((name, k) for name, _, k, _ in extras)
    return Compiled(query, columns, tuple(name for name, _, _ in dims))


def threshold(name: str, available: Mapping[str, tuple[sql.Composable, str]], thresholds: Mapping[str, Any]) -> tuple[sql.Composable, str]:
    spec = thresholds.get(name)
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        return sql.Literal(spec), "numeric"
    if isinstance(spec, Mapping) and "columna" in spec and spec["columna"] in available:
        return available[spec["columna"]]
    if isinstance(spec, Mapping) and "por" in spec and spec["por"] in available:
        cases = sql.SQL(" ").join(WHEN_VALUE.format(sql.Literal(key), sql.Literal(number)) for key, number in spec["valores"].items())
        return BY_VALUE.format(available[spec["por"]][0], cases), "numeric"
    raise Refused("lenguaje", f"derivadas: umbral {name} names no numeric threshold of this KPI's umbrales over its own columns")


def unify(left: str, right: str, key: str) -> str:
    if left == right:
        return left
    if {left, right} == {"integer", "bigint"}:
        return "bigint"
    if left in NUMERIC and right in NUMERIC:
        return "numeric"
    raise Refused("lenguaje", f"derivadas: {key} mixes a {left} with a {right}")


def derived(node: Any, available: Mapping[str, tuple[sql.Composable, str]], day: sql.Composable, thresholds: Mapping[str, Any], frame: tuple[tuple[str, ...], tuple[str, ...]], depth: int = 1) -> tuple[sql.Composable, str]:
    if isinstance(node, Mapping) and depth > MAX_DERIVED_DEPTH:
        raise Refused("lenguaje", f"derivadas nest at most {MAX_DERIVED_DEPTH} operations")
    if node == "dia":
        return day, "date"
    if isinstance(node, str):
        if node not in available:
            raise Refused("lenguaje", f"derivadas: {node} is no column this KPI outputs before it")
        return available[node]
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return sql.Literal(node), "integer" if isinstance(node, int) else "numeric"
    inner = lambda child: derived(child, available, day, thresholds, frame, depth + 1)
    if "umbral" in node:
        return threshold(node["umbral"], available, thresholds)
    if "op" in node:
        left, left_kind = inner(node["izq"])
        right, right_kind = inner(node["der"])
        return arithmetic(node["op"], left, left_kind, right, right_kind)
    if "mayor" in node or "menor" in node:
        key = "mayor" if "mayor" in node else "menor"
        (left, left_kind), (right, right_kind) = (inner(item) for item in node[key])
        return GREATEST[key].format(left, right), unify(left_kind, right_kind, key)
    if "dias_habiles" in node:
        (start, start_kind), (end, end_kind) = inner(node["dias_habiles"]["desde"]), inner(node["dias_habiles"]["hasta"])
        if start_kind != "date" or end_kind != "date":
            raise Refused("lenguaje", "derivadas: dias_habiles counts the days between two dates")
        return BUSINESS_DAYS.format(start, end), "integer"
    if "compara" in node:
        spec = node["compara"]
        (left, left_kind), (right, right_kind) = inner(spec["izq"]), inner(spec["der"])
        if not comparable(left_kind, right_kind):
            raise Refused("lenguaje", f"derivadas: compara cannot compare a {left_kind} with a {right_kind}")
        return COMPARE[spec["op"]].format(left, right), "boolean"
    if "existe" in node:
        return EXISTS.format(inner(node["existe"])[0]), "boolean"
    if "participacion" in node:
        share, kind = inner(node["participacion"])
        if kind not in NUMERIC:
            raise Refused("lenguaje", "derivadas: participacion needs a number")
        return SHARE.format(x=share), "numeric"
    if "periodo_anterior" in node:
        return previous(node["periodo_anterior"], available, frame)
    spec = node["si"]
    when, when_kind = inner(spec["cuando"])
    if when_kind != "boolean":
        raise Refused("lenguaje", "derivadas: si needs cuando to be a comparison or existe")
    (then, then_kind), (otherwise, otherwise_kind) = inner(spec["entonces"]), inner(spec["sino"])
    return WHEN.format(when, then, otherwise), unify(then_kind, otherwise_kind, "si")


def previous(name: str, available: Mapping[str, tuple[sql.Composable, str]], frame: tuple[tuple[str, ...], tuple[str, ...]]) -> tuple[sql.Composable, str]:
    periods, others = frame
    if len(periods) != 1:
        raise Refused("lenguaje", "derivadas: periodo_anterior needs agrupar to hold exactly one {columna, por}")
    if name not in available:
        raise Refused("lenguaje", f"derivadas: {name} is no column this KPI outputs before it")
    partition = PARTITION.format(sql.SQL(", ").join(sql.Identifier("nucleo", other) for other in others)) if others else sql.SQL("")
    period = periods[0]
    return PREVIOUS.format(x=available[name][0], partition=partition, period=sql.Identifier("nucleo", period), step=STEP[period]), available[name][1]


def finish(block: Mapping[str, Any], core: Compiled, day: sql.Composable, thresholds: Mapping[str, Any]) -> Compiled:
    available = {name: (sql.Identifier("nucleo", name), kind) for name, kind in core.columns}
    periods = tuple(item["por"] for item in block["agrupar"] if not isinstance(item, str))
    frame = (periods, tuple(name for name in core.entity if name not in periods))
    columns = list(core.columns)
    for name, node in block.get("derivadas", {}).items():
        available[name] = derived(node, available, day, thresholds, frame)
        columns.append((name, available[name][1]))
    places = block.get("decimales", {})
    for name in places:
        if name in core.entity or name not in available or available[name][1] not in NUMERIC:
            raise Refused("lenguaje", f"decimales: {name} is no numeric output column of this KPI")
    selected = []
    for name, kind in columns:
        expr = available[name][0]
        if name in places:
            expr, kind = ROUND.format(expr, sql.Literal(places[name])), "numeric"
        selected.append(sql.SQL("{}::{} AS {}").format(expr, TYPES[kind], sql.Identifier(name)))
    columns = [(name, "numeric" if name in places else kind) for name, kind in columns]
    query = sql.SQL("SELECT {} FROM ({}) AS nucleo").format(sql.SQL(", ").join(selected), core.query)
    kinds = dict(columns)
    having = []
    for spec in block.get("tener", []):
        if kinds.get(spec["columna"]) not in NUMERIC:
            raise Refused("lenguaje", f"tener: {spec['columna']} is no numeric output column of this KPI")
        having.append(COMPARE[spec["op"]].format(sql.Identifier("kpi", spec["columna"]), sql.Literal(spec["valor"])))
    if having:
        query = sql.SQL("SELECT * FROM ({}) AS kpi WHERE {}").format(query, sql.SQL(" AND ").join(having))
    return Compiled(query, tuple(columns), core.entity)


def function_definition(metric: str, block: Mapping[str, Any], sources: Sources, thresholds: Mapping[str, Any] | None = None) -> sql.Composable:
    if NAME.match(metric) is None:
        raise Refused("lenguaje", f"{metric} is not a metric name of lowercase letters, digits and underscores")
    compiled = compile_kpi(block, sources, day=sql.SQL("dia"), thresholds=thresholds)
    function = sql.Identifier("centinela", f"k_{metric}")
    returns = sql.SQL(", ").join(sql.SQL("{} {}").format(sql.Identifier(name), TYPES[kind]) for name, kind in compiled.columns)
    return sql.SQL(
        "DROP FUNCTION IF EXISTS {fn}(date);\n"
        "CREATE FUNCTION {fn}(dia date) RETURNS TABLE ({returns}) LANGUAGE sql STABLE SECURITY DEFINER "
        "SET search_path = pg_catalog, pg_temp AS {body};\n"
        "ALTER FUNCTION {fn}(date) OWNER TO centinela_propietario;\n"
        "REVOKE ALL ON FUNCTION {fn}(date) FROM PUBLIC;\n"
        "GRANT EXECUTE ON FUNCTION {fn}(date) TO centinela_lector;\n"
    ).format(fn=function, returns=returns, body=sql.Literal(compiled.query.as_string()))
```

- [ ] **Step 6: Declare the closing and hand the thresholds to the compiler**

In `data/kernel/fuentes.yaml`, under `fuentes:` → `pedidos_detalle:`, add the closing between `fechada_por: pedidos` and `uniones:`:

```yaml
  pedidos_detalle:
    fechada_por: pedidos
    cierres:
      facturada: { tabla: facturas, por: { pedido_id: pedido_id }, fecha: fecha_factura }
    uniones:
```

In `packages/tools/centinela_tools/tools.py:catalogue_of`, replace

```python
        compiled = compile_kpi(entry["kernel"], sources)
```

with

```python
        compiled = compile_kpi(entry["kernel"], sources, thresholds=entry.get("umbrales"))
```

In `packages/tools/centinela_tools/generate.py:render`, replace

```python
        estimated = cost(compile_kpi(entry["kernel"], sources).query)
```

with

```python
        estimated = cost(compile_kpi(entry["kernel"], sources, thresholds=entry.get("umbrales")).query)
```

and

```python
        parts.append(function_definition(metric, entry["kernel"], sources).as_string())
```

with

```python
        parts.append(function_definition(metric, entry["kernel"], sources, entry.get("umbrales")).as_string())
```

- [ ] **Step 7: Adjust the existing tests to the grown language**

`packages/tools/tests/test_language.py`: the bound of an expression is now depth three, so the planted violation is depth four. Replace

```python
        pytest.param(with_(lambda b: b.update(medida={"agregado": "sum", "de": op(op(op(COL, COL), COL), COL)})), "medida/de", id="expression-depth-three"),
```

with

```python
        pytest.param(with_(lambda b: b.update(medida={"agregado": "sum", "de": op(op(op(op(COL, COL), COL), COL), COL)})), "medida/de", id="expression-depth-four"),
```

`packages/tools/tests/test_compiler.py`: in `test_a_function_reads_its_argument_and_belongs_to_the_owner_role`, replace

```python
    assert definition.startswith('CREATE OR REPLACE FUNCTION "centinela"."k_oc_abiertas"(dia date) RETURNS TABLE ("proveedor_id" text, "ordenes_abiertas" bigint)')
```

with

```python
    assert definition.startswith('DROP FUNCTION IF EXISTS "centinela"."k_oc_abiertas"(date);\nCREATE FUNCTION "centinela"."k_oc_abiertas"(dia date) RETURNS TABLE ("proveedor_id" text, "ordenes_abiertas" bigint)')
```

and in `test_freezing_keeps_the_text_its_hash_and_the_compiler_version`, replace `frozen.compiler_version == "1"` with `frozen.compiler_version == "2"`.

`packages/tools/tests/test_sources.py`: a closing may now match the table that dates its source. Replace the whole function `test_every_closing_reads_a_child_that_references_its_source` with:

```python
def test_every_closing_reads_a_child_that_references_its_source_or_the_table_that_dates_it():
    for source in SOURCES.sources.values():
        dating = source.joins[source.dated_by].table if source.dated_by else None
        for closing in source.closings.values():
            for child_column, parent_column in closing.on.items():
                target = SCHEMA[closing.table].references.get(child_column)
                assert target == source.name or (target == dating and SCHEMA[source.name].references.get(parent_column) == dating), f"{source.name}.{closing.name}"
```

`packages/tools/tests/test_generate.py`: the committed file now holds functions, and the cost does not change what is written. Replace

```python
def no_database(query):
    raise AssertionError("no entry of data/metricas.yaml carries kernel:, so no cost is estimated")
```

with

```python
def no_database(query):
    raise AssertionError("an empty metricas.yaml estimates no cost")


def any_cost(query):
    return 0.0
```

then, in `test_the_committed_file_is_what_the_generator_writes`, replace `view_names(SQL_DIR), no_database, Settings())` with `view_names(SQL_DIR), any_cost, Settings())`; in `test_the_file_opens_with_its_banner_and_grants_column_by_column`, replace `assert "CREATE OR REPLACE FUNCTION" not in text` with `assert "CREATE FUNCTION" not in text`; and in `test_a_fixture_kpi_becomes_a_function`, replace `text.count("CREATE OR REPLACE FUNCTION") == 3` with `text.count("CREATE FUNCTION") == 3`.

- [ ] **Step 8: Run the tests that need no database**

Run: `cd packages/tools && uv run pytest -q`
Expected: every test passes except `tests/test_generate.py::test_the_committed_file_is_what_the_generator_writes`, which fails because `data/sql/05_kpis.generated.sql` still holds no function. The `db` tests are skipped with their reason.

- [ ] **Step 9: Regenerate the file against the scratch database**

Start the scratch database if `docker ps` does not list `centinela-kernel-test`, with the command of `packages/tools/AGENTS.md` § "Commands", and wait until its load check prints a number. Then:

Run: `cd packages/tools && CENTINELA_DSN=postgresql://centinela:centinela@localhost:55432/centinela uv run python -m centinela_tools.generate && grep -c '^CREATE FUNCTION' ../../data/sql/05_kpis.generated.sql`
Expected: `10`, and no `costo` refusal. The planner's costs measured while writing this plan were at most 339131 (`dias_pago_prom`, about 300 ms on the scratch database), under the cap of 1000000.

- [ ] **Step 10: Run the tests that need no database again**

Run: `cd packages/tools && uv run pytest -q`
Expected: every test passes; the `db` tests are skipped.

- [ ] **Step 11: Ask the user, then commit**

```bash
git add data/metricas.yaml data/kernel/ data/sql/05_kpis.generated.sql packages/tools/centinela_tools/ packages/tools/tests/
git commit -q -F - <<'MSG'
Build every current metric as a kernel KPI, growing the language by the measures their thresholds and pesos at risk need

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 3: Parity in two halves, against the scratch database

**Files:**
- Modify: `packages/tools/tests/conftest.py`
- Create: `packages/tools/tests/test_parity.py`

**Interfaces:**
- Consumes: the base KPIs of Task 2, `compiler.BUSINESS_DAYS`, `tools.catalogue_of`, `tools.kpi_consultar(kpi_id, day, catalogue, connect, settings)`, `tools.plain(row)`, the fixtures `connect` and `superuser` of `conftest.py`.
- Produces: the `KER-` cases, one test per metric and day, which Task 5 names on `evals/AGENTS.md`.

- [ ] **Step 1: Apply the real KPIs in every `db` session**

In `packages/tools/tests/conftest.py`, replace

```python
from centinela_tools.paths import SQL_DIR
```

with

```python
from centinela_tools.paths import METRICAS, SQL_DIR
```

add `from centinela_tools.tools import load_entries` after `from centinela_tools.sources import load_sources`, and in the fixture `applied`, replace

```python
        conn.execute(render(load_sources(), fixture_entries(), view_names(SQL_DIR), lambda query: 0.0, Settings()))
```

with

```python
        conn.execute(render(load_sources(), {**load_entries(METRICAS), **fixture_entries()}, view_names(SQL_DIR), lambda query: 0.0, Settings()))
```

Also change the header's last line from `# roles, the grants and the fixture KPIs of tests/fixtures/metricas.yaml, as the generator writes them.` to `# roles, the grants, the base KPIs of data/metricas.yaml and the fixture KPIs, as the generator writes them.`

- [ ] **Step 2: Write the parity tests**

Create `packages/tools/tests/test_parity.py`:

```python
# Parity of every base KPI of data/metricas.yaml, in two halves. On fecha_corte() the kit's views are
# right by definition, so each KPI returns its view's rows, value for value, on the columns the view
# holds. On earlier simulated days the views leak, so each KPI agrees with a hand-written as-of query
# here, never with the view. Each test is one KER- case of evals/AGENTS.md. margen_pct and
# dias_pago_prom are compared on the entities measured in the current period, because no view or
# as-of query holds a row for a week or a month with no sale or payment. descuento_en_exceso agrees
# with its view within half a peso per line, because the kit rounds each line and the kernel rounds
# the week's sum. dias_pago_prom has no view half: it measures by month of payment, and its view by
# month of invoice, whose last months hold only the invoices already paid.
from datetime import date
from decimal import Decimal

import pytest
from psycopg import sql
from psycopg.rows import dict_row

from centinela_tools.compiler import BUSINESS_DAYS
from centinela_tools.paths import METRICAS
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_consultar, load_entries, plain

pytestmark = pytest.mark.db
ENTRIES = load_entries(METRICAS)
CATALOGUE = catalogue_of(ENTRIES, load_sources())
DAYS = [date(2025, 12, 15), date(2026, 4, 8), date(2026, 9, 15)]
WEEK = "date_trunc('week', %(d)s::date - 6)::date"
MONTH = "(date_trunc('month', %(d)s::date + 1) - interval '1 month')::date"
OPEN = "f.fecha_factura <= %(d)s AND NOT EXISTS (SELECT 1 FROM centinela.pagos pg WHERE pg.factura_id = f.factura_id AND pg.fecha_pago <= %(d)s)"
SOLD = "FROM centinela.pedidos_detalle dd JOIN centinela.pedidos p USING (pedido_id) WHERE p.estado <> 'Cancelado' AND p.fecha <= %(d)s"

VIEWS = {
    "margen_pct": f"SELECT linea, margen_pct, ventas FROM centinela.v_margen_semanal_linea WHERE semana = {WEEK}",
    "saldo_vencido": "SELECT cliente_id, saldo_vencido, saldo_abierto, max_dias_vencido, cupo_credito FROM centinela.v_cartera_cliente WHERE saldo_abierto > 0",
    "concentracion_vencida_pct": (
        "SELECT cliente_id, saldo_vencido, round(100 * saldo_vencido / sum(saldo_vencido) OVER (), 2) AS concentracion_vencida_pct "
        "FROM centinela.v_cartera_cliente WHERE saldo_abierto > 0"
    ),
    "cobertura_dias": "SELECT sku, bodega_id, demanda_prom_30d, existencia, clase_abc, cobertura_dias FROM centinela.v_cobertura_inventario",
    "variacion_costo_pct": "SELECT sku, costo_unitario, costo_anterior, fecha_vigencia, variacion_pct FROM centinela.v_costo_sku WHERE vigente",
    "dias_retraso": "SELECT oc_id, fecha_recibida, fecha_esperada, recibida, dias_retraso FROM centinela.v_ordenes_compra",
    "margen_bruto_negativo": "SELECT pedido_id, linea_n, margen_bruto, sku, fecha FROM centinela.v_ventas WHERE margen_bruto < 0",
    "veces_intervalo_habitual": "SELECT cliente_id, pedidos, ultima_compra, intervalo_prom_dias, dias_sin_comprar, veces_intervalo_habitual FROM centinela.v_actividad_cliente",
}

AS_OF = {
    "margen_pct": (
        "WITH semanas AS (SELECT pr.linea, date_trunc('week', p.fecha)::date AS semana, "
        "100 * sum(dd.valor_neto - dd.cantidad * dd.costo_unitario) / nullif(sum(dd.valor_neto), 0) AS margen, sum(dd.valor_neto) AS ventas "
        f"{SOLD.replace('USING (pedido_id)', 'USING (pedido_id) JOIN centinela.productos pr USING (sku)')} "
        f"AND p.fecha >= {WEEK} - 56 AND p.fecha < {WEEK} + 7 GROUP BY 1, 2), "
        f"actual AS (SELECT linea, margen, ventas FROM semanas WHERE semana = {WEEK}), "
        f"previa AS (SELECT linea, avg(margen) AS base FROM semanas WHERE semana < {WEEK} GROUP BY 1), "
        "trimestre AS (SELECT pr.linea, sum(dd.valor_neto) / 3 AS mes "
        f"{SOLD.replace('USING (pedido_id)', 'USING (pedido_id) JOIN centinela.productos pr USING (sku)')} AND p.fecha > %(d)s::date - 90 GROUP BY 1) "
        "SELECT a.linea, round(a.margen, 2) AS margen_pct, round(b.base, 2) AS margen_pct_base, round(b.base - a.margen, 2) AS caida_pts, "
        "a.ventas, m.margen_minimo_pct, round(t.mes, 0) AS ventas_mes_prom, "
        "round((greatest(b.base, m.margen_minimo_pct) - a.margen) / 100 * a.ventas, 0) AS pesos_en_riesgo "
        "FROM actual a LEFT JOIN previa b USING (linea) JOIN centinela.ref_margen_minimo_linea m USING (linea) LEFT JOIN trimestre t USING (linea)"
    ),
    "saldo_vencido": (
        "SELECT f.cliente_id, coalesce(sum(f.valor_total) FILTER (WHERE f.fecha_vencimiento < %(d)s), 0) AS saldo_vencido, "
        "sum(f.valor_total) AS saldo_abierto, max(%(d)s::date - f.fecha_vencimiento) AS max_dias_vencido, max(c.cupo_credito) AS cupo_credito, "
        "coalesce(sum(f.valor_total) FILTER (WHERE f.fecha_vencimiento < %(d)s), 0) AS pesos_en_riesgo "
        f"FROM centinela.facturas f JOIN centinela.clientes c USING (cliente_id) WHERE {OPEN} GROUP BY 1"
    ),
    "concentracion_vencida_pct": (
        "WITH s AS (SELECT f.cliente_id, coalesce(sum(f.valor_total) FILTER (WHERE f.fecha_vencimiento < %(d)s), 0) AS v "
        f"FROM centinela.facturas f WHERE {OPEN} GROUP BY 1) "
        "SELECT cliente_id, v AS saldo_vencido, round(100 * v / nullif(sum(v) OVER (), 0), 2) AS concentracion_vencida_pct, v AS pesos_en_riesgo FROM s"
    ),
    "dias_pago_prom": (
        "WITH meses AS (SELECT f.cliente_id, date_trunc('month', pg.fecha_pago)::date AS mes, avg(pg.fecha_pago - f.fecha_factura) AS dias "
        "FROM centinela.pagos pg JOIN centinela.facturas f USING (factura_id) "
        f"WHERE f.fecha_factura <= %(d)s AND pg.fecha_pago >= ({MONTH} - interval '12 months')::date AND pg.fecha_pago < ({MONTH} + interval '1 month')::date GROUP BY 1, 2), "
        f"actual AS (SELECT cliente_id, dias FROM meses WHERE mes = {MONTH}), "
        f"previa AS (SELECT cliente_id, avg(dias) AS base FROM meses WHERE mes < {MONTH} GROUP BY 1), "
        f"cartera AS (SELECT f.cliente_id, sum(f.valor_total) AS saldo FROM centinela.facturas f WHERE {OPEN} GROUP BY 1) "
        "SELECT a.cliente_id, round(a.dias, 1) AS dias_pago_prom, round(b.base, 1) AS dias_pago_prom_base, "
        "round(100 * (a.dias / nullif(b.base, 0) - 1), 2) AS aumento_pct, c.saldo AS pesos_en_riesgo "
        "FROM actual a LEFT JOIN previa b USING (cliente_id) LEFT JOIN cartera c USING (cliente_id)"
    ),
    "cobertura_dias": (
        "WITH inv AS (SELECT sku, bodega_id, avg(salidas) AS dem, (array_agg(existencia_final ORDER BY fecha DESC))[1] AS ex "
        "FROM centinela.inventario_diario WHERE fecha > %(d)s::date - 30 AND fecha <= %(d)s GROUP BY 1, 2), "
        "precio AS (SELECT DISTINCT ON (sku) sku, precio_lista FROM centinela.lista_precios WHERE fecha_vigencia <= %(d)s ORDER BY sku, fecha_vigencia DESC), "
        "pend AS (SELECT dd.sku, count(*) AS n FROM centinela.pedidos_detalle dd JOIN centinela.pedidos p USING (pedido_id) "
        "WHERE p.estado <> 'Cancelado' AND p.fecha <= %(d)s AND NOT EXISTS "
        "(SELECT 1 FROM centinela.facturas f WHERE f.pedido_id = p.pedido_id AND f.fecha_factura <= %(d)s) GROUP BY 1) "
        "SELECT inv.sku, inv.bodega_id, round(inv.dem, 1) AS demanda_prom_30d, inv.ex AS existencia, pr.clase_abc, precio.precio_lista, "
        "round(inv.ex / nullif(inv.dem, 0), 1) AS cobertura_dias, coalesce(pend.n, 0) AS pedidos_pendientes, "
        "round(inv.dem * (CASE pr.clase_abc WHEN 'A' THEN %(a)s WHEN 'B' THEN %(b)s END - inv.ex / nullif(inv.dem, 0)) * precio.precio_lista, 0) AS pesos_en_riesgo "
        "FROM inv JOIN centinela.productos pr USING (sku) LEFT JOIN precio USING (sku) LEFT JOIN pend USING (sku)"
    ),
    "variacion_costo_pct": (
        "WITH c AS (SELECT sku, (array_agg(costo_unitario ORDER BY fecha_vigencia DESC))[1] AS cu, "
        "(array_agg(costo_unitario ORDER BY fecha_vigencia DESC))[2] AS ca, max(fecha_vigencia) AS fv "
        "FROM centinela.costos_proveedor WHERE fecha_vigencia <= %(d)s GROUP BY 1), "
        "lp AS (SELECT sku, max(fecha_vigencia) AS cambio, (array_agg(precio_lista ORDER BY fecha_vigencia DESC))[1] AS precio "
        "FROM centinela.lista_precios WHERE fecha_vigencia <= %(d)s GROUP BY 1), "
        "v AS (SELECT dd.sku, coalesce(sum(dd.cantidad) FILTER (WHERE p.fecha >= c.fv), 0) AS desde, "
        "coalesce(sum(dd.cantidad) FILTER (WHERE p.fecha > %(d)s::date - 90), 0) AS n90 "
        f"{SOLD.replace('USING (pedido_id)', 'USING (pedido_id) LEFT JOIN c USING (sku)')} GROUP BY 1), "
        "habiles AS (SELECT c.sku, count(g.dia) FILTER (WHERE extract(isodow FROM g.dia) BETWEEN 1 AND 5) AS n "
        "FROM c LEFT JOIN LATERAL generate_series(c.fv + 1, %(d)s::date, interval '1 day') AS g(dia) ON TRUE GROUP BY 1) "
        "SELECT c.sku, c.cu AS costo_unitario, c.ca AS costo_anterior, c.fv AS fecha_vigencia, lp.precio AS precio_lista, "
        "round(100 * (c.cu / nullif(c.ca, 0) - 1), 2) AS variacion_pct, "
        "CASE WHEN lp.cambio >= c.fv THEN 0 ELSE h.n END AS dias_habiles_sin_traslado, "
        "round((c.cu - c.ca) * v.desde, 0) AS pesos_en_riesgo, round(v.n90 / 3.0, 1) AS unidades_mes_prom "
        "FROM c LEFT JOIN lp USING (sku) LEFT JOIN v USING (sku) JOIN habiles h USING (sku)"
    ),
    "dias_retraso": (
        "SELECT oc_id, CASE WHEN fecha_recibida <= %(d)s THEN fecha_recibida END AS fecha_recibida, fecha_esperada, "
        "coalesce(fecha_recibida <= %(d)s, false) AS recibida, "
        "CASE WHEN fecha_recibida <= %(d)s THEN greatest(fecha_recibida - fecha_esperada, 0) ELSE greatest(%(d)s::date - fecha_esperada, 0) END AS dias_retraso, "
        "cantidad * costo_unitario AS pesos_en_riesgo FROM centinela.ordenes_compra WHERE fecha_oc <= %(d)s"
    ),
    "descuento_en_exceso": (
        "WITH s AS (SELECT p.vendedor_id, date_trunc('week', p.fecha)::date AS semana, "
        "sum(dd.cantidad * dd.precio_unitario * (dd.descuento_pct - t.tope_descuento_pct) / 100) AS e "
        "FROM centinela.pedidos_detalle dd JOIN centinela.pedidos p USING (pedido_id) JOIN centinela.clientes c ON c.cliente_id = p.cliente_id "
        "JOIN centinela.ref_topes_descuento t ON t.segmento = c.segmento "
        "WHERE p.estado <> 'Cancelado' AND p.fecha <= %(d)s AND dd.aprobacion_especial = 'N' AND dd.descuento_pct > t.tope_descuento_pct GROUP BY 1, 2) "
        "SELECT a.vendedor_id, a.semana, round(a.e, 0) AS descuento_en_exceso, round(b.e, 0) AS exceso_semana_anterior, round(a.e, 0) AS pesos_en_riesgo "
        "FROM s a LEFT JOIN s b ON b.vendedor_id = a.vendedor_id AND b.semana = a.semana - 7"
    ),
    "margen_bruto_negativo": (
        "SELECT dd.pedido_id, dd.linea_n, dd.valor_neto - dd.cantidad * dd.costo_unitario AS margen_bruto, dd.sku, p.fecha, "
        f"dd.cantidad * dd.costo_unitario - dd.valor_neto AS pesos_en_riesgo {SOLD} AND dd.valor_neto - dd.cantidad * dd.costo_unitario < 0"
    ),
    "veces_intervalo_habitual": (
        "WITH c AS (SELECT cliente_id, count(*) AS n, max(fecha) AS u, min(fecha) AS f FROM centinela.pedidos "
        "WHERE estado <> 'Cancelado' AND fecha <= %(d)s GROUP BY 1), "
        "s AS (SELECT p.cliente_id, coalesce(sum(dd.valor_neto) FILTER (WHERE p.fecha > (c.u - interval '6 months')::date), 0) / 6 AS mes "
        f"{SOLD.replace('USING (pedido_id)', 'USING (pedido_id) JOIN c ON c.cliente_id = p.cliente_id')} GROUP BY 1) "
        "SELECT c.cliente_id, c.n AS pedidos, c.u AS ultima_compra, round((c.u - c.f)::numeric / nullif(c.n - 1, 0), 1) AS intervalo_prom_dias, "
        "%(d)s::date - c.u AS dias_sin_comprar, round((%(d)s::date - c.u) / nullif((c.u - c.f)::numeric / nullif(c.n - 1, 0), 0), 1) AS veces_intervalo_habitual, "
        "round(s.mes, 0) AS pesos_en_riesgo FROM c LEFT JOIN s USING (cliente_id)"
    ),
}

MEASURED = {"margen_pct": "margen_pct", "dias_pago_prom": "dias_pago_prom"}


def parameters(day):
    classes = ENTRIES["cobertura_dias"]["umbrales"]["cobertura_dias"]["valores"]
    return {"d": day, "a": classes["A"], "b": classes["B"]}


def expected(superuser, query, day, entity):
    with superuser.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, parameters(day))
        rows = [plain(row) for row in cursor.fetchall()]
    return {tuple(row[name] for name in entity): row for row in rows}


def measured(connect, metric, day):
    entity = CATALOGUE.kpis[metric].entity
    rows = kpi_consultar(metric, day, CATALOGUE, connect, Settings())["filas"]
    column = MEASURED.get(metric)
    return {tuple(row[name] for name in entity): row for row in rows if column is None or row[column] is not None}, entity


def close(left, right, tolerance):
    if isinstance(left, (int, float, Decimal)) and isinstance(right, (int, float, Decimal)) and not isinstance(left, bool):
        return abs(float(left) - float(right)) <= tolerance
    return left == right


def agree(kernel, reference, tolerance=1e-9):
    assert set(kernel) == set(reference), sorted(set(kernel) ^ set(reference))[:5]
    for key, row in reference.items():
        for column, value in row.items():
            assert close(kernel[key][column], value, tolerance), (key, column, kernel[key][column], value)


def cut(superuser):
    return superuser.execute("SELECT centinela.fecha_corte()").fetchone()[0]


def test_every_metric_of_metricas_yaml_is_a_base_kpi():
    assert set(CATALOGUE.kpis) == set(ENTRIES)
    assert set(AS_OF) == set(ENTRIES) and set(VIEWS) | {"descuento_en_exceso", "dias_pago_prom"} == set(ENTRIES)


@pytest.mark.parametrize("metric", sorted(VIEWS))
def test_a_kpi_returns_its_views_rows_on_fecha_corte(connect, superuser, metric):
    day = cut(superuser)
    kernel, entity = measured(connect, metric, day)
    agree(kernel, expected(superuser, VIEWS[metric], day, entity))


def test_descuento_en_exceso_agrees_with_its_view_within_half_a_peso_per_line(connect, superuser):
    day = cut(superuser)
    kernel, entity = measured(connect, "descuento_en_exceso", day)
    view = expected(
        superuser,
        "SELECT vendedor_id, date_trunc('week', fecha)::date AS semana, sum(descuento_en_exceso) AS descuento_en_exceso, count(*) AS lineas "
        "FROM centinela.v_descuentos_fuera_politica GROUP BY 1, 2",
        day,
        entity,
    )
    assert set(kernel) == set(view)
    for key, row in view.items():
        assert close(kernel[key]["descuento_en_exceso"], row["descuento_en_exceso"], 0.5 * row["lineas"]), key


@pytest.mark.parametrize("day", DAYS, ids=str)
@pytest.mark.parametrize("metric", sorted(AS_OF))
def test_a_kpi_agrees_with_an_as_of_query_on_an_earlier_day(connect, superuser, metric, day):
    kernel, entity = measured(connect, metric, day)
    agree(kernel, expected(superuser, AS_OF[metric], day, entity))


@pytest.mark.parametrize("metric", sorted(AS_OF))
def test_every_kpi_returns_rows_on_some_as_of_day(connect, metric):
    assert any(measured(connect, metric, day)[0] for day in DAYS), f"{metric} returns no row on {DAYS}, so its as-of check proves nothing"


@pytest.mark.parametrize("metric", sorted(ENTRIES))
def test_every_base_kpi_outputs_pesos_en_riesgo(metric):
    assert "pesos_en_riesgo" in dict(CATALOGUE.kpis[metric].columns)


def test_cobertura_dias_outputs_the_orders_pending_on_the_day():
    assert dict(CATALOGUE.kpis["cobertura_dias"].columns)["pedidos_pendientes"] in ("bigint", "integer")


@pytest.mark.parametrize("metric", sorted(ENTRIES))
def test_a_day_before_the_dataset_returns_no_rows(connect, metric):
    assert kpi_consultar(metric, date(2025, 9, 30), CATALOGUE, connect, Settings())["filas"] == []


def test_a_customer_with_one_order_has_no_interval_and_raises_nothing(connect):
    rows = kpi_consultar("veces_intervalo_habitual", date(2025, 10, 2), CATALOGUE, connect, Settings())["filas"]
    single = [row for row in rows if row["pedidos"] == 1]
    assert single and all(row["intervalo_prom_dias"] is None and row["veces_intervalo_habitual"] is None for row in single)


@pytest.mark.parametrize(
    "start, end, days",
    [(date(2026, 2, 13), date(2026, 2, 27), 10), (date(2026, 2, 13), date(2026, 3, 2), 11), (date(2026, 2, 13), date(2026, 2, 13), 0), (date(2026, 2, 14), date(2026, 2, 15), 0)],
)
def test_business_days_count_monday_to_friday_after_the_start(superuser, start, end, days):
    assert superuser.execute(sql.SQL("SELECT {}").format(BUSINESS_DAYS.format(sql.Literal(start), sql.Literal(end)))).fetchone()[0] == days
```

- [ ] **Step 3: Run them**

Run: `cd packages/tools && CENTINELA_TEST_DSN=postgresql://centinela:centinela@localhost:55432/centinela uv run pytest tests/test_parity.py -q`
Expected: every test passes. A failure names the key, the column, the kernel's value and the reference's; the defect is in the `kernel:` block or the compiler (Global Constraints).

- [ ] **Step 4: Run the whole package**

Run: `cd packages/tools && CENTINELA_TEST_DSN=postgresql://centinela:centinela@localhost:55432/centinela uv run pytest -q`
Expected: every test passes, including `tests/test_roles.py`, which now runs with ten real `k_` functions in the database.

- [ ] **Step 5: Ask the user, then commit**

```bash
git add packages/tools/tests/conftest.py packages/tools/tests/test_parity.py
git commit -q -F - <<'MSG'
Check every base KPI against its view on fecha_corte() and against an as-of query on earlier days, where the views leak

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 4: The tree reads the kernel's catalogue

**Files:**
- Modify: `packages/agents/centinela_agents/catalog.py`, `packages/agents/pyproject.toml`, `packages/agents/uv.lock` (written by `uv sync`)
- Modify: `packages/agents/tests/support.py`, and every `packages/agents/tests/*.py` that names `VIEW_CATALOG`
- Create: `packages/agents/tests/test_kernel.py`
- Modify: `DOUBTS.md`

**Interfaces:**
- Consumes: `centinela_tools.tools.catalogue_of(entries, sources)`, `kpi_catalogo(catalogue) -> list[dict]` with keys `id`, `entidad`, `columnas` (`[{nombre, tipo}]`) and `descriptivo`; `centinela_tools.kernel.Kernel.call(name, arguments)`, whose `kpi_consultar` answer holds `filas`, or `{"rechazado": {"guarda", "detalle"}}`.
- Produces:
  - `centinela_agents/catalog.py:KernelCall = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]`
  - `centinela_agents/catalog.py:catalog_from_kernel(kpis: Iterable[Mapping[str, Any]]) -> Catalog`
  - `centinela_agents/catalog.py:kernel_reader(call: KernelCall) -> KpiReader`, which raises `RuntimeError` naming the guard on a refusal.
  - `tests/support.py:KERNEL_CATALOG`, the catalogue every test of the tree uses.

- [ ] **Step 1: Write the failing test**

Create `packages/agents/tests/test_kernel.py`:

```python
# The two inputs the kernel hands the tree: the catalogue, from kpi_catalogo, and the reader, from
# kpi_consultar. The reader raises on a refusal, so a refused reading never passes for a day with no
# rows and no alert.
import pytest

from centinela_agents.catalog import kernel_reader

from support import KERNEL_CATALOG


def test_the_catalogue_holds_each_kpis_entity_and_columns():
    kpi = KERNEL_CATALOG.kpis["saldo_vencido"]
    assert kpi.entity == ("cliente_id",) and not kpi.descriptive
    assert {"max_dias_vencido", "saldo_abierto", "cupo_credito", "pesos_en_riesgo"} <= kpi.columns


def test_the_reader_returns_the_rows_kpi_consultar_returns():
    calls = []

    def call(name, arguments):
        calls.append((name, dict(arguments)))
        return {"kpi": "saldo_vencido", "dia": "2026-03-02", "consulta": "SELECT 1", "filas": [{"cliente_id": "CLI-001"}]}

    assert kernel_reader(call)("saldo_vencido", "2026-03-02") == [{"cliente_id": "CLI-001"}]
    assert calls == [("kpi_consultar", {"kpi": "saldo_vencido", "dia": "2026-03-02"})]


def test_a_refusal_of_the_kernel_raises_instead_of_reading_as_no_rows():
    read = kernel_reader(lambda name, arguments: {"rechazado": {"guarda": "catalogo", "detalle": "x is no KPI of this client's catalogue"}})
    with pytest.raises(RuntimeError, match="catalogo"):
        read("x", "2026-03-02")
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd packages/agents && uv run pytest tests/test_kernel.py -q`
Expected: FAIL at collection with `ImportError: cannot import name 'kernel_reader' from 'centinela_agents.catalog'`.

- [ ] **Step 3: Write the two inputs**

In `packages/agents/centinela_agents/catalog.py`, replace `from typing import Any, Callable, Mapping` with `from typing import Any, Callable, Iterable, Mapping`, add after the line `KpiReader = ...`:

```python
KernelCall = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]
```

and append at the end of the file:

```python


def catalog_from_kernel(kpis: Iterable[Mapping[str, Any]]) -> Catalog:
    return Catalog(
        {
            kpi["id"]: Kpi(tuple(kpi["entidad"]), frozenset(column["nombre"] for column in kpi["columnas"]), bool(kpi["descriptivo"]))
            for kpi in kpis
        }
    )


def kernel_reader(call: KernelCall) -> KpiReader:
    def read(metric: str, day: str) -> list[Mapping[str, Any]]:
        answer = call("kpi_consultar", {"kpi": metric, "dia": day})
        if "rechazado" in answer:
            raise RuntimeError(f"the kernel refused {metric} on {day}: {answer['rechazado']['guarda']}: {answer['rechazado']['detalle']}")
        return list(answer["filas"])

    return read
```

- [ ] **Step 4: Make `packages/tools` a development dependency**

In `packages/agents/pyproject.toml`, replace

```toml
[dependency-groups]
dev = ["pytest>=8"]
```

with

```toml
[dependency-groups]
dev = ["centinela-tools", "pytest>=8"]

[tool.uv.sources]
centinela-tools = { path = "../tools", editable = true }
```

Run: `cd packages/agents && uv sync && uv run python -c "import centinela_tools.paths as p; print(p.METRICAS)"`
Expected: the path of this tree's `data/metricas.yaml`. `uv.lock` changes; uv writes it, as `GENERATED.md` lists.

- [ ] **Step 5: Replace the hand-written catalogue with the kernel's**

In `packages/agents/tests/support.py`:
- Replace the four header lines (from `# The catalogue the tests hand the validator and the walk.` to `# The real catalogue comes from kpi_catalogo; DOUBTS.md files the gap.`) with:

```python
# Helpers the tree's tests share. The catalogue is the one the kernel serves: kpi_catalogo of
# packages/tools over the kernel: blocks of data/metricas.yaml, compiled with no database.
```

- Replace `from centinela_agents.catalog import Catalog, Kpi` with `from centinela_agents.catalog import Catalog, catalog_from_kernel`.
- After `from centinela_agents.yaml_loader import load_yaml`, add:

```python
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_catalogo, load_entries
```

- Delete the function `kpi(entity, *columns)` and the whole assignment `VIEW_CATALOG = Catalog({...})`, and put in their place:

```python
KERNEL_CATALOG = catalog_from_kernel(kpi_catalogo(catalogue_of(load_entries(METRICAS), load_sources())))
```

Then rename every other use:

Run: `cd packages/agents && sed -i 's/VIEW_CATALOG/KERNEL_CATALOG/g' tests/*.py && grep -rn "VIEW_CATALOG" . --include='*.py'`
Expected: no output.

- [ ] **Step 6: Run the package**

Run: `cd packages/agents && uv run pytest -q`
Expected: every test passes. `tests/test_validator.py` loads the base against `KERNEL_CATALOG`, so every `kpi.<metric>.<column>` the base reads is a column the kernel builds.

- [ ] **Step 7: Delete the paid debt**

In `DOUBTS.md`, delete the whole paragraph that opens with `**The base tree reads KPI columns no kernel builds.**` and ends with ``grep -o 'kpi\.[a-z0-9_]*\.[a-z0-9_]*' packages/agents/arbol/base.yaml | sort -u`.``, with the blank line before it.

- [ ] **Step 8: Ask the user, then commit**

```bash
git add packages/agents/ DOUBTS.md
git commit -q -F - <<'MSG'
Validate the tree against the catalogue the kernel serves and read KPIs through kpi_consultar, which pays the debt of columns no kernel built

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 5: The level pages

**Files:**
- Modify: `data/AGENTS.md`, `packages/tools/AGENTS.md`, `packages/agents/AGENTS.md`, `packages/agents/skills/vigia/contrato.md`, `evals/AGENTS.md`

**Interfaces:**
- Consumes: the decisions of this plan and the code of Tasks 2 to 4.
- Produces: the heading `data/AGENTS.md` § "The base KPIs", which Task 6 links from the guide.

- [ ] **Step 1: `data/AGENTS.md`, the clock**

In "The simulated clock", put this sentence as its own paragraph right before the paragraph that opens with `**Only some views compute "today"`:

```markdown
**The three paragraphs below describe the kit's views**, which the kernel KPIs replace for
detection; they still bind any agent that reads a view directly.
```

- [ ] **Step 2: `data/AGENTS.md`, the language table**

In "The kernel's language", replace the rows `filtro`, `medida`, `linea_base` and `salida` of the table, and add the rows `columnas`, `tomar`, `derivadas`, `decimales` and `tener` after `linea_base`, so the table reads:

```markdown
| Key | Holds | Bound |
|---|---|---|
| `fuente` | one source of `kernel/fuentes.yaml`: a table of `sql/01_esquema.sql`, never a `v_*` view, because several views compute "today" from `fecha_corte()` | a closed list |
| `unir` | names of the source's joins | at most three, each after the one it joins from |
| `abierto_al_dia` | `desde`, an event date, and `hasta`, a closing date or a closing the source declares: the rows open on `dia` | one time frame per KPI |
| `ventana` | an event date and a number of days back from `dia` | at most 365 days; one time frame per KPI |
| `filtro` | a column, an operator from `=`, `!=`, `<`, `<=`, `>`, `>=`, `en`, and a literal of the column's type, a date written `YYYY-MM-DD`; or, in place of the literal, `contra`: another column or `dia`, less `menos_dias` or `menos_meses` when it is a date | at most five; an `en` list of at most 20; a text literal of at most 200 characters, with no `%` and no NUL character; `contra` takes no `en`, and `menos_dias` at most 365 or `menos_meses` at most 12, never both |
| `agrupar` | dimensions the source declares, or `{columna, por}` with `semana` or `mes` over an event or term date; it is the KPI's entity, one row per entity | one to three |
| `medida` | `sum`, `avg`, `count`, `min`, `max` or `mediana` over a column, or over one expression of `+ - * /` over columns, numbers and `dia`; `ultimo` or `anterior`, the latest value or the one before it by `por`, an event date; `si`, conditions of the `filtro` form that only this measure applies; `count` with no column counts rows | expression depth three; at most three conditions in `si`; a `sum` with `si` over no row is 0 |
| `razon` | a `medida` over another `medida`, in place of `medida` | one |
| `linea_base` | an event date, `semana` or `mes`, N, and `delta`, `delta_pct` or `caida` (the base minus the value): the last period complete on `dia` against the mean of the N before it | N at most 12; one time frame per KPI; a numeric measure; no `{columna, por}` in `agrupar` |
| `columnas` | more named measures over the same rows; with a `linea_base`, each is measured on the last complete period | at most eight |
| `tomar` | other KPIs, each written inline as a block, named, with `por` mapping each column of its entity to a column of this KPI; read as `<name>.<column>` | at most two; a taken KPI takes at most one more level |
| `derivadas` | named expressions computed after the measures, over the columns before them: `+ - * /`, `mayor` and `menor` of two, `dias_habiles` (Monday to Friday after `desde`, up to `hasta`), `compara`, `existe`, `si` with `cuando`, `entonces` and `sino`, `participacion` (the percent of a column's total over every row) and `periodo_anterior` (a column of the same entity one period before); operands are columns, numbers, `dia` and `{umbral: <column>}`, the entry's own `umbrales` for that column | at most six; four operations deep; `periodo_anterior` needs exactly one `{columna, por}` in `agrupar` |
| `decimales` | the decimals of an output column, rounded on the way out only, so a derived column reads the unrounded value | 0 to 4 |
| `tener` | an output column, a comparison and a number: the only rows the KPI returns | at most three |
| `salida` | the names of the output columns: `valor`, plus `base` and `delta` with a `linea_base` | each unique across `agrupar`, `salida`, `columnas` and `derivadas`, never `dia` or `periodo` |
```

- [ ] **Step 3: `data/AGENTS.md`, the taken KPI**

Right after the paragraph that opens with `**A join is many-to-one**`, add:

```markdown
**A taken KPI joins like a join.** `tomar` reaches the whole entity of another KPI, which holds one
row per entity, so it never multiplies a row; it compiles on the same `dia`, so the clock holds
inside it. It is written inline, not named by id, so a block stays self-contained and an approved
KPI can take one with no base KPI behind it. An `umbral` operand reads the entry's own `umbrales`,
so a pesos at risk that needs a threshold reads the one place the threshold is written.
```

- [ ] **Step 4: `data/AGENTS.md`, the base KPIs**

Add this section right before `## The scenarios`:

```markdown
## The base KPIs

**Every metric of `metricas.yaml` carries a `kernel:` block, and none is dropped or renamed**,
because the skills, `acciones.md`, the evals and the draft contract of `apps/web` name them. The list
is `grep -oP '^  \K[a-z_]+(?=:)' metricas.yaml`. Each compiles to `centinela.k_<metric>(dia)`, which
`Vigía`'s detection reads.

**A base KPI outputs what is read from it**: its entity, the columns the decision tree reads, the
columns its `umbrales` names, the columns `calcular_impacto` reads
([`../packages/tools/AGENTS.md`](../packages/tools/AGENTS.md)), and its view's own columns that
parity compares. `Analista` still reads the views for anything else.

**Every base KPI outputs `pesos_en_riesgo`**, the formula its entry writes in prose, because the
detection reads an alert's exposure from that column and computes none.

**`cobertura_dias` outputs `pedidos_pendientes`**: the orders holding the SKU that are placed by
`dia`, not cancelled, and not invoiced by `dia`, through the closing `facturada`. `OPE-POL-007` §2
makes a coverage under 5 days with pending orders critical, and `pedidos.estado` is `fuga`. It
counts across both warehouses, because the map from a city to its warehouse is written only in
`v_cobertura_inventario`'s text, in no table.

**`descuento_en_exceso` outputs `exceso_semana_anterior`**, the same seller's excess the week
before, because `COM-POL-002` §5 escalates two consecutive weeks of the same seller. It and
`margen_bruto_negativo` return the whole history up to `dia`, as their views do; the tree's rule of
one alert per metric and entity keeps an old week or line from alerting twice.

**`dias_pago_prom` measures by month of payment**: the mean days from invoice to payment of the
payments made in the last complete month, against the mean of the 12 months before. Its view,
`v_dias_pago_mensual`, groups by month of invoice, and the last months of invoices hold only the
ones already paid, so a slow payer would never reach the threshold of `FIN-POL-004` §5. A customer
who pays nothing has no row; `saldo_vencido` covers that case.

**`audiencia` is derived from the owners** that the two tables of
[`../packages/agents/skills/estratega/acciones.md`](../packages/agents/skills/estratega/acciones.md)
name for the metric: `operacion` is who executes (`Compras`, `Analista de cartera`, a
`vendedor_id`), `supervision` who supervises (`Jefe de cartera`, `Control Comercial`, `Comercial`),
and `gerencia` is `Dirección Financiera` and `Gerencia Comercial`. A new owner there is placed here
first.

**The kit's views stay as delivered**, because `Analista`'s cause views and the kit's examples read
them, and they are the reference for parity.

**Parity is checked in two halves.** On `fecha_corte()`, the last day of the dataset, the kit's views
are right by definition, so each KPI returns its view's rows, value for value, on the columns the
view holds. On earlier simulated days the views leak, so each KPI agrees with a hand-written as-of
query, never with the view. `dias_pago_prom` has only that second half, because its view measures
by month of invoice. `uv run pytest tests/test_parity.py` in `packages/tools` holds both against
the scratch database; its header states the comparisons that depart and why.
```

- [ ] **Step 5: `packages/tools/AGENTS.md`**

- In "Why each file exists", in the `tests/` row, replace

```markdown
`tests/fixtures/metricas.yaml` holds the KPIs they compile;
```

with

```markdown
`tests/fixtures/metricas.yaml` holds the KPIs they compile; `tests/test_parity.py` checks every base KPI against its view and an as-of query;
```

- In "The KPI kernel", replace `compile_kpi(block, sources, day)` with `compile_kpi(block, sources, day, thresholds)`, and replace the end of that sentence, `simulated day by construction.` (on the next line), with

```markdown
simulated day by construction; `thresholds`, the entry's `umbrales`, answers an `umbral` operand.
```

- In the paragraph that opens with `**The cost cap is a measurement.**`, after the sentence that ends `leaves room for a baseline KPI.`, add

```markdown
The base KPIs of `data/metricas.yaml` cost at most 339131 on the official dataset, `dias_pago_prom`'s.
```

- In "The impact calculator", replace the two lines

```markdown
`calcular_impacto` takes a formula name, the alert's entity and the simulated day, runs its queries
over the views, and returns each figure with its query. The formula, not the model, chooses every
```

with

```markdown
`calcular_impacto` takes a formula name, the alert's entity and the simulated day, runs
`kpi_consultar` on the KPIs below, and returns each figure with its query. The formula, not the model, chooses every
```

  and replace the formula table with:

```markdown
| Formula | Returns | Computed as |
|---|---|---|
| `traslado_costo` | `price_increase_pct`, impact per month | the increase from `costo_anterior` to `costo_unitario` over `precio_lista`, the list price in force, all of `k_variacion_costo_pct`; times its `unidades_mes_prom`, the SKU's mean monthly units over the last 90 days |
| `precio_a_margen_minimo` | `price_increase_pct`, impact per month | the price change that takes the line's `margen_pct` to `margen_minimo_pct`, both of `k_margen_pct`; the margin gap times its `ventas_mes_prom`, the line's mean monthly `valor_neto` over the last 90 days |
| `cartera_vencida` | impact once | the customer's `saldo_vencido` in `k_saldo_vencido` |
| `ventas_protegidas` | `units`, impact once | `demanda_prom_30d` of `k_cobertura_dias` times the class minimum coverage of `OPE-POL-007 §2` minus its `existencia`; those units times its `precio_lista`, the list price in force |
| `descuento_recuperado` | impact per month | the seller's `sum(descuento_en_exceso)` over the rows of `k_descuento_en_exceso` whose `semana` falls in the last four weeks |
| `venta_bajo_costo` | impact per month | `-sum(margen_bruto)` of the SKU's rows of `k_margen_bruto_negativo` whose `fecha` falls in the last four weeks |
| `compra_recuperada` | impact per month | the customer's `pesos_en_riesgo` in `k_veces_intervalo_habitual`, its mean monthly `valor_neto` over the six months up to `ultima_compra` |
```

- [ ] **Step 6: `packages/agents/AGENTS.md` and `Vigía`'s skill**

- In "Why each file exists", in the `pyproject.toml`, `uv.lock` row, replace

```markdown
the package and its pinned dependencies; `uv.lock` is written by uv
```

with

```markdown
the package and its pinned dependencies, with `packages/tools` for the tests, which validate the base against the catalogue the kernel serves; `uv.lock` is written by uv
```

- In "Decisions", at the end of the bullet that opens with `**The kernel reaches the tree through two inputs**`, after `The tree never opens a connection, because no agent does.`, add

```markdown
  `centinela_agents/catalog.py:catalog_from_kernel(kpis)` builds the catalogue from `kpi_catalogo`,
  and `centinela_agents/catalog.py:kernel_reader(call)` builds the reader from `kpi_consultar`,
  raising on a refusal, so a refused reading never passes for a day with no alert.
```

- In "The universe", replace

```markdown
reached through the `v_*` views
```

with

```markdown
reached through the kernel's KPIs and the `v_*` views
```

- In "`Vigía` detects", replace

```markdown
- **Tools:** read-only SQL over the views `metricas.yaml` names, filtered by the simulated day.
```

with

```markdown
- **Tools:** `kpi_consultar` over the KPIs `metricas.yaml` names, on the simulated day.
```

- In `packages/agents/skills/vigia/contrato.md`, replace

```markdown
it reads the thresholds in `metricas.yaml` and the views,
```

with

```markdown
it reads the thresholds in `metricas.yaml` and the kernel's KPIs,
```

Run: `grep -rn 'v_[a-z_]*' packages/agents/skills/vigia/`
Expected: no output (the spec's acceptance).

- [ ] **Step 7: `evals/AGENTS.md`**

- In "The case format", in the `verificacion_sql` row, replace

```markdown
the query against the `v_*` views that produces the expected answer
```

with

```markdown
the query against the `v_*` views, or a kernel function `centinela.k_<metric>(dia)`, that produces the expected answer
```

- In "The cases of each agent", the first sentence ends `or with `ORQ-` for` and continues `the orchestrator, so the set of one runs alone` on the next line. Replace `the orchestrator, so the set` with

```markdown
the orchestrator and `KER-` for the kernel, so the set
```

- Add this row at the end of that section's table:

```markdown
| kernel | per metric of `data/metricas.yaml`: parity with its view on `fecha_corte()` where the view measures the same thing, and the as-of check on three earlier simulated days | the view, and a hand-written as-of query |
```

- After the paragraph that opens with `**The orchestrator's routing cases run with no model`, add:

```markdown
**The kernel's cases run with no model and no `apps/api`**:
[`../packages/tools/tests/test_parity.py`](../packages/tools/tests/test_parity.py) holds them
against the scratch database, one test per metric and day, and
[`../packages/tools/AGENTS.md`](../packages/tools/AGENTS.md) names the command. The `VIG-` cases run
unchanged, with `Vigía` reading the kernel.
```

- [ ] **Step 8: Check the links and the pages**

Run: the link check of `CLAUDE.md` (verification 6).
Expected: no output.
Run: `grep -n "VIEW_CATALOG\|no kernel builds" -r . --include='*.md' | grep -v node_modules | grep -v docs/superpowers/`
Expected: no output.

- [ ] **Step 9: Ask the user, then commit**

```bash
git add data/AGENTS.md packages/tools/AGENTS.md packages/agents/AGENTS.md packages/agents/skills/vigia/contrato.md evals/AGENTS.md
git commit -q -F - <<'MSG'
State the base KPIs, the new primitives and the kernel cases on the pages that own them, and point Vigía at kpi_consultar

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 6: The guide chapter, and the checks only a person runs

**Files:**
- Modify: `docs/guide/chapters/kpi-kernel.md`, `docs/guide/chapters/status.md`

**Interfaces:**
- Consumes: the heading `data/AGENTS.md` § "The base KPIs".
- Produces: a chapter that owns only what no level page states.

- [ ] **Step 1: Shrink the chapter**

In `docs/guide/chapters/kpi-kernel.md`:
- In the intro, replace `this chapter draws them and owns the two parts still to be built.` with `this chapter draws them and owns the one part still to be built.`
- Replace the top warning box with: `> **Decided, not implemented.** No agent calls the kernel's tools yet, and no KPI is born at runtime. The last section is what remains.`
- Replace the whole section `## Rebuilding the current metrics`, its warning box and its paragraph, with:

```markdown
## Rebuilding the current metrics

Every metric of `metricas.yaml` is a base KPI of the kernel, checked against its view in two
halves; [data](../../../data/AGENTS.md) states it under "The base KPIs".
```

The section draws no diagram, so it carries no `Draws:` caption.

- [ ] **Step 2: `status.md`**

In the "By part" table, change the last cell of the `data` row to `none`, of the `packages/tools` row to `none`, and of the `evals` row to `cases for the tree's growth`.

- [ ] **Step 3: Build the guide without Docmost**

Run: `cd docs/guide && python publish.py --build-only "$(mktemp -d)"`
Expected: no `draws ... which that page lacks` problem, and no broken link.

- [ ] **Step 4: Run the whole verification**

Run: `cd packages/tools && CENTINELA_TEST_DSN=postgresql://centinela:centinela@localhost:55432/centinela uv run pytest -q`, then `cd ../agents && uv run pytest -q`.
Expected: every test passes in both packages.
Run: the `CLAUDE.md` link check. Expected: no output.
Run: `git status --short`, against `GENERATED.md`. Expected: only the files of this task. `05_kpis.generated.sql` is unchanged since Task 2.

- [ ] **Step 5: Ask the user, then commit**

```bash
git add docs/guide/chapters/kpi-kernel.md docs/guide/chapters/status.md
git commit -q -F - <<'MSG'
Shrink the kernel chapter's rebuild section to a link, now that data states the base KPIs

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

- [ ] **Step 6: Hand the person-only checks to the user**

Ask the user to run these and report:

1. **The compose from scratch** (`CLAUDE.md` verification 1): `cd data && docker compose down -v && docker compose up -d`, then, as `centinela_lector`, `SELECT * FROM centinela.k_saldo_vencido(centinela.fecha_corte()) LIMIT 5;`. It proves that initdb applies the ten functions after `04` and that the reader runs them.
2. **The ISO 22400-2 fields** of each entry of `data/metricas.yaml` (decision 11), which no test can judge: `audiencia` against the rule `data/AGENTS.md` § "The base KPIs" states, the rest against each metric's meaning.
3. **The guide**: `python publish.py` in `docs/guide`, then read "The KPI kernel", "What exists today" and the `data` page in Docmost.
4. **An end-to-end read** of every page this plan touched, for present tense and for a fact stated in two places (`CLAUDE.md` verification 7).

The plan stays until the user confirms; deleting it is a separate commit, by `CLAUDE.md`'s rule.

---

## Self-review against the spec

| Spec requirement | Task |
|---|---|
| every metric gains a `kernel:` block, none dropped or renamed | 2 (`test_every_metric_of_metricas_yaml_is_a_base_kpi` in 3) |
| ISO 22400-2 fields on every entry | 2 (`check_card` in `catalogue_of`) |
| compiles to `centinela.k_<metric>(dia)` in `05_kpis.generated.sql` | 2 |
| parity on `fecha_corte()`, row for row, against the view | 3, except `dias_pago_prom`, checked by its as-of query only (decision 14) |
| as-of check on three earlier simulated days, against a hand-written query | 3, with a guard that each KPI returns rows on one of them (decision 8) |
| the kit's views stay as delivered | 2 (no file of `data/sql/01` to `04` changes) |
| `pesos_en_riesgo` and every formula of `calcular_impacto` read kernel KPIs | 2, 5; no formula reads a view (decision 6) |
| every base KPI outputs `pesos_en_riesgo` | 2, 3 (`test_every_base_kpi_outputs_pesos_en_riesgo`) |
| `cobertura_dias` outputs `pedidos_pendientes` from dates | 2, 3 |
| a measure the language lacks is a primitive with its bound, never a hand-written function | 2 (`test_primitives.py`) |
| `margen_pct`: baseline over 8 weeks and the join to `ref_margen_minimo_linea` | 2, 3 |
| `variacion_costo_pct`: no price change within 10 business days | 2, 3 |
| `descuento_en_exceso`: two consecutive weeks of the same seller | 2, 3 |
| `Vigía` and the tree read the kernel | 4, 5 |
| the pages of "Pages this spec changes" | 5, 6 |
| Acceptance: the `VIG-` cases pass with `Vigía` reading the kernel | 4 (decision 10: no `VIG-` case exists; the tree's tests run on the kernel's catalogue) |
| Acceptance: `grep -rn 'v_[a-z_]*' packages/agents/skills/vigia/` prints nothing | 5, Step 6 |
