"""CREAR UNA CUENTA DE LECTURA LOCAL SIN MOSTRAR SU CLAVE."""
from pathlib import Path
import secrets
import subprocess

raiz = Path(__file__).resolve().parent.parent
ruta = raiz / '.secrets' / 'api_db_password'
comando = ['docker', 'compose', 'exec', '-T', 'postgres', 'sh', '-c',
           'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
consulta = subprocess.run(comando + ['-tAc', "SELECT 1 FROM pg_roles WHERE rolname='dn_api_lectura'"],
                          cwd=raiz, check=True, capture_output=True, text=True).stdout.strip()
if consulta and not ruta.exists():
    raise SystemExit('LA CUENTA EXISTE PERO FALTA SU ARCHIVO DE CLAVE; NO SE MODIFICO')
ruta.parent.mkdir(parents=True, exist_ok=True)
if not ruta.exists():
    ruta.write_text(secrets.token_hex(32), encoding='ascii')
clave = ruta.read_text(encoding='ascii').strip()
if len(clave) != 64 or any(c not in '0123456789abcdef' for c in clave):
    raise SystemExit('EL ARCHIVO DE CLAVE NO TIENE EL FORMATO ESPERADO')
sql = f"""
DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='dn_api_lectura') THEN
  CREATE ROLE dn_api_lectura LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
END IF; END $$;
ALTER ROLE dn_api_lectura PASSWORD '{clave}';
REVOKE ALL ON TABLE eventos, alertas FROM dn_api_lectura;
GRANT USAGE ON SCHEMA public TO dn_api_lectura;
GRANT SELECT (id,sensor,tipo,fecha_evento,fecha_recepcion,ip_origen,simulado,tenant_id)
ON eventos TO dn_api_lectura;
GRANT SELECT (id,evento_id,regla,severidad,descripcion,ip_origen,fecha_alerta,simulado,
estado,umbral,ventana_segundos,cantidad,inicio_ventana,fin_ventana)
ON alertas TO dn_api_lectura;
"""
subprocess.run(comando, cwd=raiz, input=sql, text=True, check=True, capture_output=True)
print('CUENTA DE LECTURA CONFIGURADA; CLAVE GUARDADA EN .secrets')
