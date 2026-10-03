-- Written by `uv run python -m centinela_tools.generate` in packages/tools, from data/kernel/fuentes.yaml,
-- data/metricas.yaml and the views of data/sql/03_capa_semantica.sql and data/sql/04_vistas_causa.sql.
-- Never edit it by hand: the defect is in those sources. Applied after 04_vistas_causa.sql.
DO $roles$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'centinela_lector') THEN
    CREATE ROLE centinela_lector LOGIN PASSWORD 'centinela_lector';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'centinela_kernel') THEN
    CREATE ROLE centinela_kernel LOGIN PASSWORD 'centinela_kernel';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'centinela_propietario') THEN
    CREATE ROLE centinela_propietario NOLOGIN;
  END IF;
  EXECUTE format('REVOKE TEMPORARY ON DATABASE %I FROM PUBLIC', current_database());
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO centinela_lector, centinela_kernel', current_database());
END
$roles$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA centinela TO centinela_lector, centinela_kernel, centinela_propietario;
GRANT SELECT ("vendedor_id", "region") ON "centinela"."vendedores" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("cliente_id", "nombre", "segmento", "ciudad", "region", "vendedor_id", "plazo_dias", "cupo_credito", "fecha_alta") ON "centinela"."clientes" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("proveedor_id", "nombre", "lead_time_dias", "pais") ON "centinela"."proveedores" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("sku", "nombre", "linea", "proveedor_id", "clase_abc", "unidad") ON "centinela"."productos" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("bodega_id", "nombre", "ciudad") ON "centinela"."bodegas" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("sku", "fecha_vigencia", "precio_lista") ON "centinela"."lista_precios" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("sku", "proveedor_id", "fecha_vigencia", "costo_unitario") ON "centinela"."costos_proveedor" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("oc_id", "proveedor_id", "sku", "bodega_id", "fecha_oc", "fecha_esperada", "fecha_recibida", "cantidad", "costo_unitario", "estado") ON "centinela"."ordenes_compra" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("pedido_id", "fecha", "cliente_id", "vendedor_id", "ciudad", "canal", "estado") ON "centinela"."pedidos" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("pedido_id", "linea_n", "sku", "cantidad", "precio_lista", "precio_unitario", "descuento_pct", "aprobacion_especial", "valor_neto", "costo_unitario") ON "centinela"."pedidos_detalle" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("factura_id", "pedido_id", "cliente_id", "fecha_factura", "fecha_vencimiento", "valor_neto", "iva", "valor_total") ON "centinela"."facturas" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("pago_id", "factura_id", "fecha_pago", "valor", "medio_pago") ON "centinela"."pagos" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("fecha", "bodega_id", "sku", "existencia_inicial", "entradas", "salidas", "existencia_final") ON "centinela"."inventario_diario" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("segmento", "tope_descuento_pct") ON "centinela"."ref_topes_descuento" TO centinela_kernel, centinela_propietario;
GRANT SELECT ("linea", "margen_minimo_pct") ON "centinela"."ref_margen_minimo_linea" TO centinela_kernel, centinela_propietario;
ALTER FUNCTION centinela.fecha_corte() SECURITY DEFINER SET search_path = centinela, pg_temp;
ALTER FUNCTION centinela.fecha_corte() OWNER TO centinela_propietario;
GRANT SELECT ON "centinela"."v_ventas" TO centinela_lector;
GRANT SELECT ON "centinela"."v_margen_semanal_linea" TO centinela_lector;
GRANT SELECT ON "centinela"."v_cartera_cliente" TO centinela_lector;
GRANT SELECT ON "centinela"."v_dias_pago_mensual" TO centinela_lector;
GRANT SELECT ON "centinela"."v_cobertura_inventario" TO centinela_lector;
GRANT SELECT ON "centinela"."v_descuentos_fuera_politica" TO centinela_lector;
GRANT SELECT ON "centinela"."v_actividad_cliente" TO centinela_lector;
GRANT SELECT ON "centinela"."v_costo_sku" TO centinela_lector;
GRANT SELECT ON "centinela"."v_precio_sku" TO centinela_lector;
GRANT SELECT ON "centinela"."v_ordenes_compra" TO centinela_lector;
GRANT SELECT ON "centinela"."v_margen_minimo_linea" TO centinela_lector;
