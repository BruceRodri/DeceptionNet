"""GATEWAY LOCAL SOLO PARA EL SENUELO HTTP DE LA EMPRESA SIMULADA."""
import select,socket,threading

class Listener:
    def __init__(self,ip,port):
        self.port=port;self.active=True
        self.sock=socket.socket();self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.sock.bind((ip,port));self.sock.listen(32);self.sock.settimeout(1)
        self.thread=threading.Thread(target=self.accept,daemon=True);self.thread.start()
    def accept(self):
        while self.active:
            try:client,_=self.sock.accept()
            except socket.timeout:continue
            except OSError:break
            threading.Thread(target=self.relay,args=(client,),daemon=True).start()
    def relay(self,client):
        try:
            with client, socket.create_connection(('senuelo',8080),timeout=3) as target:
                while True:
                    ready,_,_=select.select([client,target],[],[],5)
                    if not ready:break
                    for source in ready:
                        data=source.recv(65536)
                        if not data:return
                        (target if source is client else client).sendall(data)
        except OSError:pass
    def close(self):self.active=False;self.sock.close();self.thread.join(timeout=2)
class Gateway:
    def __init__(self,port):
        with socket.create_connection(('senuelo',8080),timeout=5) as route:self.ip=route.getsockname()[0]
        self.listener=Listener(self.ip,port)
    def healthy(self,port):
        try:
            with socket.create_connection((self.ip,port),timeout=2) as s:
                s.settimeout(2);s.sendall(b'GET /_health HTTP/1.0\r\nHost: local\r\n\r\n');return b' 200 ' in s.recv(512)
        except OSError:return False
    def change(self,port):
        if port not in (2301,2302):return 'fallida','PUERTO FUERA DE CATALOGO'
        if port==self.listener.port:return ('aplicada','YA ESTABA EN EL PUERTO') if self.healthy(port) else ('fallida','SENUELO NO RESPONDE')
        candidate=None
        try:
            candidate=Listener(self.ip,port)
            if not self.healthy(port):raise OSError('SALUD FALLIDA')
            old=self.listener;self.listener=candidate;old.close();return 'aplicada','NUEVO CAMINO VERIFICADO'
        except OSError:
            if candidate:candidate.close()
            return 'revertida','FALLO DE SALUD; PUERTO ANTERIOR CONSERVADO'
