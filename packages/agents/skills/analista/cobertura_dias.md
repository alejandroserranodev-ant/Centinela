# Analista: `cobertura_dias`

The entity is a `sku` in a `bodega_id`. The symptom is `cobertura_dias` in `v_cobertura_inventario` on `:dia`.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | an order is late | `v_ordenes_compra` where `sku` and `bodega_id` = the entity and `recibida` is false | a row has `dias_retraso` > 0 | no row has |
| H2 | the supplier stopped delivering | `v_ordenes_compra` where `sku` = the entity, the last 90 days to `:dia` | the last received order is older than twice `lead_time_dias` and an open order exists | an order was received within twice `lead_time_dias` |
| H3 | a delivery arrived short | `v_ordenes_compra` where `sku` and `bodega_id` = the entity and `recibida` is true, the last 60 days | the received `cantidad` of the last order is below the mean of the previous ones | it is not below |
| H4 | demand rose | `v_ventas` where `sku` = the entity and `fecha <= :dia`, `sum(cantidad)` by week | the last four weeks exceed the mean of the eight before them | they do not |
| H5 | no order was placed | `v_ordenes_compra` where `sku` and `bodega_id` = the entity, the last 60 days | no row exists | a row exists |

1. Test H1, H2, H3, H5 before H4. A supply cause outranks a demand cause.
2. Name the `proveedor_id`, the `oc_id` and `lead_time_dias` in the evidence.
3. If `unidades_pendientes` > 0, add to `assumptions` the limit of `v_cobertura_inventario` the
   clock section of `data/AGENTS.md` names.
4. If every hypothesis is refuted, answer `no_evidence`.
