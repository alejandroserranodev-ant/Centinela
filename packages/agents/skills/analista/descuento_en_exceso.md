# Analista: `descuento_en_exceso`

The entity is a `vendedor_id` in a week. The symptom starts on the first `fecha` of its rows in
`v_descuentos_fuera_politica`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | one seller concentrates the excess | `v_descuentos_fuera_politica` where `fecha <= :dia`, `sum(descuento_en_exceso)` by `vendedor_id` | the entity has the largest sum | another seller has a larger sum |
| H2 | it repeats in consecutive weeks | the same view where `vendedor_id` = the entity, by week | rows exist in two consecutive weeks up to `:dia` | they do not |
| H3 | it concentrates in a few customers | the same view where `vendedor_id` = the entity, `sum(descuento_en_exceso)` by `cliente_id` | the top three customers hold more than half of the sum | they do not |
| H4 | the excess erodes the line's margin | `v_ventas` where `vendedor_id` = the entity and `fecha <= :dia`, `sum(margen_bruto)` by week | `margen_bruto` falls from the symptom start | it does not |

1. H1 is the main cause if it holds. Report H2, H3 and H4 as contributing when they hold.
2. If H2 holds, cite `COM-POL-002 §5`.
3. Cite `tope_descuento_pct` and `aprobacion_especial` from the view, never a figure from the policy text.
4. If H1 is refuted, answer `identified` with the cause spread across sellers, and list each with its sum.
