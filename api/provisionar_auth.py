"""PREPARAR ESQUEMA Y SECRETOS LOCALES SIN IMPRIMIR SUS VALORES."""
from pathlib import Path
import secrets
import subprocess

raiz = Path(__file__).resolve().parent.parent
carpeta = raiz / '.secrets'
carpeta.mkdir(exist_ok=True)
comando = ['docker', 'compose', 'exec', '-T', 'postgres', 'sh', '-c',
           'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
consulta = subprocess.run(comando + ['-tAc', "SELECT 1 FROM pg_roles WHERE rolname='dn_api_auth'"],
                          cwd=raiz, capture_output=True, text=True, check=True).stdout.strip()
clave_path = carpeta / 'auth_db_password'
if consulta and not clave_path.exists():
    raise SystemExit('LA CUENTA EXISTE PERO FALTA SU CLAVE; NO SE MODIFICO')
for nombre in ('auth_db_password', 'jwt_secret', 'bootstrap_token'):
    ruta = carpeta / nombre
    if not ruta.exists():
        ruta.write_text(secrets.token_hex(32), encoding='ascii')
    valor = ruta.read_text(encoding='ascii').strip()
    if len(valor) != 64 or any(c not in '0123456789abcdef' for c in valor):
        raise SystemExit('UN ARCHIVO DE SECRETO TIENE FORMATO INVALIDO')
clave = clave_path.read_text(encoding='ascii').strip()
migracion = (raiz / 'migraciones' / '011_autenticacion.sql').read_text(encoding='utf-8')
sql = migracion + f"""
DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='dn_api_auth') THEN
  CREATE ROLE dn_api_auth LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
END IF; END $$;
ALTER ROLE dn_api_auth PASSWORD '{clave}';
GRANT USAGE ON SCHEMA public TO dn_api_auth;
GRANT SELECT,INSERT ON usuarios_locales TO dn_api_auth;
GRANT SELECT,INSERT,UPDATE ON sesiones_locales TO dn_api_auth;
GRANT SELECT,INSERT ON auditoria_local TO dn_api_auth;
GRANT USAGE,SELECT ON SEQUENCE usuarios_locales_id_seq, auditoria_local_id_seq TO dn_api_auth;
"""
subprocess.run(comando, cwd=raiz, input=sql, text=True, check=True, capture_output=True)
print('AUTENTICACION LOCAL PREPARADA; CODIGO DE CONFIGURACION EN .secrets/bootstrap_token')
