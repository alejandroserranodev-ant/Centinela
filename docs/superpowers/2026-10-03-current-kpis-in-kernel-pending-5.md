# Spec 5 of 6: the current metrics, built by the kernel

**Status:** pending its plan. **Depends on:** spec 4, `kpi-kernel`, for the language, the compiler
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
