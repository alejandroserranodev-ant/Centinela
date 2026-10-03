# Analista: `margen_pct`

The entity is a `linea`. The symptom starts on the first complete `semana` of
`v_margen_semanal_linea` (`semana + 6 <= :dia`) whose `margen_pct` is below the mean of its 8
previous weeks.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | supplier cost rose | `v_costo_sku` where `linea` = the entity and `fecha_vigencia` within the 12 weeks before `:dia` | one or more rows have `variacion_pct` > 0 and `fecha_vigencia` <= the symptom start | no row has `variacion_pct` > 0 |
| H2 | list price not adjusted to H1 | `v_precio_sku` for the SKUs of H1, `fecha_vigencia` between the cost change and `:dia` | H1 holds and no row has `variacion_pct` > 0 | a row has `variacion_pct` > 0 |
| H3 | discount rose | `v_ventas` where `linea` = the entity and `fecha <= :dia`, `avg(descuento_pct)` by week | the mean from the symptom start is above the mean of the 8 weeks before it | it is equal or below |
| H4 | mix moved to lower-margin SKUs | `v_ventas` where `linea` = the entity and `fecha <= :dia`, `sum(valor_neto)` and `sum(margen_bruto)` by `sku` and week | SKUs with `margen_bruto / valor_neto` below the line's gained share of `valor_neto` from the symptom start | no such SKU gained share |

1. If H1 and H2 hold, report them as one main cause: the cost rose and the price did not follow.
   Name the `proveedor_id` and the SKUs.
2. If H1 holds and H2 is refuted, report H1 as main and test H3 and H4 as contributing.
3. Compare the line's `margen_pct` with `margen_minimo_pct` in `v_margen_minimo_linea` and state it as evidence.
4. If H1, H3 and H4 are refuted, answer `no_evidence`.
5. If H1 and H2 hold and the input lists an open `variacion_costo_pct` alert on a SKU of H1, set
   `same_cause_as` to its `id`. Otherwise, set none.
