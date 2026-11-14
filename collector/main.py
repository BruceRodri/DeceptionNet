import json
import hashlib
import os
import time
from pathlib import Path
import redis
from adaptadores import adaptar_cowrie
# DEFINIR DONDE ESTAN LOS REGISTROS DE COWRIE.
RUTA_JSON = Path("/datos_cowrie/log/cowrie/cowrie.json")
# GUARDAR HASTA QUE PARTE DEL ARCHIVO HEMOS LEIDO.
RUTA_ESTADO = Path("/estado/offset.txt")
# CONECTAR CON EL SERVICIO REDIS DE DOCKER.
cliente_redis = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True
)
# PUBLICAR Y GUARDAR EL IDENTIFICADOR DE ORIGEN EN UNA OPERACION ATOMICA.
publicar = cliente_redis.register_script('''
local existente = redis.call('HGET', KEYS[2], ARGV[1])
if existente then return existente end
local id = redis.call('XADD', KEYS[1], '*', unpack(ARGV, 2))
redis.call('HSET', KEYS[2], ARGV[1], id)
return id
''')
# CREAR LA CARPETA DONDE GUARDAREMOS EL PROGRESO.
RUTA_ESTADO.parent.mkdir(parents=True, exist_ok=True)
# RECUPERAR LA ULTIMA POSICION LEIDA.
try:
    posicion = int(RUTA_ESTADO.read_text())
except (FileNotFoundError, ValueError):
    posicion = 0
print("COLECTOR DE DECEPTIONNET INICIADO", flush=True)
# REVISAR CONTINUAMENTE LOS EVENTOS DE COWRIE.
while True:
    try:
        if RUTA_JSON.exists():
            # REINICIAR LA LECTURA SI EL ARCHIVO SE REDUCE.
            if RUTA_JSON.stat().st_size < posicion:
                posicion = 0
            # ABRIR LOS REGISTROS EN MODO SOLO LECTURA.
            with RUTA_JSON.open("rb") as archivo:
                archivo.seek(posicion)
                while True:
                    inicio = archivo.tell()
                    linea = archivo.readline()
                    # ESPERAR SI NO HAY EVENTOS COMPLETOS.
                    if not linea or not linea.endswith(b"\n"):
                        break
                    nueva_posicion = archivo.tell()
                    try:
                        evento = json.loads(linea.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        print("EVENTO JSON NO VALIDO", flush=True)
                        posicion = nueva_posicion
                        RUTA_ESTADO.write_text(str(posicion))
                        continue
                    identidad = os.fstat(archivo.fileno())
                    origen = f'cowrie-ssh:{identidad.st_dev}:{identidad.st_ino}:{inicio}:'.encode() + linea
                    raw_id = hashlib.sha256(origen).hexdigest()
                    datos = adaptar_cowrie(evento, raw_id)
                    argumentos = [raw_id]
                    for campo, valor in datos.items():
                        argumentos.extend((campo, valor))
                    publicar(keys=['dn:eventos', 'dn:fuentes:ids'], args=argumentos)
                    # GUARDAR EL PROGRESO DESPUES DE PUBLICAR.
                    posicion = nueva_posicion
                    RUTA_ESTADO.write_text(str(posicion))
                    print(
                        f"EVENTO ENVIADO: {datos['eventid']}",
                        flush=True
                    )
    except (OSError, redis.RedisError) as error:
        print(f"ERROR DEL COLECTOR: {error}", flush=True)
    # ESPERAR DOS SEGUNDOS ANTES DE REVISAR OTRA VEZ.
    time.sleep(2)
