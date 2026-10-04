# Analista: `concentracion_vencida_pct`

The entity is a `cliente_id`. The symptom is its share of the sum of `saldo_vencido` over every
customer in `v_cartera_cliente`. It starts on the first `mes_factura` in `v_dias_pago_mensual` whose
`dias_pago_prom` exceeds `plazo_dias`. If no month does, it starts on `:dia`.

`v_dias_pago_mensual` counts paid invoices only, so a month whose invoices are still unpaid has no row.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the customer pays slower | `v_dias_pago_mensual` where `cliente_id` = the entity and `mes_factura <= :dia`, the last three rows by `mes_factura` | `dias_pago_prom` rises across those three rows | it does not rise, or fewer than three rows exist |
| H2 | the customer bought more | `v_ventas` where `cliente_id` = the entity and `fecha <= :dia`, `sum(valor_neto)` by month, only months whose last day <= `:dia` | the mean of the last three months exceeds the mean of the six before them | it does not |
| H3 | the customer is above its limit | `v_cartera_cliente` where `cliente_id` = the entity | `saldo_abierto` > `cupo_credito` | `saldo_abierto` <= `cupo_credito` |
| H4 | an old invoice was never paid | `v_cartera_cliente` where `cliente_id` = the entity | H1 is refuted and `max_dias_vencido` falls in `tramo_4` of `saldo_vencido` in `data/metricas.yaml` | H1 holds, or `max_dias_vencido` falls in another `tramo` |
| H5 | the seller's other customers are overdue (candidate) | `v_ventas` where `fecha <= :dia`, distinct `cliente_id` and `vendedor_id`, joined to `v_cartera_cliente` by `cliente_id` | another customer of the entity's `vendedor_id` has `max_dias_vencido` above the `umbral_alerta` of `saldo_vencido` | no other customer has |

1. Test H1 to H4 in order. The first that holds is the main cause. Report each other one that holds as contributing.
2. If a main cause holds, test H5. If H5 holds, report it as contributing. Otherwise, report nothing more.
3. Report at most two contributing causes. If more hold, keep them in table order and drop the rest.
4. If H1 holds and the input lists an open `dias_pago_prom` or `saldo_vencido` alert whose
   `entity` is the entity, set `same_cause_as` to its `id`; if both are listed, choose the
   `dias_pago_prom` one. Otherwise, set none.
5. Add to `assumptions` the limits of `v_cartera_cliente` and `v_dias_pago_mensual` the clock section
   of `data/AGENTS.md` names, and that months with unpaid invoices have no row.
6. State the customer's `saldo_vencido` and the portfolio's `sum(saldo_vencido)`, each as a `Figure`.
7. If H1 to H4 are refuted, answer `no_evidence`. H5 alone is never a cause.
