"""PREPARAR CUENTA Y TABLAS DEL CONTROLADOR DE LABORATORIO."""
from pathlib import Path
import secrets
import subprocess

raiz=Path(__file__).resolve().parent.parent
ruta=raiz/'.secrets'/'controlador_db_password'
comando=['docker','compose','exec','-T','postgres','sh','-c',
         'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
existe=subprocess.run(comando+['-tAc',"SELECT 1 FROM pg_roles WHERE rolname='dn_mtd_control'"],
                      cwd=raiz,check=True,capture_output=True,text=True).stdout.strip()
if existe and not ruta.exists(): raise SystemExit('LA CUENTA EXISTE SIN CLAVE; NO SE MODIFICO')
if not ruta.exists(): ruta.write_text(secrets.token_hex(32),encoding='ascii')
clave=ruta.read_text(encoding='ascii').strip()
if len(clave)!=64 or any(c not in '0123456789abcdef' for c in clave): raise SystemExit('CLAVE INVALIDA')
sql=(raiz/'migraciones'/'013_controlador_mtd.sql').read_text(encoding='utf-8')+f"""
DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='dn_mtd_control') THEN
 CREATE ROLE dn_mtd_control LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
END IF; END $$;
ALTER ROLE dn_mtd_control PASSWORD '{clave}';
GRANT USAGE ON SCHEMA public TO dn_mtd_control;
GRANT SELECT (id,evento_id,regla,severidad,simulado,ip_origen,fecha_alerta) ON alertas TO dn_mtd_control;
GRANT SELECT (id,sensor,tenant_id) ON eventos TO dn_mtd_control;
GRANT SELECT ON mtd_config,mtd_acciones TO dn_mtd_control;
GRANT SELECT,INSERT ON mtd_decisiones TO dn_mtd_control;
GRANT SELECT,UPDATE ON mtd_control_estado TO dn_mtd_control;
GRANT INSERT ON mtd_acciones TO dn_mtd_control;
GRANT USAGE,SELECT ON SEQUENCE mtd_decisiones_id_seq,mtd_acciones_id_seq TO dn_mtd_control;
GRANT UPDATE (gateway_ip) ON mtd_config TO dn_mtd_gateway;
GRANT SELECT ON mtd_decisiones TO dn_api_auth;
"""
subprocess.run(comando,cwd=raiz,input=sql,text=True,check=True,capture_output=True)
print('CONTROLADOR: CUENTA Y TABLAS PREPARADAS')
