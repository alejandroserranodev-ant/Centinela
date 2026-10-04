# Analista: `margen_bruto_negativo`

The entity is one order line: a `pedido_id` and its `linea_n`. The symptom is that line's row of
`v_ventas`, with `margen_bruto` < 0; it starts on the row's `fecha`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the list price was already below cost | `v_ventas` where `pedido_id` and `linea_n` = the entity | `precio_lista * cantidad` <= `costo_total` | `precio_lista * cantidad` > `costo_total` |
| H2 | the discount pushed the sale below cost | the same query | `precio_lista * cantidad` > `costo_total` and `descuento_pct` > 0 | `precio_lista * cantidad` <= `costo_total`, or `descuento_pct` = 0 |
| H3 | one seller concentrates the lines of this SKU below cost | `v_ventas` where `sku` = the line's `sku`, `margen_bruto` < 0 and `fecha <= :dia`, `count(*)` by `vendedor_id` | the line's `vendedor_id` holds more than half the rows | it does not |

1. H1 and H2 cannot both hold. The one that holds is the main cause.
2. If H1 or H2 is the main cause, test H3. If H3 holds, report it as contributing. Otherwise, report
   nothing more.
3. If H1 and H2 are refuted, answer `no_evidence` with `reason`: "La línea no está bajo costo en
   los datos del día." List the query in `queriesReviewed`.
4. Name in the evidence the line's `sku`, `vendedor_id` and `cliente_id`.
5. Add to `assumptions`: "No consta aprobación de Gerencia General en los datos." Never say the
   policy was breached.
6. Set no `same_cause_as`: the only open alerts this metric shares a cause with are of
   `margen_bruto_negativo` itself, which the contract refuses.
