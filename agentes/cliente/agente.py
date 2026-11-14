"""ENVIAR EVENTOS CON COLA SQLITE PERSISTENTE Y REINTENTOS POR TLS."""
from pathlib import Path
import json,os,sqlite3,ssl,time,urllib.error,urllib.request
from gateway import Gateway
from protocolo import validar_orden
db=sqlite3.connect('/estado/cola.db')
db.execute('CREATE TABLE IF NOT EXISTS pendientes (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
db.execute('CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor INTEGER NOT NULL)')
db.execute('CREATE TABLE IF NOT EXISTS ordenes_ejecutadas (id TEXT PRIMARY KEY, estado TEXT NOT NULL, resultado TEXT NOT NULL)')
if 'confirmada' not in [row[1] for row in db.execute('PRAGMA table_info(ordenes_ejecutadas)')]:
    db.execute('ALTER TABLE ordenes_ejecutadas ADD COLUMN confirmada INTEGER NOT NULL DEFAULT 1')
db.commit()
token=Path('/run/secrets/agent_token').read_text().strip()
tenant=os.environ['TENANT_ID']
if tenant not in ('empresa_a','empresa_b'):raise RuntimeError('TENANT INVALIDO')
context=ssl.create_default_context(cafile='/run/secrets/agente_tls.crt')
source=Path('/registros/eventos.jsonl')
gateway=None
def request(path,data=None):
    body=json.dumps(data).encode() if data is not None else None
    req=urllib.request.Request('https://ingreso-agentes:8443'+path,data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,context=context,timeout=4) as response:return json.load(response)
def process_order():
    global gateway
    order=request('/v1/orden')['orden']
    if not order:return
    order=validar_orden(order,tenant,token)
    previous=db.execute('SELECT estado,resultado FROM ordenes_ejecutadas WHERE id=?',(order['id'],)).fetchone()
    if previous:status,result=previous
    else:
        status,result=gateway.change(order['puerto'])
        with db:
            if status=='aplicada':db.execute("INSERT INTO estado(clave,valor) VALUES('puerto',?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",(order['puerto'],))
            db.execute('INSERT INTO ordenes_ejecutadas(id,estado,resultado,confirmada) VALUES(?,?,?,0)',(order['id'],status,result))
    request('/v1/ack',{'id':order['id'],'estado':status,'resultado':result})
    with db:db.execute('UPDATE ordenes_ejecutadas SET confirmada=1 WHERE id=?',(order['id'],))
    print(f'ORDEN {order["id"]}: {status}',flush=True)
def retry_ack():
    row=db.execute('SELECT id,estado,resultado FROM ordenes_ejecutadas WHERE confirmada=0 ORDER BY rowid LIMIT 1').fetchone()
    if row:
        request('/v1/ack',{'id':row[0],'estado':row[1],'resultado':row[2]})
        with db:db.execute('UPDATE ordenes_ejecutadas SET confirmada=1 WHERE id=?',(row[0],))
def collect():
    if not source.exists():return
    row=db.execute("SELECT valor FROM estado WHERE clave='offset'").fetchone();offset=row[0] if row else 0
    with source.open('rb') as f:
        if source.stat().st_size<offset:raise RuntimeError('ARCHIVO DE EVENTOS REDUCIDO; REQUIERE REVISION')
        f.seek(offset)
        while True:
            line=f.readline()
            if not line or not line.endswith(b'\n'):break
            item=json.loads(line)
            with db:
                db.execute('INSERT OR IGNORE INTO pendientes(id,payload) VALUES (?,?)',(item['id'],json.dumps(item)))
                db.execute("INSERT INTO estado(clave,valor) VALUES('offset',?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",(f.tell(),))
def send():
    rows=db.execute('SELECT id,payload FROM pendientes ORDER BY rowid LIMIT 20').fetchall()
    if not rows:return
    payload=json.dumps({'eventos':[json.loads(row[1]) for row in rows]}).encode()
    request=urllib.request.Request('https://ingreso-agentes:8443/v1/eventos',data=payload,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    with urllib.request.urlopen(request,context=context,timeout=4) as response:accepted=json.load(response)['aceptados']
    if set(accepted)!={row[0] for row in rows}:raise ValueError('ACK INCORRECTO')
    with db:db.executemany('DELETE FROM pendientes WHERE id=?',[(item,) for item in accepted])
    print(f'LOTE CONFIRMADO: {len(accepted)}',flush=True)
print('AGENTE LOCAL INICIADO',flush=True)
while True:
    try:
        if gateway is None:
            row=db.execute("SELECT valor FROM estado WHERE clave='puerto'").fetchone();gateway=Gateway(row[0] if row else 2301)
        collect();send();retry_ack();process_order()
    except (OSError,urllib.error.URLError,ValueError,RuntimeError,sqlite3.Error) as error:print('REINTENTO:',type(error).__name__,flush=True)
    time.sleep(1)
