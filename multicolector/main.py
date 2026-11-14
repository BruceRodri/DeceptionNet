"""LEER REGISTROS EN SOLO LECTURA Y PUBLICAR MENSAJES IDEMPOTENTES."""
import hashlib
import json
import os
import time
from pathlib import Path

import redis
from adaptadores import adaptar_opencanary

SENSOR = os.environ['SENSOR_ID']
if SENSOR not in ('canary-web', 'canary-bd'):
    raise ValueError('SENSOR NO RECONOCIDO')
FUENTE = Path('/registros/eventos.jsonl')
ESTADO = Path('/estado/checkpoint.json')
redis_cli = redis.Redis(host='redis', port=6379, decode_responses=True, socket_connect_timeout=5)
# PUBLICAR Y MARCAR EL IDENTIFICADOR DE ORIGEN EN UNA OPERACION ATOMICA.
PUBLICAR = redis_cli.register_script('''
local existente = redis.call('HGET', KEYS[2], ARGV[1])
if existente then return existente end
local id = redis.call('XADD', KEYS[1], '*', unpack(ARGV, 2))
redis.call('HSET', KEYS[2], ARGV[1], id)
return id
''')


def guardar_estado(identidad, posicion):
    temporal = ESTADO.with_suffix('.tmp')
    with temporal.open('w', encoding='utf-8') as archivo:
        json.dump({'identidad': identidad, 'posicion': posicion}, archivo)
        archivo.flush()
        os.fsync(archivo.fileno())
    os.replace(temporal, ESTADO)


def main():
    try:
        estado = json.loads(ESTADO.read_text(encoding='utf-8'))
        identidad_anterior = estado['identidad']
        posicion = int(estado['posicion'])
    except (FileNotFoundError, ValueError, KeyError, TypeError):
        identidad_anterior, posicion = None, 0
    print(f'COLECTOR INICIADO: {SENSOR}', flush=True)
    while True:
        try:
            if not FUENTE.exists():
                time.sleep(2)
                continue
            with FUENTE.open('rb') as archivo:
                stat = os.fstat(archivo.fileno())
                identidad = f'{stat.st_dev}:{stat.st_ino}'
                if identidad != identidad_anterior or stat.st_size < posicion:
                    identidad_anterior, posicion = identidad, 0
                archivo.seek(posicion)
                while True:
                    inicio = archivo.tell()
                    linea = archivo.readline()
                    if not linea or not linea.endswith(b'\n'):
                        break
                    nueva_posicion = archivo.tell()
                    origen = f'{SENSOR}:{identidad}:{inicio}:'.encode() + linea
                    raw_id = hashlib.sha256(origen).hexdigest()
                    try:
                        evento = adaptar_opencanary(json.loads(linea), SENSOR, raw_id)
                    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
                        print(f'REGISTRO INVALIDO EN {SENSOR} POSICION {inicio}', flush=True)
                        evento = None
                    if evento:
                        argumentos = [raw_id]
                        for campo, valor in evento.items():
                            argumentos.extend((campo, valor))
                        mensaje_id = PUBLICAR(keys=['dn:eventos', 'dn:fuentes:ids'], args=argumentos)
                        print(f'EVENTO ENVIADO: {SENSOR} {evento["eventid"]} {mensaje_id}', flush=True)
                    guardar_estado(identidad, nueva_posicion)
                    posicion = nueva_posicion
        except (OSError, redis.RedisError) as error:
            print(f'ERROR DE COLECTOR {SENSOR}: {error}', flush=True)
        time.sleep(2)


if __name__ == '__main__':
    main()
