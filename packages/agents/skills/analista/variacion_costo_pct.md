# Analista: `variacion_costo_pct`

The entity is a `sku`. The symptom starts on the `fecha_vigencia` of the cost row the alert cites.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the supplier raised the cost and the price did not follow | `v_precio_sku` where `sku` = the entity and `fecha_vigencia` between the symptom start and `:dia` | no row has `variacion_pct` > 0 | a row has `variacion_pct` > 0 |
| H2 | the same supplier raised other SKUs | `v_costo_sku` where `proveedor_id` = the entity's supplier and `fecha_vigencia` within 14 days of the symptom start | another `sku` has `variacion_pct` above the share the `umbral_alerta` of `variacion_costo_pct` in `data/metricas.yaml` names | no other `sku` has |

1. H1 is the main cause. Never count business days. Add to `assumptions`: "Días hábiles contados de lunes a viernes, sin festivos."
2. If H2 holds, report it as contributing. Otherwise, report nothing more.
3. If the input lists an open `margen_pct` alert whose `entity` is the entity's `linea`, set
   `same_cause_as` to its `id`. Otherwise, set none.
4. If H1 is refuted, answer `no_evidence` with `reason`: "El precio se revisó después del alza de costo."
