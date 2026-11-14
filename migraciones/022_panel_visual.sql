-- Registro manual de organizaciones y señales confirmadas para el panel.
BEGIN;
ALTER TABLE organizaciones ADD COLUMN IF NOT EXISTS creada_en timestamptz NOT NULL DEFAULT now();
GRANT SELECT ON organizaciones, sensores_registro TO dn_api_auth;
-- Mostrar en el panel los comandos del señuelo y su usuario, sin consultar contraseñas.
GRANT SELECT (usuario,comando) ON eventos TO dn_rls_lab,dn_rls_empresa_a,dn_rls_empresa_b;
DROP POLICY IF EXISTS auth_registro_sensores ON sensores_registro;
CREATE POLICY auth_registro_sensores ON sensores_registro FOR SELECT TO dn_api_auth USING (true);
CREATE OR REPLACE FUNCTION registrar_empresa_panel(p_id text, p_nombre text, p_usuario text, p_hash text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE r text; t text;
BEGIN
  IF p_id !~ '^org_[a-f0-9]{32}$' OR length(trim(p_nombre)) NOT BETWEEN 2 AND 80
    OR p_usuario !~ '^[a-zA-Z0-9_]{3,60}$' OR p_hash !~ '^scrypt\$32768\$8\$1\$[a-f0-9]{32}\$[a-f0-9]{64}$'
    THEN RAISE EXCEPTION 'REGISTRO_INVALIDO'; END IF;
  r := 'dn_rls_' || p_id;
  INSERT INTO public.organizaciones(id,nombre,simulada) VALUES (p_id,trim(p_nombre),true);
  INSERT INTO public.usuarios_locales(usuario,password_hash,rol,tenant_id) VALUES (p_usuario,p_hash,'admin',p_id);
  EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',r);
  EXECUTE format('GRANT USAGE ON SCHEMA public TO %I',r);
  EXECUTE format('GRANT SELECT(id,sensor,tipo,fecha_evento,fecha_recepcion,ip_origen,simulado,tenant_id,usuario,comando) ON public.eventos TO %I',r);
  EXECUTE format('GRANT SELECT(id,evento_id,regla,severidad,descripcion,ip_origen,fecha_alerta,simulado,estado,umbral,ventana_segundos,cantidad,tenant_id) ON public.alertas TO %I',r);
  EXECUTE format('GRANT SELECT ON public.politicas_mtd,public.sensores_registro TO %I',r);
  EXECUTE format('GRANT SELECT(id,usuario_id,accion,resultado,fecha,detalle,tenant_id) ON public.auditoria_local TO %I',r);
  EXECUTE format('GRANT %I TO dn_api_auth WITH INHERIT FALSE, SET TRUE',r);
END $$;
-- Aplicar las columnas adicionales a empresas ya registradas por el panel.
DO $$ DECLARE r text; BEGIN
  FOR r IN SELECT rolname FROM pg_roles WHERE rolname ~ '^dn_rls_org_[a-f0-9]{32}$' LOOP
    EXECUTE format('GRANT SELECT(usuario,comando) ON public.eventos TO %I',r);
  END LOOP;
END $$;
REVOKE ALL ON FUNCTION registrar_empresa_panel(text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION registrar_empresa_panel(text,text,text,text) TO dn_api_auth;
DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['eventos','alertas','politicas_mtd','sensores_registro','auditoria_local'] LOOP
    EXECUTE format('DROP POLICY IF EXISTS lectura_empresa_registrada ON %I',t);
    EXECUTE format($p$CREATE POLICY lectura_empresa_registrada ON %I FOR SELECT USING
      (tenant_id ~ '^org_[a-f0-9]{32}$' AND current_user = 'dn_rls_' || tenant_id)$p$,t);
  END LOOP;
END $$;
CREATE TABLE IF NOT EXISTS demo_conexiones (
 id uuid PRIMARY KEY, usuario_id bigint NOT NULL REFERENCES usuarios_locales(id),
 tenant_id text NOT NULL REFERENCES organizaciones(id), puerto integer NOT NULL CHECK(puerto IN (2201,2202,2203,2222)),
 estado text NOT NULL DEFAULT 'solicitada', creada_en timestamptz NOT NULL DEFAULT now(), detalle text NOT NULL DEFAULT ''
);
ALTER TABLE demo_conexiones ADD COLUMN IF NOT EXISTS origen text;
ALTER TABLE demo_conexiones ADD COLUMN IF NOT EXISTS tipo text NOT NULL DEFAULT 'ssh';
ALTER TABLE demo_conexiones DROP CONSTRAINT IF EXISTS demo_conexiones_puerto_check;
ALTER TABLE demo_conexiones ADD CONSTRAINT demo_conexiones_puerto_check CHECK(puerto IN (2201,2202,2203,2222,8080,3307));
GRANT SELECT,INSERT,UPDATE ON demo_conexiones TO dn_api_auth;
GRANT SELECT ON mtd_decisiones TO dn_api_auth;
CREATE OR REPLACE FUNCTION notificar_actividad_panel() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_notify('dn_actividad',json_build_object('tipo',TG_TABLE_NAME,'tenant',NEW.tenant_id,'id',NEW.id::text)::text);
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS eventos_panel ON eventos;
CREATE TRIGGER eventos_panel AFTER INSERT ON eventos FOR EACH ROW EXECUTE FUNCTION notificar_actividad_panel();
DROP TRIGGER IF EXISTS alertas_panel ON alertas;
CREATE TRIGGER alertas_panel AFTER INSERT ON alertas FOR EACH ROW EXECUTE FUNCTION notificar_actividad_panel();
DROP TRIGGER IF EXISTS mtd_panel ON mtd_acciones;
CREATE TRIGGER mtd_panel AFTER INSERT OR UPDATE ON mtd_acciones FOR EACH ROW EXECUTE FUNCTION notificar_actividad_panel();
DROP TRIGGER IF EXISTS decisiones_panel ON mtd_decisiones;
CREATE TRIGGER decisiones_panel AFTER INSERT ON mtd_decisiones FOR EACH ROW EXECUTE FUNCTION notificar_actividad_panel();
DROP TRIGGER IF EXISTS remoto_panel ON ordenes_remotas;
CREATE TRIGGER remoto_panel AFTER INSERT OR UPDATE ON ordenes_remotas FOR EACH ROW EXECUTE FUNCTION notificar_actividad_panel();
INSERT INTO versiones_esquema(version) VALUES ('022_panel_visual') ON CONFLICT DO NOTHING;
COMMIT;
