-- CONSERVAR LOS REGISTROS ANTERIORES BAJO LA ORGANIZACION LOCAL EXISTENTE.
BEGIN;
CREATE TABLE IF NOT EXISTS versiones_esquema (version text PRIMARY KEY, aplicada_en timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS organizaciones (id text PRIMARY KEY, nombre text NOT NULL UNIQUE, simulada boolean NOT NULL DEFAULT true);
INSERT INTO organizaciones(id,nombre,simulada) VALUES ('lab','LAB_LOCAL',false),('empresa_a','Empresa A simulada',true),('empresa_b','Empresa B simulada',true) ON CONFLICT (id) DO NOTHING;
CREATE TABLE IF NOT EXISTS agentes (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tenant_id text NOT NULL REFERENCES organizaciones(id), nombre text NOT NULL, simulado boolean NOT NULL DEFAULT true, UNIQUE(tenant_id,nombre), UNIQUE(tenant_id,id));
CREATE TABLE IF NOT EXISTS sensores_registro (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tenant_id text NOT NULL REFERENCES organizaciones(id), nombre text NOT NULL, agente_id bigint, simulado boolean NOT NULL DEFAULT true, UNIQUE(tenant_id,nombre), UNIQUE(tenant_id,id), FOREIGN KEY(tenant_id,agente_id) REFERENCES agentes(tenant_id,id));
CREATE TABLE IF NOT EXISTS politicas_mtd (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tenant_id text NOT NULL REFERENCES organizaciones(id), sensor_id bigint NOT NULL, nombre text NOT NULL, activa boolean NOT NULL DEFAULT false, UNIQUE(tenant_id,nombre), FOREIGN KEY(tenant_id,sensor_id) REFERENCES sensores_registro(tenant_id,id));
INSERT INTO sensores_registro(tenant_id,nombre,simulado) SELECT DISTINCT tenant_id,sensor,false FROM eventos ON CONFLICT(tenant_id,nombre) DO NOTHING;
ALTER TABLE alertas ADD COLUMN IF NOT EXISTS tenant_id text;
UPDATE alertas a SET tenant_id=e.tenant_id FROM eventos e WHERE a.evento_id=e.id AND a.tenant_id IS NULL;
ALTER TABLE alertas ALTER COLUMN tenant_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS eventos_tenant_id_id ON eventos(tenant_id,id);
CREATE UNIQUE INDEX IF NOT EXISTS alertas_tenant_id_id ON alertas(tenant_id,id);
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='eventos_organizacion_fk') THEN ALTER TABLE eventos ADD CONSTRAINT eventos_organizacion_fk FOREIGN KEY(tenant_id) REFERENCES organizaciones(id); END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='usuarios_organizacion_fk') THEN ALTER TABLE usuarios_locales ADD CONSTRAINT usuarios_organizacion_fk FOREIGN KEY(tenant_id) REFERENCES organizaciones(id); END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='alertas_evento_tenant_fk') THEN ALTER TABLE alertas ADD CONSTRAINT alertas_evento_tenant_fk FOREIGN KEY(tenant_id,evento_id) REFERENCES eventos(tenant_id,id); END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='mtd_config_organizacion_fk') THEN ALTER TABLE mtd_config ADD CONSTRAINT mtd_config_organizacion_fk FOREIGN KEY(tenant_id) REFERENCES organizaciones(id); END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='mtd_acciones_organizacion_fk') THEN ALTER TABLE mtd_acciones ADD CONSTRAINT mtd_acciones_organizacion_fk FOREIGN KEY(tenant_id) REFERENCES organizaciones(id); END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='mtd_acciones_alerta_tenant_fk') THEN ALTER TABLE mtd_acciones ADD CONSTRAINT mtd_acciones_alerta_tenant_fk FOREIGN KEY(tenant_id,alerta_id) REFERENCES alertas(tenant_id,id); END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='mtd_decisiones_alerta_tenant_fk') THEN ALTER TABLE mtd_decisiones ADD CONSTRAINT mtd_decisiones_alerta_tenant_fk FOREIGN KEY(tenant_id,alerta_id) REFERENCES alertas(tenant_id,id); END IF;
END $$;
-- DERIVAR EL PROPIETARIO DE UNA ALERTA DEL EVENTO Y NO DE ENTRADAS DEL CLIENTE.
CREATE OR REPLACE FUNCTION asignar_tenant_alerta() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN SELECT tenant_id INTO STRICT NEW.tenant_id FROM eventos WHERE id=NEW.evento_id; RETURN NEW; END $$;
DROP TRIGGER IF EXISTS alertas_tenant_automatico ON alertas;
CREATE TRIGGER alertas_tenant_automatico BEFORE INSERT OR UPDATE OF evento_id ON alertas FOR EACH ROW EXECUTE FUNCTION asignar_tenant_alerta();
INSERT INTO agentes(tenant_id,nombre) VALUES ('empresa_a','agente-prueba-a'),('empresa_b','agente-prueba-b') ON CONFLICT(tenant_id,nombre) DO NOTHING;
INSERT INTO sensores_registro(tenant_id,nombre,agente_id) SELECT tenant_id,'sensor-prueba',id FROM agentes WHERE nombre IN ('agente-prueba-a','agente-prueba-b') ON CONFLICT(tenant_id,nombre) DO NOTHING;
INSERT INTO politicas_mtd(tenant_id,sensor_id,nombre) SELECT tenant_id,id,'politica-prueba-inactiva' FROM sensores_registro WHERE tenant_id IN ('empresa_a','empresa_b') AND nombre='sensor-prueba' ON CONFLICT(tenant_id,nombre) DO NOTHING;
INSERT INTO eventos(stream,redis_id,sensor,tipo,fecha_evento,simulado,tenant_id,raw_event_id)
VALUES ('fixture-dia15','1-0','sensor-prueba','evento.prueba',now(),true,'empresa_a','fixture-a'),('fixture-dia15','2-0','sensor-prueba','evento.prueba',now(),true,'empresa_b','fixture-b') ON CONFLICT DO NOTHING;
INSERT INTO alertas(evento_id,regla,severidad,descripcion,ip_origen,simulado)
SELECT id,'regla_prueba_tenant','baja','Alerta simulada para verificar propiedad','127.0.0.1',true FROM eventos WHERE stream='fixture-dia15' ON CONFLICT(evento_id,regla) DO NOTHING;
INSERT INTO versiones_esquema(version) VALUES ('011_autenticacion'),('012_gateway_mtd'),('013_controlador_mtd'),('015_multicliente') ON CONFLICT DO NOTHING;
GRANT SELECT(tenant_id) ON alertas TO dn_api_lectura;
COMMIT;
