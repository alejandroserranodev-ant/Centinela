# Analista: `concentracion_vencida_pct`

The entity is a `cliente_id`. The symptom is its share of the sum of `saldo_vencido` over every
customer in `v_cartera_cliente`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the customer's own debt grew | `v_dias_pago_mensual` where `cliente_id` = the entity and `mes_factura <= :dia` | `dias_pago_prom` rises across the last three months | it does not rise |
| H2 | the rest of the portfolio paid, so the share rose | `v_cartera_cliente`, `sum(saldo_vencido)` of every other customer | H1 is refuted and the customer's `max_dias_vencido` is the highest in the portfolio | H1 holds |

1. Report H1 as the main cause if it holds. Otherwise, report H2.
2. State the customer's `saldo_vencido` and the portfolio's `sum(saldo_vencido)`, each as a `Figure`.
3. If H1 and H2 are refuted, answer `no_evidence`.
