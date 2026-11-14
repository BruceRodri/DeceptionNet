"""SENUELO HTTP INOFENSIVO QUE REGISTRA CONEXIONES LOCALES."""
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,os,uuid
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_args):pass
    def do_GET(self):
        if self.path=='/_health':
            self.send_response(200);self.send_header('Content-Length','0');self.end_headers();return
        record={'id':uuid.uuid4().hex+uuid.uuid4().hex,'timestamp':datetime.now(timezone.utc).isoformat(),'ip_origen':self.client_address[0]}
        with Path('/registros/eventos.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(record)+'\n');f.flush();os.fsync(f.fileno())
        data=b'Servicio de laboratorio\n';self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
print('SENUELO HTTP LOCAL ACTIVO',flush=True)
ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
