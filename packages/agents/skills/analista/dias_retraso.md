# Analista: `dias_retraso`

The entity is an `oc_id`. The symptom starts on its `fecha_esperada`.

Never read `recibida` or `dias_retraso` in `v_ordenes_compra`: the view computes them against
`fecha_corte()`, not `:dia`. On `:dia`, an order is **open** when `fecha_oc <= :dia` and
`fecha_recibida` is null or later than `:dia`. An open order is **late** when `fecha_esperada < :dia`;
its delay is `:dia - fecha_esperada`, computed in the query. A received order was **received late**
when `fecha_recibida <= :dia` and `fecha_recibida > fecha_esperada`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the supplier is late on other orders | `v_ordenes_compra` where `proveedor_id` = the order's supplier and `fecha_oc <= :dia` | another order is late on `:dia`, or was received late | no other order is |
| H2 | the delay puts the SKU at risk | `v_cobertura_inventario` where `sku` and `bodega_id` = the order's | `cobertura_dias` < the order's delay + `lead_time_dias` | it is not |

1. If H1 holds, report it as the main cause: the supplier is late across orders. Otherwise, answer
   `no_evidence` with `reason`: "Los datos no registran el motivo del retraso y ninguna otra orden
   del proveedor está retrasada."
2. If H2 holds, report it as contributing, and if the input lists an open `cobertura_dias` alert on
   that SKU and warehouse, set `same_cause_as` to its `id`. Otherwise, report nothing more and set none.
3. The data holds no reason for a delay. Never state one.
