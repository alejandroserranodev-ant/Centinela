# Analista: `veces_intervalo_habitual`

The entity is a `cliente_id`. The symptom starts on its `ultima_compra` in `v_actividad_cliente`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the customer was already buying less | `v_ventas` where `cliente_id` = the entity and `fecha <= :dia`, `sum(valor_neto)` by month | the three months before `ultima_compra` are below the mean of the six before them | they are not |
| H2 | it dropped specific lines first | `v_ventas` where `cliente_id` = the entity, `sum(valor_neto)` by `linea` and month | a `linea` it bought every month stops before `ultima_compra` | no line stops early |
| H3 | it is blocked by debt | `v_cartera_cliente` where `cliente_id` = the entity | `max_dias_vencido` > 0 or `saldo_abierto` > `cupo_credito` | neither |
| H4 | it was served worse | `v_descuentos_fuera_politica` and `v_ventas` where `cliente_id` = the entity, the last six months | its mean `descuento_pct` fell before `ultima_compra` | it did not |

1. Report H3 as the main cause if it holds: a customer with debt is not a customer who left. Set
   `same_cause_as` to an open `saldo_vencido` alert of the same customer.
2. Otherwise, report H1 as main and H2 and H4 as contributing when they hold.
3. The data holds no reason the customer gives. Never state one.
4. If every hypothesis is refuted, answer `no_evidence` with `reason`: "El cliente dejó de comprar sin una señal previa en los datos."
