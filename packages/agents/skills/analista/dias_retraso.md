# Analista: `dias_retraso`

The entity is an `oc_id`. The symptom starts on its `fecha_esperada`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the supplier is late on other orders | `v_ordenes_compra` where `proveedor_id` = the order's supplier and `fecha_esperada <= :dia` | another order has `dias_retraso` > 0 | no other order has |
| H2 | the delay puts the SKU at risk | `v_cobertura_inventario` where `sku` and `bodega_id` = the order's | `cobertura_dias` < `dias_retraso` + `lead_time_dias` | it is not |

1. H1 is the main cause if it holds: the supplier is late across orders. Otherwise, the cause is
   this order alone; say so in `sentence`.
2. Report H2 as contributing if it holds, and set `same_cause_as` to an open `cobertura_dias`
   alert on that SKU and warehouse.
3. The data holds no reason for a delay. Never state one.
