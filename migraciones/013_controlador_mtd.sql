-- REGISTRAR DECISIONES Y EVITAR PROCESAR UNA ALERTA DOS VECES.
ALTER TABLE mtd_config ADD COLUMN IF NOT EXISTS gateway_ip TEXT;
CREATE TABLE IF NOT EXISTS mtd_control_estado (
  tenant_id TEXT PRIMARY KEY,
  ultima_alerta BIGINT NOT NULL DEFAULT 0
);
INSERT INTO mtd_control_estado(tenant_id,ultima_alerta)
SELECT 'lab',COALESCE(max(id),0) FROM alertas ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS mtd_decisiones (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  alerta_id BIGINT NOT NULL REFERENCES alertas(id),
  sensor TEXT NOT NULL,
  puntuacion INTEGER NOT NULL,
  resultado TEXT NOT NULL CHECK (resultado IN ('sin_accion','cooldown','solicitada')),
  motivo TEXT NOT NULL,
  accion_id BIGINT REFERENCES mtd_acciones(id),
  creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,alerta_id)
);
