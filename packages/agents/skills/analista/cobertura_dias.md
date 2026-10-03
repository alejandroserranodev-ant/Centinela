# Analista: `cobertura_dias`

The entity is a `sku` in a `bodega_id`. The symptom is `cobertura_dias` in `v_cobertura_inventario` on `:dia`.

Never read `recibida` or `dias_retraso` in `v_ordenes_compra`: the view computes them against
`fecha_corte()`, not `:dia`. On `:dia`, an order is **open** when `fecha_oc <= :dia` and
`fecha_recibida` is null or later than `:dia`. An open order is **late** when `fecha_esperada < :dia`;
its delay is `:dia - fecha_esperada`, computed in the query.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | an order is late | `v_ordenes_compra` where `sku` and `bodega_id` = the entity and `fecha_oc <= :dia` | an order is late on `:dia` | no order is late on `:dia` |
| H2 | no order is on the way | the same query | no order is open on `:dia` and no `fecha_oc` falls in the 60 days to `:dia` | an order is open, or a `fecha_oc` falls in those 60 days |
| H3 | demand rose | `v_ventas` where `sku` = the entity and `fecha <= :dia`, `sum(cantidad)` by `date_trunc('week', fecha)`, only weeks whose start + 6 <= `:dia` | the mean of the last four weeks exceeds the mean of the eight before them | it does not |

1. Test H1, then H2. H1 and H2 cannot both hold. The one that holds is the main cause.
2. If H1 and H2 are refuted, test H3. If H3 holds, it is the main cause. Otherwise, answer `no_evidence`.
3. If H1 or H2 is the main cause, test H3. If H3 holds, report it as a contributing cause. Otherwise, report none.
4. If H1 holds, name in the evidence its `oc_id`, `proveedor_id`, `lead_time_dias`, `fecha_esperada` and delay.
   If an order of the entity has `fecha_recibida` after the late order's `fecha_esperada` and on or
   before `:dia`, cite its `oc_id` and `cantidad` as a delivery received while the late order was open.
   Otherwise, cite none.
5. If H1 holds and the input lists a `dias_retraso` alert whose `entidad` is the late `oc_id`, set
   `same_cause_as` to its `id`. Otherwise, set none.
6. If H3 was run, add to `assumptions` that it measures the `sku` in both warehouses, because no view
   gives demand by `bodega_id`. Otherwise, add nothing.
7. If `unidades_pendientes` > 0, add to `assumptions` the limit of `v_cobertura_inventario` the clock
   section of `data/AGENTS.md` names. Otherwise, add nothing.
