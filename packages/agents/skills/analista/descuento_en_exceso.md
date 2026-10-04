# Analista: `descuento_en_exceso`

The entity is a `vendedor_id` in a `semana`, the Monday that starts the week. The symptom is the
seller's rows of `v_descuentos_fuera_politica` whose `fecha` falls in that week and on or before
`:dia`; it starts on the first `fecha` of them.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | one seller concentrates the excess | `v_descuentos_fuera_politica` where `date_trunc('week', fecha)` = the entity's `semana` and `fecha <= :dia`, `sum(descuento_en_exceso)` by `vendedor_id` | the entity's `vendedor_id` has the largest sum | another seller has a larger sum |
| H2 | it repeats in consecutive weeks | the same view where `vendedor_id` = the entity's and `fecha <= :dia`, by `date_trunc('week', fecha)` | rows exist in the week before the entity's `semana` | they do not |
| H3 | it concentrates in a few customers | the same view where `vendedor_id` = the entity's, in the entity's `semana`, `sum(descuento_en_exceso)` by `cliente_id` | the top three customers hold more than half of the sum | they do not |
| H4 | the excess erodes the seller's margin | `v_ventas` where `vendedor_id` = the entity's and `fecha <= :dia`, `sum(margen_bruto)` by week | `margen_bruto` falls from the symptom start | it does not |

1. H1 is the main cause if it holds. Report H2, H3 and H4 as contributing when they hold.
2. If H1 is refuted and H2 or H3 holds, report the first of them that holds as the main cause, and
   the others that hold as contributing.
3. If H1, H2 and H3 are refuted, answer `no_evidence` with `reason`: "El exceso de descuento es de
   una sola semana y no se concentra en el vendedor ni en sus clientes."
4. If H2 holds, cite `COM-POL-002 §5`.
5. Cite `tope_descuento_pct` and `aprobacion_especial` from the view, never a figure from the policy text.
6. If the input lists an open `descuento_en_exceso` alert whose `entity` names the same
   `vendedor_id` in the week before, set `same_cause_as` to its `id`. Otherwise, set none.
