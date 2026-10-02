# Analista: `dias_pago_prom`

The entity is a `cliente_id`. The symptom starts on the first `mes_factura` whose `dias_pago_prom`
exceeds its historical mean by the share `metricas.yaml` names.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | a sustained slowdown | `v_dias_pago_mensual` where `cliente_id` = the entity and `mes_factura <= :dia` | `dias_pago_prom` is above the historical mean in each of the last three months | it is above in fewer than three |
| H2 | the customer is also buying less | `v_actividad_cliente` where `cliente_id` = the entity | `veces_intervalo_habitual` > 1 | `veces_intervalo_habitual` <= 1 |
| H3 | the slowdown is still within the term | `v_cartera_cliente` where `cliente_id` = the entity | `max_dias_vencido` <= 0 | `max_dias_vencido` > 0 |

1. H1 is the main cause if it holds. If it is refuted, answer `no_evidence` with `reason`:
   "El aumento es de un solo mes."
2. Report H2 as contributing if it holds, and set `same_cause_as` to an open
   `veces_intervalo_habitual` alert of the same customer.
3. If H3 holds, say in `sentence` that the customer still pays within its term.
4. Add to `assumptions` the limit of `v_dias_pago_mensual` the clock section of `data/AGENTS.md` names.
