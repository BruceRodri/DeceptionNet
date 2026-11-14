"""CONSUMIDOR ASINCRONO DE EVENTOS DE DECEPTIONNET."""
import logging
import os
import socket
import time
from pathlib import Path

import psycopg
import redis
from redis.exceptions import ResponseError

from detector import Detector, ReglaUmbral
from normalizador import normalizar
from repositorio import Repositorio

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG = logging.getLogger('analyzer')
STREAM = os.getenv('REDIS_STREAM', 'dn:eventos')
GRUPO = os.getenv('REDIS_GROUP', 'dn:analizadores')
CONSUMIDOR = socket.gethostname()
VENTANA = int(os.getenv('VENTANA_SEGUNDOS', '300'))
FALLOS = int(os.getenv('UMBRAL_FALLOS', '5'))
CONEXIONES = int(os.getenv('UMBRAL_CONEXIONES', '10'))
RECUPERAR_MS = int(os.getenv('RECUPERAR_PENDIENTES_MS', '30000'))
if RECUPERAR_MS <= 0:
    raise ValueError('EL TIEMPO DE RECUPERACION DEBE SER POSITIVO')
DETECTOR = Detector((
    ReglaUmbral('autenticaciones_fallidas', 'cowrie.login.failed', FALLOS, VENTANA),
    ReglaUmbral('multiples_conexiones', 'cowrie.session.connect', CONEXIONES, VENTANA),
    ReglaUmbral('multiples_conexiones_web', 'honeypot.http.request', CONEXIONES, VENTANA),
    # Los servicios señuelo no deberían recibir intentos de autenticación legítimos.
    ReglaUmbral('intento_acceso_web_local', 'opencanary.http.3001', 1, VENTANA, sensor='canary-web'),
    ReglaUmbral('intento_acceso_mysql_local', 'opencanary.mysql.8001', 1, VENTANA, sensor='canary-bd'),
))


def atender(cliente, repositorio, mensajes):
    """CONFIRMAR CADA MENSAJE DESPUES DE LA TRANSACCION EN POSTGRESQL."""
    for identificador, datos in mensajes:
        evento = normalizar(identificador, datos)
        nuevo, alertas = repositorio.guardar_y_evaluar(evento, DETECTOR)
        cliente.xack(STREAM, GRUPO, identificador)
        LOG.info('EVENTO %s: %s', 'GUARDADO' if nuevo else 'YA EXISTENTE', identificador)
        for nombre in alertas:
            LOG.info('ALERTA GENERADA: %s ORIGEN=%s SIMULADO=%s', nombre, evento.origen, evento.simulado)


def ejecutar():
    """CONECTAR, RECUPERAR PENDIENTES Y CONSUMIR MENSAJES NUEVOS."""
    cliente = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379,
                          decode_responses=True, socket_connect_timeout=5,
                          socket_timeout=10, health_check_interval=30)
    cliente.ping()
    try:
        cliente.xgroup_create(STREAM, GRUPO, id='0-0', mkstream=True)
        LOG.info('GRUPO CREADO DESDE EL INICIO DEL FLUJO')
    except ResponseError as error:
        if 'BUSYGROUP' not in str(error):
            raise
    with psycopg.connect(host=os.getenv('POSTGRES_HOST', 'postgres'),
                         dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'],
                         password=os.environ['POSTGRES_PASSWORD'], connect_timeout=5,
                         autocommit=True) as db:
        db.execute(Path('/app/schema.sql').read_text(encoding='utf-8'))
        repositorio = Repositorio(db, STREAM)
        LOG.info('ANALIZADOR INICIADO: CONSUMIDOR=%s', CONSUMIDOR)
        cursor = '0-0'
        while True:
            cursor, pendientes, _ = cliente.xautoclaim(STREAM, GRUPO, CONSUMIDOR,
                                                       RECUPERAR_MS, cursor, count=100)
            atender(cliente, repositorio, pendientes)
            respuesta = cliente.xreadgroup(GRUPO, CONSUMIDOR, {STREAM: '>'}, count=100, block=3000)
            for _, mensajes in respuesta:
                atender(cliente, repositorio, mensajes)


if __name__ == '__main__':
    while True:
        try:
            ejecutar()
        except (redis.RedisError, psycopg.Error, OSError) as error:
            LOG.error('ERROR DE CONEXION O PROCESAMIENTO: %s; REINTENTO EN 5 SEGUNDOS', error)
            time.sleep(5)
