-- RESTRINGIR EL GATEWAY A UN SENSOR Y TRES PUERTOS DE LABORATORIO.
CREATE TABLE IF NOT EXISTS mtd_config (
  tenant_id TEXT NOT NULL,
  sensor TEXT NOT NULL CHECK (sensor = 'cowrie-ssh'),
  puerto INTEGER NOT NULL CHECK (puerto IN (2201,2202,2203)),
  actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,sensor)
);
INSERT INTO mtd_config(tenant_id,sensor,puerto) VALUES ('lab','cowrie-ssh',2201)
ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS mtd_acciones (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id TEXT NOT NULL DEFAULT 'lab',
  sensor TEXT NOT NULL CHECK (sensor = 'cowrie-ssh'),
  puerto_destino INTEGER NOT NULL CHECK (puerto_destino IN (2201,2202,2203)),
  puerto_anterior INTEGER,
  tipo TEXT NOT NULL CHECK (tipo IN ('manual','adaptativo','periodico','reversion')),
  estado TEXT NOT NULL DEFAULT 'solicitada' CHECK (estado IN ('solicitada','en_proceso','aplicada','fallida','revertida')),
  motivo TEXT NOT NULL,
  clave TEXT NOT NULL UNIQUE,
  solicitado_por BIGINT REFERENCES usuarios_locales(id),
  alerta_id BIGINT REFERENCES alertas(id),
  solicitada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
  iniciada_en TIMESTAMPTZ,
  terminada_en TIMESTAMPTZ,
  duracion_ms INTEGER,
  detalle TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS mtd_acciones_estado_idx ON mtd_acciones(estado,id);
