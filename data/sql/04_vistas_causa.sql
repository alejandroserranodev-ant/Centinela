-- Centinela · cause views: read-only exposure of the CSVs the kit's views leave out.
-- They add no data and no table; each one reads only tables 01_esquema.sql creates.
-- Every row is bounded by centinela.fecha_corte(), and no status is read from an `estado`
-- column, because those columns hold the state at the end of the dataset.
-- Run after 03_capa_semantica.sql.
SET search_path TO centinela;

CREATE OR REPLACE VIEW v_costo_sku AS
WITH c AS (SELECT c.sku, c.proveedor_id, c.fecha_vigencia, c.costo_unitario,
                  lag(c.costo_unitario) OVER (PARTITION BY c.sku ORDER BY c.fecha_vigencia) AS costo_anterior,
                  lead(c.fecha_vigencia) OVER (PARTITION BY c.sku ORDER BY c.fecha_vigencia) AS siguiente
           FROM costos_proveedor c WHERE c.fecha_vigencia <= fecha_corte())
SELECT c.sku, pr.nombre AS producto, pr.linea, pr.clase_abc, c.proveedor_id, pv.nombre AS proveedor,
       pv.lead_time_dias, c.fecha_vigencia, c.costo_unitario, c.costo_anterior,
       round(100 * (c.costo_unitario / nullif(c.costo_anterior, 0) - 1), 2) AS variacion_pct,
       c.siguiente IS NULL AS vigente
FROM c JOIN productos pr USING (sku) JOIN proveedores pv ON pv.proveedor_id = c.proveedor_id;

CREATE OR REPLACE VIEW v_precio_sku AS
WITH l AS (SELECT sku, fecha_vigencia, precio_lista,
                  lag(precio_lista) OVER (PARTITION BY sku ORDER BY fecha_vigencia) AS precio_anterior,
                  lead(fecha_vigencia) OVER (PARTITION BY sku ORDER BY fecha_vigencia) AS siguiente
           FROM lista_precios WHERE fecha_vigencia <= fecha_corte())
SELECT l.sku, pr.nombre AS producto, pr.linea, l.fecha_vigencia, l.precio_lista, l.precio_anterior,
       round(100 * (l.precio_lista / nullif(l.precio_anterior, 0) - 1), 2) AS variacion_pct,
       l.siguiente IS NULL AS vigente
FROM l JOIN productos pr USING (sku);

CREATE OR REPLACE VIEW v_ordenes_compra AS
SELECT o.oc_id, o.proveedor_id, pv.nombre AS proveedor, pv.lead_time_dias, o.sku, pr.nombre AS producto,
       pr.linea, pr.clase_abc, o.bodega_id, o.fecha_oc, o.fecha_esperada,
       CASE WHEN o.fecha_recibida <= fecha_corte() THEN o.fecha_recibida END AS fecha_recibida,
       o.cantidad, o.costo_unitario,
       o.fecha_recibida IS NOT NULL AND o.fecha_recibida <= fecha_corte() AS recibida,
       CASE WHEN o.fecha_recibida <= fecha_corte() THEN greatest(o.fecha_recibida - o.fecha_esperada, 0)
            WHEN o.fecha_esperada < fecha_corte() THEN fecha_corte() - o.fecha_esperada
            ELSE 0 END AS dias_retraso
FROM ordenes_compra o JOIN productos pr USING (sku) JOIN proveedores pv ON pv.proveedor_id = o.proveedor_id
WHERE o.fecha_oc <= fecha_corte();

CREATE OR REPLACE VIEW v_margen_minimo_linea AS
SELECT linea, margen_minimo_pct FROM ref_margen_minimo_linea;
