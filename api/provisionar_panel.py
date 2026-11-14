"""Aplicar la migración del panel sin exponer credenciales en la salida."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
script = (root / 'migraciones/022_panel_visual.sql').read_text(encoding='utf-8')
result = subprocess.run(['docker','compose','exec','-T','postgres','sh','-c',
    'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
    cwd=root,input=script,text=True,capture_output=True,encoding='utf-8')
if result.returncode:
    print(result.stderr)
    raise SystemExit('No se pudo aplicar la migración del panel.')
print('Migración 022 aplicada: registro manual de empresas, RLS y notificaciones de actividad.')
