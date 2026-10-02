# Analista: `margen_bruto_negativo`

The entity is a `sku`, or a `vendedor_id` when the lines share one seller. The symptom is the rows
of `v_ventas` with `margen_bruto` < 0 and `fecha <= :dia`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the cost rose above the price | `v_costo_sku` and `v_precio_sku` where `sku` = the entity, `vigente` on the sale date | `costo_unitario` > `precio_lista` | `costo_unitario` <= `precio_lista` |
| H2 | the discount pushed the price below cost | `v_ventas`, the same rows | `precio_unitario` < `costo_total / cantidad` and `precio_lista` > `costo_total / cantidad` | `precio_lista` <= `costo_total / cantidad` |
| H3 | one seller concentrates the lines | `v_ventas`, the same rows, `count(*)` by `vendedor_id` | one `vendedor_id` holds more than half the rows | none does |

1. Report H1 or H2 as the main cause, whichever holds. They cannot both hold for one row.
2. Report H3 as contributing when it holds.
3. Add to `assumptions`: "No consta aprobación de Gerencia General en los datos." Never say the policy was breached.
