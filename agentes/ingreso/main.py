"""RECIBIR EVENTOS SOBRE TLS Y ASIGNAR IDENTIDAD DESDE LA CREDENCIAL."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import hashlib,hmac,json,os,ssl,uuid
import redis
import psycopg

client=redis.Redis(host='redis',port=6379,decode_responses=True,socket_timeout=3)
tokens={name:Path(f'/run/secrets/agente_{name}_token').read_text().strip() for name in ('a','b')}
dbpassword=Path('/run/secrets/ingreso_db_password').read_text().strip()
def connectdb():return psycopg.connect(host='postgres',dbname=os.environ['POSTGRES_DB'],user='dn_ingreso_agentes',password=dbpassword,connect_timeout=4)
push=client.register_script('''
local anterior=redis.call('HGET',KEYS[2],ARGV[1])
if anterior then return anterior end
local id=redis.call('XADD',KEYS[1],'*',unpack(ARGV,2))
redis.call('HSET',KEYS[2],ARGV[1],id)
return id
''')
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_args):pass
    def reply(self,code,obj):
        data=json.dumps(obj).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def identity(self):
        auth=self.headers.get('Authorization','')
        if not auth.startswith('Bearer '):return None
        token=auth[7:];name=next((name for name,value in tokens.items() if hmac.compare_digest(token,value)),None)
        return name
    def do_GET(self):
        if self.path!='/v1/orden':return self.reply(404,{'error':'NO_ENCONTRADO'})
        name=self.identity()
        if name is None:return self.reply(401,{'error':'NO_AUTENTICADO'})
        try:
            with connectdb() as db:
                db.execute("UPDATE ordenes_remotas SET estado='caducada',resultado='PLAZO VENCIDO' WHERE tenant_id=%s AND estado='pendiente' AND vence_en < now()",('empresa_'+name,))
                row=db.execute("""UPDATE ordenes_remotas SET estado='entregada' WHERE id=(SELECT id FROM ordenes_remotas
                  WHERE tenant_id=%s AND estado IN ('pendiente','entregada') AND vence_en>now()
                  ORDER BY creada_en FOR UPDATE SKIP LOCKED LIMIT 1)
                  RETURNING id,tenant_id,sensor,puerto,vence_en""",('empresa_'+name,)).fetchone()
            if not row:return self.reply(200,{'orden':None})
            order={'id':str(row[0]),'tenant_id':row[1],'sensor':row[2],'puerto':row[3],'vence_en':row[4].isoformat()}
            raw=json.dumps(order,sort_keys=True,separators=(',',':')).encode()
            order['firma']=hmac.new(tokens[name].encode(),raw,hashlib.sha256).hexdigest()
            self.reply(200,{'orden':order})
        except (psycopg.Error,OSError):self.reply(503,{'error':'SERVICIO_NO_DISPONIBLE'})
    def do_POST(self):
        if self.path not in ('/v1/eventos','/v1/ack'):return self.reply(404,{'error':'NO_ENCONTRADO'})
        name=self.identity()
        if name is None:return self.reply(401,{'error':'NO_AUTENTICADO'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 1<=size<=32768:raise ValueError()
            body=json.loads(self.rfile.read(size))
            if self.path=='/v1/ack':
                if set(body)!={'id','estado','resultado'} or body['estado'] not in ('aplicada','fallida','revertida') or not isinstance(body['resultado'],str) or len(body['resultado'])>200:raise ValueError()
                order_id=str(uuid.UUID(body['id']))
                with connectdb() as db:
                    row=db.execute("UPDATE ordenes_remotas SET estado=%s,resultado=%s,confirmada_en=now() WHERE id=%s AND tenant_id=%s AND estado='entregada' RETURNING id",(body['estado'],body['resultado'],order_id,'empresa_'+name)).fetchone()
                    if not row:row=db.execute("SELECT id FROM ordenes_remotas WHERE id=%s AND tenant_id=%s AND estado=%s",(order_id,'empresa_'+name,body['estado'])).fetchone()
                return self.reply(200 if row else 409,{'confirmada':bool(row)})
            items=body['eventos']
            if not isinstance(items,list) or not 1<=len(items)<=20:raise ValueError()
            for item in items:
                if set(item)!={'id','timestamp','ip_origen'} or len(item['id'])!=64 or any(c not in '0123456789abcdef' for c in item['id']):raise ValueError()
                if not isinstance(item['timestamp'],str) or len(item['timestamp'])>64 or not isinstance(item['ip_origen'],str) or len(item['ip_origen'])>45:raise ValueError()
            for item in items:
                fields={'tenant_id':'empresa_'+name,'sensor':'sensor-remoto-'+name,'raw_event_id':item['id'],'eventid':'honeypot.http.request','timestamp':item['timestamp'],'src_ip':item['ip_origen'],'simulado':'false'}
                args=[item['id']]
                for key,value in fields.items():args.extend([key,value])
                push(keys=['dn:eventos','dn:agente:'+name+':ids'],args=args)
            self.reply(200,{'aceptados':[item['id'] for item in items]})
        except (KeyError,TypeError,ValueError,json.JSONDecodeError):self.reply(400,{'error':'LOTE_INVALIDO'})
        except (redis.RedisError,psycopg.Error,OSError):self.reply(503,{'error':'SERVICIO_NO_DISPONIBLE'})

server=ThreadingHTTPServer(('0.0.0.0',8443),Handler)
context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
context.load_cert_chain('/run/secrets/agente_tls.crt','/run/secrets/agente_tls.key')
server.socket=context.wrap_socket(server.socket,server_side=True)
print('INGRESO TLS DE AGENTES ACTIVO',flush=True);server.serve_forever()
