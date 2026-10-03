# Analista: `saldo_vencido`

The entity is a `cliente_id`. The symptom starts on the first `mes_factura` whose `dias_pago_prom`
exceeds `plazo_dias`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the customer pays slower | `v_dias_pago_mensual` where `cliente_id` = the entity and `mes_factura <= :dia`, the last three rows by `mes_factura` | `dias_pago_prom` rises across those three rows and the last exceeds `plazo_dias` from `v_cartera_cliente` | it does not rise, it stays within `plazo_dias`, or fewer than three rows exist |
| H2 | the customer buys above its limit | `v_cartera_cliente` where `cliente_id` = the entity | `saldo_abierto` > `cupo_credito` | `saldo_abierto` <= `cupo_credito` |
| H3 | the customer bought more, not paid less | `v_ventas` where `cliente_id` = the entity and `fecha <= :dia`, `sum(valor_neto)` by month | the last three months exceed the mean of the previous six and H1 is refuted | they do not |

1. Report H1 as the main cause if it holds. Report H2 as contributing if it holds.
2. Report H3 as main only if H1 is refuted. If H1 and H3 are refuted and H2 holds, report H2 as main.
3. If H1 holds and the input lists an open `dias_pago_prom` or `concentracion_vencida_pct` alert
   whose `entidad` is the entity, set `same_cause_as` to its `id`; if both are listed, choose the
   `dias_pago_prom` one. Otherwise, set none.
4. Add to `assumptions` the limits of `v_dias_pago_mensual` and `v_cartera_cliente` the clock section
   of `data/AGENTS.md` names, and that months whose invoices are still unpaid have no row.
5. If H1, H2 and H3 are refuted, answer `no_evidence`.
