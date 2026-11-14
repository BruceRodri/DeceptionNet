-- IDENTIFICAR CADA MENSAJE DEL FLUJO PARA EVITAR DUPLICADOS.
CREATE TABLE IF NOT EXISTS eventos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stream VARCHAR(128) NOT NULL,
    redis_id VARCHAR(64) NOT NULL,
    sensor TEXT NOT NULL,
    tipo TEXT NOT NULL,
    fecha_evento TIMESTAMPTZ NOT NULL,
    fecha_recepcion TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_origen TEXT,
    sesion TEXT,
    usuario TEXT,
    comando TEXT,
    simulado BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (stream, redis_id)
);
CREATE INDEX IF NOT EXISTS eventos_reglas_idx
    ON eventos (tipo, ip_origen, simulado, fecha_evento);

-- RELACIONAR CADA ALERTA CON EL EVENTO QUE DISPARO LA REGLA.
CREATE TABLE IF NOT EXISTS alertas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evento_id BIGINT NOT NULL REFERENCES eventos(id),
    regla TEXT NOT NULL,
    severidad TEXT NOT NULL CHECK (severidad IN ('baja', 'media', 'alta')),
    descripcion TEXT NOT NULL,
    ip_origen TEXT NOT NULL,
    fecha_alerta TIMESTAMPTZ NOT NULL DEFAULT now(),
    simulado BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (evento_id, regla)
);
CREATE INDEX IF NOT EXISTS alertas_reglas_idx
    ON alertas (regla, ip_origen, simulado, fecha_alerta);

-- AMPLIAR ALERTAS SIN MODIFICAR NI INVENTAR EVIDENCIA DE REGISTROS ANTERIORES.
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS estado TEXT NOT NULL DEFAULT 'nueva';
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS umbral INTEGER;
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS ventana_segundos INTEGER;
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS cantidad INTEGER;
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS inicio_ventana TIMESTAMPTZ;
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS fin_ventana TIMESTAMPTZ;
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS evidencia JSONB;
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS clave_deduplicacion TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS alertas_clave_deduplicacion_idx
    ON alertas (clave_deduplicacion) WHERE clave_deduplicacion IS NOT NULL;
CREATE INDEX IF NOT EXISTS eventos_sensor_reglas_idx
    ON eventos (sensor, tipo, ip_origen, simulado, fecha_evento);

-- RESERVAR UN IDENTIFICADOR LOCAL DE TENANT Y DEDUPLICAR LA FUENTE.
ALTER TABLE eventos ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'lab';
ALTER TABLE eventos ADD COLUMN IF NOT EXISTS raw_event_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS eventos_fuente_unica_idx
    ON eventos (tenant_id, sensor, raw_event_id) WHERE raw_event_id IS NOT NULL;

-- NOTIFICAR SOLO EL IDENTIFICADOR DE LAS ALERTAS AL CONFIRMAR LA TRANSACCION.
CREATE OR REPLACE FUNCTION notificar_alerta_local() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify('dn_alertas', NEW.id::text);
    RETURN NEW;
END;
$$;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='alertas_notificar_local'
                   AND tgrelid='alertas'::regclass AND NOT tgisinternal) THEN
        CREATE TRIGGER alertas_notificar_local AFTER INSERT ON alertas
            FOR EACH ROW EXECUTE FUNCTION notificar_alerta_local();
    END IF;
END $$;

-- Valores opcionales del laboratorio; sin filas se conservan los valores de entorno.
CREATE TABLE IF NOT EXISTS configuracion_alertas (
 regla text PRIMARY KEY CHECK (regla IN ('multiples_conexiones','intento_acceso_web_local','intento_acceso_mysql_local')),
 umbral integer NOT NULL CHECK (umbral BETWEEN 1 AND 1000),
 ventana_segundos integer NOT NULL CHECK (ventana_segundos BETWEEN 10 AND 86400),
 actualizado_en timestamptz NOT NULL DEFAULT now()
);
