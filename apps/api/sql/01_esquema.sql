CREATE SCHEMA IF NOT EXISTS api;

CREATE TABLE IF NOT EXISTS api.simulacion (
  id boolean PRIMARY KEY DEFAULT true CHECK (id),
  dia_actual date NOT NULL
);

CREATE TABLE IF NOT EXISTS api.alertas (
  id text PRIMARY KEY DEFAULT ('alerta_' || replace(gen_random_uuid()::text, '-', '')),
  status text NOT NULL CHECK (status IN ('new', 'analyzing', 'proposed', 'approved', 'rejected', 'executed')),
  cuerpo jsonb NOT NULL,
  costos jsonb NOT NULL DEFAULT '[]'::jsonb,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alertas_status ON api.alertas (status);

CREATE TABLE IF NOT EXISTS api.bitacora (
  id bigserial PRIMARY KEY,
  alerta_id text NOT NULL REFERENCES api.alertas (id),
  tipo text NOT NULL CHECK (tipo IN ('alert', 'evidence', 'proposal', 'decision', 'action', 'result')),
  actor jsonb NOT NULL,
  detalle text NOT NULL,
  query_id text,
  dia_simulado date NOT NULL,
  creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bitacora_alerta ON api.bitacora (alerta_id);
