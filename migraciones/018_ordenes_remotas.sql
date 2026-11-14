-- RESTRINGIR LAS ORDENES A SENUEL0S SIMULADOS Y PUERTOS PREDEFINIDOS.
BEGIN;
CREATE TABLE IF NOT EXISTS ordenes_remotas (
 id uuid PRIMARY KEY, tenant_id text NOT NULL REFERENCES organizaciones(id), sensor text NOT NULL,
 puerto integer NOT NULL CHECK (puerto IN (2301,2302)), clave text NOT NULL, solicitado_por bigint NOT NULL REFERENCES usuarios_locales(id),
 creada_en timestamptz NOT NULL DEFAULT now(), vence_en timestamptz NOT NULL,
 estado text NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','entregada','aplicada','fallida','revertida','caducada')),
 resultado text, confirmada_en timestamptz, UNIQUE(tenant_id,clave),
 CHECK ((tenant_id='empresa_a' AND sensor='sensor-remoto-a') OR (tenant_id='empresa_b' AND sensor='sensor-remoto-b'))
);
CREATE TABLE IF NOT EXISTS ordenes_remotas_historial (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, orden_id uuid NOT NULL REFERENCES ordenes_remotas(id),
 tenant_id text NOT NULL REFERENCES organizaciones(id), estado text NOT NULL, fecha timestamptz NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION registrar_estado_remoto() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN IF TG_OP='INSERT' OR NEW.estado IS DISTINCT FROM OLD.estado THEN
 INSERT INTO ordenes_remotas_historial(orden_id,tenant_id,estado) VALUES(NEW.id,NEW.tenant_id,NEW.estado);
 END IF; RETURN NEW; END $$;
DROP TRIGGER IF EXISTS ordenes_registrar_estado ON ordenes_remotas;
CREATE TRIGGER ordenes_registrar_estado AFTER INSERT OR UPDATE OF estado ON ordenes_remotas FOR EACH ROW EXECUTE FUNCTION registrar_estado_remoto();
GRANT SELECT,INSERT ON ordenes_remotas TO dn_api_auth;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='dn_ingreso_agentes') THEN
 CREATE ROLE dn_ingreso_agentes LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
END IF; END $$;
GRANT USAGE ON SCHEMA public TO dn_ingreso_agentes;
GRANT SELECT,UPDATE ON ordenes_remotas TO dn_ingreso_agentes;
INSERT INTO versiones_esquema(version) VALUES ('018_ordenes_remotas') ON CONFLICT DO NOTHING;
COMMIT;
