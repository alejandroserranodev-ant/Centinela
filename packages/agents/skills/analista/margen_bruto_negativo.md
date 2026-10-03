# Analista: `margen_bruto_negativo`

The entity is a `sku`, or a `vendedor_id` when the lines share one seller. The symptom is the rows
of `v_ventas` with `margen_bruto` < 0 and `fecha <= :dia`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the list price was already below cost | `v_ventas`, the same rows | `precio_lista * cantidad` <= `costo_total` | `precio_lista * cantidad` > `costo_total` |
| H2 | the discount pushed the sale below cost | `v_ventas`, the same rows | `precio_lista * cantidad` > `costo_total` and `descuento_pct` > 0 | `precio_lista * cantidad` <= `costo_total`, or `descuento_pct` = 0 |
| H3 | one seller concentrates the lines | `v_ventas`, the same rows, `count(*)` by `vendedor_id` | one `vendedor_id` holds more than half the rows | none does |

1. Report as the main cause the hypothesis, H1 or H2, whose rows hold the larger `-sum(margen_bruto)`.
   Report the other as contributing when it holds for at least one row.
2. Report H3 as contributing when it holds.
3. If neither H1 nor H2 holds for any row, answer `no_evidence` with the queries reviewed. Otherwise,
   answer `identified`.
4. Add to `assumptions`: "No consta aprobación de Gerencia General en los datos." Never say the policy was breached.
