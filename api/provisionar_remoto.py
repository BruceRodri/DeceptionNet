"""CREAR CUENTA LIMITADA PARA ENTREGAR Y CONFIRMAR ORDENES."""
from pathlib import Path
import secrets,subprocess
root=Path(__file__).resolve().parent.parent
path=root/'.secrets'/'ingreso_db_password'
cmd=['docker','compose','exec','-T','postgres','sh','-c','psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
exists=subprocess.run(cmd+['-tAc',"SELECT 1 FROM pg_roles WHERE rolname='dn_ingreso_agentes'"],cwd=root,text=True,capture_output=True,check=True).stdout.strip()
if exists and not path.exists():raise SystemExit('EXISTE EL ROL SIN SU ARCHIVO DE CLAVE; NO SE MODIFICO')
if not path.exists():path.write_text(secrets.token_hex(32),encoding='ascii')
password=path.read_text().strip()
if len(password)!=64 or any(c not in '0123456789abcdef' for c in password):raise SystemExit('SECRETO INVALIDO')
script=(root/'migraciones'/'018_ordenes_remotas.sql').read_text()+f"\nALTER ROLE dn_ingreso_agentes PASSWORD '{password}';"
r=subprocess.run(cmd,cwd=root,input=script,text=True,capture_output=True)
if r.returncode:print(r.stderr);raise SystemExit(1)
print('ORDENES REMOTAS Y CUENTA LIMITADA PREPARADAS')
