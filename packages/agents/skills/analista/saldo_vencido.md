# Analista: `saldo_vencido`

The entity is a `cliente_id`. The symptom starts on the first `mes_factura` whose `dias_pago_prom`
exceeds `plazo_dias`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the customer pays slower | `v_dias_pago_mensual` where `cliente_id` = the entity and `mes_factura <= :dia`, ordered by `mes_factura` | `dias_pago_prom` rises across the last three months and exceeds `plazo_dias` from `v_cartera_cliente` | it does not rise, or it stays within `plazo_dias` |
| H2 | the customer buys above its limit | `v_cartera_cliente` where `cliente_id` = the entity | `saldo_abierto` > `cupo_credito` | `saldo_abierto` <= `cupo_credito` |
| H3 | the customer bought more, not paid less | `v_ventas` where `cliente_id` = the entity and `fecha <= :dia`, `sum(valor_neto)` by month | the last three months exceed the mean of the previous six and H1 is refuted | they do not |

1. Report H1 as the main cause if it holds. Report H2 as contributing if it holds.
2. Report H3 as main only if H1 is refuted.
3. Add to `assumptions` the limit of `v_dias_pago_mensual` the clock section of `data/AGENTS.md` names.
4. If H1, H2 and H3 are refuted, answer `no_evidence`.
