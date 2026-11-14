-- ASIGNAR UNA IDENTIDAD DE LECTURA DISTINTA A CADA ORGANIZACION.
BEGIN;
DO $$ DECLARE r text; BEGIN
 FOREACH r IN ARRAY ARRAY['dn_rls_lab','dn_rls_empresa_a','dn_rls_empresa_b'] LOOP
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r) THEN EXECUTE format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',r); END IF;
  EXECUTE format('GRANT USAGE ON SCHEMA public TO %I',r);
  EXECUTE format('GRANT SELECT (id,sensor,tipo,fecha_evento,fecha_recepcion,ip_origen,simulado,tenant_id) ON eventos TO %I',r);
  EXECUTE format('GRANT SELECT (id,evento_id,regla,severidad,descripcion,ip_origen,fecha_alerta,simulado,estado,umbral,ventana_segundos,cantidad,tenant_id) ON alertas TO %I',r);
  EXECUTE format('GRANT SELECT ON politicas_mtd,sensores_registro TO %I',r);
 END LOOP;
END $$;
ALTER TABLE auditoria_local ADD COLUMN IF NOT EXISTS tenant_id text REFERENCES organizaciones(id);
UPDATE auditoria_local a SET tenant_id=coalesce(u.tenant_id,'lab') FROM usuarios_locales u WHERE a.usuario_id=u.id AND a.tenant_id IS NULL;
UPDATE auditoria_local SET tenant_id='lab' WHERE tenant_id IS NULL;
ALTER TABLE auditoria_local ALTER COLUMN tenant_id SET NOT NULL;
CREATE OR REPLACE FUNCTION asignar_tenant_auditoria() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.usuario_id IS NULL THEN NEW.tenant_id='lab';
 ELSE SELECT tenant_id INTO STRICT NEW.tenant_id FROM usuarios_locales WHERE id=NEW.usuario_id; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS auditoria_tenant_automatico ON auditoria_local;
CREATE TRIGGER auditoria_tenant_automatico BEFORE INSERT ON auditoria_local FOR EACH ROW EXECUTE FUNCTION asignar_tenant_auditoria();
GRANT SELECT(id,usuario_id,accion,resultado,fecha,detalle,tenant_id) ON auditoria_local TO dn_rls_lab,dn_rls_empresa_a,dn_rls_empresa_b;
-- LOS SERVICIOS INTERNOS SOLO RECIBEN LAS FILAS NECESARIAS PARA EL LABORATORIO.
DO $$ DECLARE tabla text; BEGIN
 FOREACH tabla IN ARRAY ARRAY['eventos','alertas','politicas_mtd','sensores_registro','auditoria_local'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',tabla);
  EXECUTE format('DROP POLICY IF EXISTS lectura_por_identidad ON %I',tabla);
  EXECUTE format($p$CREATE POLICY lectura_por_identidad ON %I FOR SELECT TO dn_rls_lab,dn_rls_empresa_a,dn_rls_empresa_b USING (tenant_id = CASE current_user WHEN 'dn_rls_lab' THEN 'lab' WHEN 'dn_rls_empresa_a' THEN 'empresa_a' WHEN 'dn_rls_empresa_b' THEN 'empresa_b' ELSE NULL END)$p$,tabla);
 END LOOP;
END $$;
DROP POLICY IF EXISTS controlador_eventos_lab ON eventos;
CREATE POLICY controlador_eventos_lab ON eventos FOR SELECT TO dn_mtd_control USING (tenant_id='lab');
DROP POLICY IF EXISTS controlador_alertas_lab ON alertas;
CREATE POLICY controlador_alertas_lab ON alertas FOR SELECT TO dn_mtd_control USING (tenant_id='lab');
DROP POLICY IF EXISTS auth_auditoria_select ON auditoria_local;
REVOKE SELECT ON auditoria_local FROM dn_api_auth;
DROP POLICY IF EXISTS auth_auditoria_insert ON auditoria_local;
CREATE POLICY auth_auditoria_insert ON auditoria_local FOR INSERT TO dn_api_auth WITH CHECK (true);
INSERT INTO versiones_esquema(version) VALUES ('016_aislamiento') ON CONFLICT DO NOTHING;
COMMIT;
