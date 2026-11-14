"""GATEWAY MTD RESTRINGIDO AL SENUEL0 SSH DEL LABORATORIO."""
import logging
import os
import select
import socket
import threading
import time
from pathlib import Path

import psycopg

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG = logging.getLogger('gateway')
PUERTOS = {2201, 2202, 2203}
DESTINO = ('cowrie', 2222)


def retransmitir(cliente):
    """COPIAR TRAFICO AL UNICO DESTINO PERMITIDO SIN INSPECCIONAR CREDENCIALES."""
    try:
        with cliente, socket.create_connection(DESTINO, timeout=4) as destino:
            cliente.settimeout(None)
            destino.settimeout(None)
            while True:
                listos, _, _ = select.select([cliente, destino], [], [], 60)
                if not listos:
                    break
                for origen in listos:
                    datos = origen.recv(65536)
                    if not datos:
                        return
                    (destino if origen is cliente else cliente).sendall(datos)
    except OSError:
        return


class Escucha:
    def __init__(self, puerto):
        if puerto not in PUERTOS:
            raise ValueError('PUERTO FUERA DEL CATALOGO')
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', puerto))
        self.socket.listen(64)
        self.socket.settimeout(0.5)
        self.activa = True
        self.hilo = threading.Thread(target=self._aceptar, daemon=True)
        self.hilo.start()
        self.puerto = puerto

    def _aceptar(self):
        while self.activa:
            try:
                cliente, _ = self.socket.accept()
                threading.Thread(target=retransmitir, args=(cliente,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def cerrar(self):
        self.activa = False
        self.socket.close()
        self.hilo.join(timeout=2)


def verificar(puerto):
    """COMPROBAR EL NUEVO CAMINO HASTA EL SALUDO SSH DE COWRIE."""
    with socket.create_connection(('127.0.0.1', puerto), timeout=4) as cliente:
        cliente.settimeout(4)
        return cliente.recv(256).startswith(b'SSH-')


def trabajar(db):
    """SER EL UNICO GATEWAY ACTIVO Y PROCESAR SOLICITUDES EN ORDEN."""
    if not db.execute('SELECT pg_try_advisory_lock(772120)').fetchone()[0]:
        raise RuntimeError('OTRO GATEWAY YA TIENE EL BLOQUEO')
    db.execute("UPDATE mtd_acciones SET estado='solicitada', detalle='RECUPERADA TRAS REINICIO' WHERE estado='en_proceso' AND tenant_id='lab' AND sensor='cowrie-ssh'")
    puerto = db.execute("SELECT puerto FROM mtd_config WHERE tenant_id='lab' AND sensor='cowrie-ssh'").fetchone()[0]
    # IDENTIFICAR LA IP DE SALIDA HACIA COWRIE PARA EXCLUIR LAS PRUEBAS DEL GATEWAY.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as ruta:
        ruta.connect(DESTINO)
        gateway_ip = ruta.getsockname()[0]
    db.execute("UPDATE mtd_config SET gateway_ip=%s WHERE tenant_id='lab' AND sensor='cowrie-ssh'", (gateway_ip,))
    activa = Escucha(puerto)
    LOG.info('GATEWAY ACTIVO EN %s', puerto)
    try:
        while True:
            with db.transaction():
                fila = db.execute("""UPDATE mtd_acciones SET estado='en_proceso',iniciada_en=now()
                    WHERE id=(SELECT id FROM mtd_acciones WHERE estado='solicitada' AND tenant_id='lab'
                    AND sensor='cowrie-ssh' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
                    RETURNING id,puerto_destino""").fetchone()
            if not fila:
                time.sleep(0.5)
                continue
            accion, nuevo = fila
            anterior = activa.puerto
            inicio = time.monotonic()
            candidata = None
            try:
                if nuevo != anterior:
                    candidata = Escucha(nuevo)
                if not verificar(nuevo):
                    raise OSError('EL DESTINO NO RESPONDIO CON UN SALUDO SSH')
                duracion = round((time.monotonic()-inicio)*1000)
                with db.transaction():
                    db.execute("UPDATE mtd_config SET puerto=%s,actualizado_en=now() WHERE tenant_id='lab' AND sensor='cowrie-ssh'", (nuevo,))
                    db.execute("""UPDATE mtd_acciones SET estado='aplicada',puerto_anterior=%s,
                        terminada_en=now(),duracion_ms=%s,detalle='SALUDO SSH VERIFICADO' WHERE id=%s""", (anterior,duracion,accion))
                if candidata:
                    antigua, activa = activa, candidata
                    antigua.cerrar()
                LOG.info('ACCION %s APLICADA: %s -> %s EN %s MS', accion, anterior, nuevo, duracion)
            except (OSError, psycopg.Error) as error:
                if candidata:
                    candidata.cerrar()
                # LA ESCUCHA ANTERIOR SIGUE ABIERTA HASTA CONFIRMAR EL CAMBIO.
                estado = 'revertida' if candidata else 'fallida'
                try:
                    db.execute("""UPDATE mtd_acciones SET estado=%s,puerto_anterior=%s,terminada_en=now(),
                        duracion_ms=%s,detalle=%s WHERE id=%s""",
                        (estado,anterior,round((time.monotonic()-inicio)*1000),'VERIFICACION O CAMBIO FALLIDO',accion))
                except psycopg.Error:
                    raise
                LOG.warning('ACCION %s %s: %s', accion, estado, type(error).__name__)
    finally:
        activa.cerrar()


if __name__ == '__main__':
    clave = Path('/run/secrets/gateway_db_password').read_text(encoding='ascii').strip()
    while True:
        try:
            with psycopg.connect(host='postgres',dbname=os.environ['POSTGRES_DB'],user='dn_mtd_gateway',
                                 password=clave,autocommit=True,connect_timeout=5) as db:
                trabajar(db)
        except (psycopg.Error, OSError, RuntimeError) as error:
            LOG.error('GATEWAY INTERRUMPIDO: %s; REINTENTO EN 5 SEGUNDOS', type(error).__name__)
            time.sleep(5)
