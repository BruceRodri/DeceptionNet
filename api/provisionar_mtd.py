"""CREAR CUENTA LIMITADA PARA EL GATEWAY DE LABORATORIO."""
from pathlib import Path
import secrets
import subprocess

raiz = Path(__file__).resolve().parent.parent
ruta = raiz / '.secrets' / 'gateway_db_password'
comando = ['docker','compose','exec','-T','postgres','sh','-c',
           'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
consulta = subprocess.run(comando + ['-tAc',"SELECT 1 FROM pg_roles WHERE rolname='dn_mtd_gateway'"],
                          cwd=raiz,capture_output=True,text=True,check=True).stdout.strip()
if consulta and not ruta.exists():
    raise SystemExit('LA CUENTA DEL GATEWAY EXISTE SIN SU CLAVE; NO SE MODIFICO')
ruta.parent.mkdir(exist_ok=True)
if not ruta.exists(): ruta.write_text(secrets.token_hex(32),encoding='ascii')
clave=ruta.read_text(encoding='ascii').strip()
if len(clave)!=64 or any(c not in '0123456789abcdef' for c in clave): raise SystemExit('CLAVE INVALIDA')
sql=(raiz/'migraciones'/'012_gateway_mtd.sql').read_text(encoding='utf-8')+f"""
DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='dn_mtd_gateway') THEN
 CREATE ROLE dn_mtd_gateway LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
END IF; END $$;
ALTER ROLE dn_mtd_gateway PASSWORD '{clave}';
GRANT USAGE ON SCHEMA public TO dn_mtd_gateway;
GRANT SELECT,UPDATE ON mtd_config,mtd_acciones TO dn_mtd_gateway;
GRANT SELECT,INSERT ON mtd_acciones TO dn_api_auth;
GRANT SELECT ON mtd_config TO dn_api_auth;
GRANT USAGE,SELECT ON SEQUENCE mtd_acciones_id_seq TO dn_api_auth;
"""
subprocess.run(comando,cwd=raiz,input=sql,text=True,check=True,capture_output=True)
print('GATEWAY MTD: TABLAS Y CUENTA LIMITADA PREPARADAS')
