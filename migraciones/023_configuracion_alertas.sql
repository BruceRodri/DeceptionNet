BEGIN;
CREATE TABLE IF NOT EXISTS configuracion_alertas (
 regla text PRIMARY KEY CHECK (regla IN ('multiples_conexiones','intento_acceso_web_local','intento_acceso_mysql_local')),
 umbral integer NOT NULL CHECK (umbral BETWEEN 1 AND 1000),
 ventana_segundos integer NOT NULL CHECK (ventana_segundos BETWEEN 10 AND 86400),
 actualizado_en timestamptz NOT NULL DEFAULT now()
);
REVOKE ALL ON configuracion_alertas FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE ON configuracion_alertas TO dn_api_auth;
INSERT INTO versiones_esquema(version) VALUES ('023_configuracion_alertas') ON CONFLICT DO NOTHING;
COMMIT;
