# Spec 5 of 6: the current metrics, built by the kernel

**Status:** planned in `2026-10-03-current-kpis-in-kernel-plan.md`. **Depends on:** spec 4, `kpi-kernel`, for the language, the compiler
and the tools.

## Why

The kernel earns trust by rebuilding what already exists and proving it agrees. Every metric in
`metricas.yaml` gains a `kernel:` block, compiles to `centinela.k_<metric>(dia)` in
`data/sql/05_kpis.generated.sql`, and is checked
against the view it replaces. Once it holds, `Vigía` and the tree read the kernel, and the clock
leaks the data page lists stop reaching any alert.

## Decisions

- **Every metric of `metricas.yaml` is rebuilt, and none is dropped or renamed**, because the
  skills, `acciones.md`, the evals and the draft contract of `apps/web` name them. The list is
  `grep -oP '^  \K[a-z_]+(?=:)' data/metricas.yaml`.
- **Parity is checked in two halves.** On `fecha_corte()`, the last day of the dataset, the kit's
  views are correct by definition, so the kernel KPI must return the same rows as its `v_*` view,
  value for value. On earlier simulated days, the kit's views are the ones that leak, so the
  kernel KPI is checked against a hand-written as-of query in the test, never against the view.
  The reason: the kit is the reference only where it is right.
- **The kit's views stay, vendored as delivered**, because `Analista`'s cause views and the kit's
  own examples read them, and because they are the reference for the first half of parity.
- **`pesos_en_riesgo` and every formula of `calcular_impacto` read kernel KPIs**, so the exposure
  `Vigía` reports and the recovery `Estratega` proposes are computed by one definition.
- **Every base KPI outputs a `pesos_en_riesgo` column**, the formula its entry writes in prose,
  because bug spec 1, `orchestrator-runtime`, which runs after this one, reads the exposure of a
  detection from that column and computes none. **`cobertura_dias` also outputs
  `pedidos_pendientes`**, the orders pending dispatch on `dia`, built from their dates, because
  OPE-POL-007 §2 makes a coverage under 5 days with pending orders critical and `pedidos.estado`
  is marked `fuga`.
- **A metric whose `umbral_alerta` needs a measure the language cannot express is a defect of the
  language**, fixed by adding a primitive in spec 4's table, with its bound, never by a hand-written
  function in `05_kpis.generated.sql`. Expected cases: `margen_pct` needs `linea_base` over 8 weeks and the
  join to `ref_margen_minimo_linea`; `variacion_costo_pct` needs "no price change within 10 business
  days", which needs a business-day window; `descuento_en_exceso` needs "two consecutive weeks of
  the same seller". Each one the plan meets is added to spec 4's table first.

## Per metric

The plan of this spec carries one task per metric with the same four steps: write the `kernel:`
block and the ISO 22400-2 fields; compile and validate; parity on `fecha_corte()`; as-of check on
three simulated days spread over the period. Where the as-of check and the view disagree on an
earlier day, the disagreement is the leak the clock section of `data/AGENTS.md` names, and the
test asserts the kernel's value.

## Who reads what, after this spec

| Reader | Reads before | Reads after |
|---|---|---|
| `Vigía`'s detection | the `v_*` view of each metric, filtered by the simulated day | `kpi_consultar` on `k_<metric>(dia)` |
| a `detectar` node of the tree | none; the tree does not exist yet | `kpi.<metric>.<column>`, built by the kernel |
| `calcular_impacto` | the `v_*` views it names | the kernel KPIs, plus `v_precio_sku` and `v_costo_sku` where it needs a price or a cost in force |
| `Analista` | every view | every view, plus `kpi_catalogo` and `kpi_consultar` |
| `ejecutar.vigente` (spec 2) | none; the node does not exist yet | `kpi_consultar` on the KPI that justified the approved action |

## Pages this spec changes

| Page | Change |
|---|---|
| `data/metricas.yaml` | a `kernel:` block and the ISO 22400-2 fields on every entry |
| `data/AGENTS.md`, "The simulated clock" | "Only some views compute "today" from `fecha_corte()`" and the two paragraphs after it stay, prefixed by one sentence: they describe the kit's views, which the kernel KPIs replace for detection, and they still bind any agent that reads a view directly |
| `packages/agents/AGENTS.md`, `Vigía`'s tools | "read-only SQL over the views `metricas.yaml` names, filtered by the simulated day" becomes "`kpi_consultar` over the KPIs `metricas.yaml` names, on the simulated day" |
| `packages/tools/AGENTS.md`, "The impact calculator" | the "Computed as" column names kernel KPIs where it names a metric's view |
| `evals/AGENTS.md` | a `KER-` prefix: parity on `fecha_corte()` and the as-of check per metric; the `VIG-` cases run unchanged and must still pass |
| `docs/guide/chapters/kpi-kernel.md` | the section on rebuilding the current metrics shrink to a link to the level page this spec writes them into; the diagrams stay in the chapter, each captioned `Draws:` with that page's new section, and the chapter's warning box drops what this spec implements |

## Acceptance

- Parity on `fecha_corte()` holds for every metric, row for row.
- The as-of check holds on three simulated days per metric.
- The `VIG-` cases of `evals/AGENTS.md` pass with `Vigía` reading the kernel.
- `grep -rn 'v_[a-z_]*' packages/agents/skills/vigia/` prints nothing that `Vigía` queries directly.

## Amendments made while planning

Each item supersedes the line of this spec it names; the plan builds the amended version.

- **The language grows by primitives the metrics force, each with its bound**, and none takes free SQL. `medida.si`: up to three conditions of the `filtro` form, compiled to `FILTER (WHERE ...)`; a `sum` with `si` over no row is 0, so `saldo_vencido` is 0 for a customer whose open invoices are not yet due, as in the view. `ultimo` and `anterior`: the latest value, or the one before it, ordered by `por`, an `evento` date. Expression operands: a number and `dia`, at depth three (it was two). `filtro` and `si` take `contra` in place of `valor`: another column or `dia`, less `menos_dias` (at most 365) or `menos_meses` (at most 12), never both and never with `en`. `columnas`: up to eight more named measures, measured on the last complete period with a `linea_base`. `tomar`: up to two other KPIs, written inline, joined many-to-one on their whole entity by `por`, compiled on the same `dia`, read as `<name>.<column>`, nesting at most one more level; inline so a block stays self-contained and an approved KPI can take one with no base KPI behind it. `derivadas`: up to six named expressions after the measures, four operations deep: `+ - * /`, `mayor`, `menor`, `dias_habiles` (Monday to Friday after `desde` up to `hasta`), `compara`, `existe`, `si` with `cuando`, `entonces` and `sino`, `participacion` and `periodo_anterior` (needs exactly one `{columna, por}` in `agrupar`); operands are columns, numbers, `dia` and `{umbral: <column>}` from the entry's `umbrales`. `decimales`: 0 to 4, rounded on the way out only. `tener`: up to three conditions on output columns. `linea_base.salida` gains `caida`, the base minus the value. The expected cases resolved so: `margen_pct` needs `caida`, `columnas` and the join to `ref_margen_minimo_linea`; "no price change within 10 business days" is `dias_habiles` over a taken KPI of `lista_precios`; "two consecutive weeks of the same seller" is `periodo_anterior`; `veces_intervalo_habitual` needs no lag, because the mean gap is `(last - first) / (n - 1)`.
- **The compiler wraps every KPI in an outer `nucleo` layer**, where `derivadas`, `decimales` and `tener` apply, and `COMPILER_VERSION` becomes `"2"`, because the compiled text of every KPI changes; no approved KPI exists yet.
- **The generator writes `DROP FUNCTION IF EXISTS` before each `CREATE FUNCTION`**, because `CREATE OR REPLACE FUNCTION` cannot change the columns a function returns; the grants are written again after the drop.
- **Each KPI outputs what is read from it**, not every column of its view: its entity, the columns the tree reads, the columns its `umbrales` names, `pesos_en_riesgo`, the columns `calcular_impacto` reads, and the view's columns parity compares. `Analista` still reads the views. The entity of `margen_pct` is `linea` and of `dias_pago_prom` is `cliente_id`, because a baseline measures the current period; every other entity is its view's.
- **`cobertura_dias.pedidos_pendientes` counts the orders holding the SKU, placed by `dia`, not cancelled and not invoiced by `dia`, across both warehouses**, through a closing `facturada` of `pedidos_detalle` matched on `pedido_id`. An order is invoiced on its day or the next, so "not invoiced by `dia`" is pending dispatch. It is per SKU because the map from a city to its warehouse is written only in `v_cobertura_inventario`'s text.
- **`calcular_impacto`'s figures are KPI columns, and it reads no view.** `traslado_costo` reads `costo_unitario`, `costo_anterior`, `precio_lista` and `unidades_mes_prom` of `variacion_costo_pct`; `precio_a_margen_minimo` reads `ventas_mes_prom` of `margen_pct`, each `_mes_prom` the last 90 days over 3; `compra_recuperada` is `veces_intervalo_habitual`'s `pesos_en_riesgo`; `venta_bajo_costo` reads `margen_bruto_negativo`'s `fecha` and `sku`. This supersedes "plus `v_precio_sku` and `v_costo_sku`" in the table "Who reads what": those views compute `vigente` from `fecha_corte()`, so on an earlier day they name the price of the year's end.
- **Parity compares a view's own columns, and three comparisons depart.** `descuento_en_exceso` agrees with its view within half a peso per line, because the kit rounds each line and the kernel the week. `margen_pct` and `dias_pago_prom` are compared on the entities measured in the current period, because a view has no row for a period with no sale or payment. `dias_pago_prom` has no view half: it measures by month of payment, its view by month of invoice.
- **The as-of days are 2025-12-15, 2026-04-08 and 2026-09-15**, and `test_every_kpi_returns_rows_on_some_as_of_day` fails when a KPI returns no row on all three, because a day with no row proves nothing.
- **The tree's tests validate the base against the catalogue the kernel serves.** `packages/tools` is a development dependency of `packages/agents`; `centinela_agents/catalog.py:catalog_from_kernel(kpis)` and `centinela_agents/catalog.py:kernel_reader(call)` build the catalogue and the reader, the reader raising on a refusal. The `DOUBTS.md` debt "The base tree reads KPI columns no kernel builds" is paid.
- **No `VIG-` case exists**, so the acceptance on them is checked as far as code exists: the base validates against the kernel's catalogue and the walk of `detectar` runs on it.
- **The ISO 22400-2 fields follow written rules**: `rango` bounds what the measure can take, so `margen_bruto_negativo` has `max: 0`; `tendencia` follows the threshold's direction; `temporalidad` is `semanal` for `margen_pct` and `descuento_en_exceso`, `mensual` for `dias_pago_prom`, `diaria` otherwise. `audiencia` is derived from the owners of `packages/agents/skills/estratega/acciones.md`: `operacion` is who executes (`Compras`, `Analista de cartera`, a `vendedor_id`), `supervision` who supervises (`Jefe de cartera`, `Control Comercial`, `Comercial`), `gerencia` `Dirección Financiera` and `Gerencia Comercial`.
- **The second line of `metricas.yaml`'s header says `Vigía` reads the metrics through the kernel and `Analista` also through the views**, because "through the views" stops being true for detection.
- **`descuento_en_exceso` and `margen_bruto_negativo` return the whole history up to `dia`**, as their views do; the tree's rule of one alert per metric and entity keeps an old row from alerting twice.
- **`dias_pago_prom` measures by month of payment** (`linea_base.columna: pagos.fecha_pago`), against the mean of the 12 months before. By month of invoice the last months hold only the invoices already paid: on `fecha_corte()` that measures 37 of 406 customers at 23.9 days against a mean near 42, so a slow payer never reaches the threshold of `FIN-POL-004` §5; by month of payment it measures 408.
- **`dias_pago_prom`'s `descripcion` becomes "Días promedio entre factura y pago, por mes de pago"**, because `kpi_catalogo` serves it as the card; the key is unchanged. This supersedes "none is dropped or renamed" only in that one value changes.
