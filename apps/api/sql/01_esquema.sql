CREATE SCHEMA IF NOT EXISTS api;

CREATE TABLE IF NOT EXISTS api.simulacion (
  id boolean PRIMARY KEY DEFAULT true CHECK (id),
  dia_actual date NOT NULL
);

CREATE TABLE IF NOT EXISTS api.alertas (
  id text PRIMARY KEY DEFAULT ('alerta_' || replace(gen_random_uuid()::text, '-', '')),
  status text NOT NULL,
  cuerpo jsonb NOT NULL,
  costos jsonb NOT NULL DEFAULT '[]'::jsonb,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE api.alertas DROP CONSTRAINT IF EXISTS alertas_status_check;
ALTER TABLE api.alertas ADD CONSTRAINT alertas_status_check
  CHECK (status IN ('new', 'analyzing', 'proposed', 'approved', 'rejected', 'executed', 'merged'));

CREATE INDEX IF NOT EXISTS idx_alertas_status ON api.alertas (status);

CREATE TABLE IF NOT EXISTS api.bitacora (
  id bigserial PRIMARY KEY,
  alerta_id text REFERENCES api.alertas (id),
  tipo text NOT NULL,
  actor jsonb NOT NULL,
  detalle text NOT NULL,
  query_id text,
  dia_simulado date NOT NULL,
  creado_en timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE api.bitacora ALTER COLUMN alerta_id DROP NOT NULL;
ALTER TABLE api.bitacora ADD COLUMN IF NOT EXISTS figuras jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE api.bitacora DROP CONSTRAINT IF EXISTS bitacora_tipo_check;
ALTER TABLE api.bitacora ADD CONSTRAINT bitacora_tipo_check
  CHECK (tipo IN ('alert', 'evidence', 'proposal', 'decision', 'action', 'result', 'question', 'answer', 'refusal', 'configuracion', 'costo'));

CREATE INDEX IF NOT EXISTS idx_bitacora_alerta ON api.bitacora (alerta_id);

CREATE TABLE IF NOT EXISTS api.consultas (
  query_id text PRIMARY KEY,
  kpi text NOT NULL,
  dia date NOT NULL,
  consulta text NOT NULL,
  creado_en timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE api.consultas ADD COLUMN IF NOT EXISTS fuente text NOT NULL DEFAULT 'kernel';
ALTER TABLE api.consultas ADD COLUMN IF NOT EXISTS filas jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE api.consultas DROP CONSTRAINT IF EXISTS consultas_fuente_check;
ALTER TABLE api.consultas ADD CONSTRAINT consultas_fuente_check CHECK (fuente IN ('kernel', 'alertas'));

CREATE TABLE IF NOT EXISTS api.configuracion (
  id boolean PRIMARY KEY DEFAULT true CHECK (id),
  cuerpo jsonb NOT NULL,
  guardado_por jsonb,
  actualizado_en timestamptz
);
