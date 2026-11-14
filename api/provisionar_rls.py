"""CREAR SECRETOS DE LECTURA POR ORGANIZACION Y APLICAR LA MIGRACION."""
from pathlib import Path
import secrets
import subprocess
root=Path(__file__).resolve().parent.parent
secrets_dir=root/'.secrets'
roles=['lab','empresa_a','empresa_b']
script=(root/'migraciones'/'016_aislamiento.sql').read_text(encoding='utf-8')
command=['docker','compose','exec','-T','postgres','sh','-c','psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
for role in roles:
    path=secrets_dir/f'rls_{role}_password'
    exists=subprocess.run(command+['-tAc',f"SELECT 1 FROM pg_roles WHERE rolname='dn_rls_{role}'"],cwd=root,text=True,capture_output=True,check=True).stdout.strip()
    if exists and not path.exists():raise SystemExit('EXISTE UN ROL SIN SU ARCHIVO DE CLAVE; NO SE MODIFICO')
    if not path.exists(): path.write_text(secrets.token_hex(32),encoding='ascii')
    password=path.read_text(encoding='ascii').strip()
    if len(password)!=64 or any(c not in '0123456789abcdef' for c in password): raise SystemExit('SECRETO INVALIDO')
    script+=f"\nALTER ROLE dn_rls_{role} PASSWORD '{password}';"
result=subprocess.run(command,cwd=root,input=script,text=True,capture_output=True)
if result.returncode: print(result.stderr);raise SystemExit('FALLO LA MIGRACION RLS')
print('RLS INSTALADO Y CREDENCIALES DE LECTURA POR ORGANIZACION CREADAS')
