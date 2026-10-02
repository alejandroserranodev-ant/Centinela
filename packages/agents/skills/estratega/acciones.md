# Estratega: the closed list of actions

These rows are the only actions you may propose. Each comes from the policy section it cites.
`owner` values are the roles the policies name, written as the policies write them. `tramo` is the
step of `FIN-POL-004 §4` the alert's `max_dias_vencido` falls in, as `tramos` in `metricas.yaml`
defines it; `Vigía` sends it with the alert. The formulas are the ones `calcular_impacto`
computes, defined in `packages/tools/AGENTS.md`.

| `metrica` | Condition | `type` | `parameters` | Formula | Policy |
|---|---|---|---|---|---|
| `margen_pct` | the cause names SKUs whose cost rose | `price_change_draft` | `sku`, `price_increase_pct` | `traslado_costo` | `OPE-POL-007 §4` |
| `margen_pct` | the line is below `margen_minimo_pct` | `price_change_draft` | `linea`, `price_increase_pct` | `precio_a_margen_minimo` | `OPE-POL-007 §4` |
| `margen_pct` | always | `task` | `owner: Comercial` | none | `OPE-POL-007 §4` |
| `variacion_costo_pct` | always | `price_change_draft` | `sku`, `price_increase_pct` | `traslado_costo` | `OPE-POL-007 §4` |
| `saldo_vencido` | `tramo` is `tramo_1` | `email_draft` | `recipient: cliente_id`, `vendedor_id` | `cartera_vencida` | `FIN-POL-004 §4` |
| `saldo_vencido` | `tramo` is `tramo_2` | `task` | `owner: Analista de cartera`, `cliente_id`, `vendedor_id` | `cartera_vencida` | `FIN-POL-004 §4` |
| `saldo_vencido` | `tramo` is `tramo_3` | `task` | `owner: Jefe de cartera`, `cliente_id` (new orders cash only) | `cartera_vencida` | `FIN-POL-004 §4` |
| `saldo_vencido` | `tramo` is `tramo_4` | `task` | `owner: Dirección Financiera`, `cliente_id` (block dispatches) | `cartera_vencida` | `FIN-POL-004 §4` |
| `saldo_vencido` | `saldo_abierto` > `cupo_credito` | `task` | `owner: Dirección Financiera`, `cliente_id` | none | `FIN-POL-004 §3` |
| `concentracion_vencida_pct` | always | `task` | `owner: Jefe de cartera`, `cliente_id` | `cartera_vencida` | `FIN-POL-004 §5` |
| `dias_pago_prom` | always | `email_draft` | `recipient: cliente_id`, `vendedor_id` | none | `FIN-POL-004 §5` |
| `cobertura_dias` | the cause names an open order | `purchase_order_draft` | `oc_id`, `proveedor_id`, `sku`, `warehouse: bodega_id` (expedite) | `ventas_protegidas` | `OPE-POL-007 §2` |
| `cobertura_dias` | the cause names no open order | `purchase_order_draft` | `proveedor_id`, `sku`, `warehouse: bodega_id`, `units` | `ventas_protegidas` | `OPE-POL-007 §2` |
| `cobertura_dias` | `clase_abc` is `B` | `task` | `owner: Compras`, `sku` (review reorder point) | none | `OPE-POL-007 §2` |
| `dias_retraso` | always | `email_draft` | `recipient: proveedor_id`, `oc_id` | none | `OPE-POL-007 §3` |
| `dias_retraso` | always | `task` | `owner: Compras`, `oc_id` (partial delivery or another supplier) | `ventas_protegidas` | `OPE-POL-007 §3` |
| `descuento_en_exceso` | always | `task` | `owner: Control Comercial`, `vendedor_id` | `descuento_recuperado` | `COM-POL-002 §5` |
| `descuento_en_exceso` | the cause shows two consecutive weeks | `task` | `owner: Gerencia Comercial`, `vendedor_id` (quote under review) | `descuento_recuperado` | `COM-POL-002 §5` |
| `margen_bruto_negativo` | always | `task` | `owner: Gerencia Comercial`, `sku` | `venta_bajo_costo` | `COM-POL-002 §4` |
| `veces_intervalo_habitual` | always | `task` | `owner: vendedor_id`, `cliente_id` | `compra_recuperada` | none; the policies prescribe no action, so `description` says the action is Centinela's proposal |

`units` in a new order is `demanda_prom_30d` times the class minimum coverage minus `existencia`,
computed by `calcular_impacto`, never chosen.
