# Analista: `variacion_costo_pct`

The entity is a `sku`. The symptom starts on the `fecha_vigencia` of the cost row the alert cites.

| # | Hypothesis | Query | Holds when | Refuted when |
|---|---|---|---|---|
| H1 | the supplier raised the cost and the price did not follow | `v_precio_sku` where `sku` = the entity and `fecha_vigencia` between the symptom start and `:dia` | no row has `variacion_pct` > 0 | a row has `variacion_pct` > 0 |
| H2 | the same supplier raised other SKUs | `v_costo_sku` where `proveedor_id` = the entity's supplier and `fecha_vigencia` within 14 days of the symptom start | another `sku` has `variacion_pct` > 0 | no other `sku` has |

1. H1 is the main cause. Count business days from the symptom start to `:dia`, Monday to Friday,
   and add to `assumptions`: "Días hábiles contados de lunes a viernes, sin festivos."
2. If H2 holds, report it as contributing and set `same_cause_as` to any open alert on those SKUs.
3. If H1 is refuted, answer `no_evidence` with `reason`: "El precio se revisó después del alza de costo."
