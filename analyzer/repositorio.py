"""PERSISTENCIA TRANSACCIONAL Y CONSULTAS DE LAS VENTANAS."""
import hashlib
import json
from dataclasses import replace
from datetime import timedelta


class Repositorio:
    def __init__(self, db, stream):
        self.db = db
        self.stream = stream

    def guardar_y_evaluar(self, evento, detector):
        """GUARDAR EVENTO Y ALERTAS EN UNA TRANSACCION Y SIN DUPLICADOS."""
        with self.db.transaction():
            with self.db.cursor() as cur:
                # PROTEGER LA VENTANA DE UN SENSOR Y ORIGEN ENTRE CONSUMIDORES.
                if evento.origen:
                    bloqueo = json.dumps([evento.tenant_id, evento.sensor, evento.origen, evento.simulado])
                    cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', (bloqueo,))
                cur.execute('''INSERT INTO eventos
                    (stream,redis_id,sensor,tipo,fecha_evento,ip_origen,sesion,usuario,comando,simulado,tenant_id,raw_event_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING RETURNING id''',
                    (self.stream, evento.redis_id, evento.sensor, evento.tipo, evento.fecha,
                     evento.origen, evento.sesion, evento.usuario, evento.comando, evento.simulado,
                     evento.tenant_id, evento.raw_event_id))
                fila = cur.fetchone()
                if fila is None:
                    return False, []
                evento_id = fila[0]
                alertas = []
                for regla in detector.reglas_para(evento):
                    # Solo el laboratorio local tiene reglas configurables desde el panel.
                    if evento.tenant_id == "lab":
                        cur.execute("SELECT umbral, ventana_segundos FROM configuracion_alertas WHERE regla=%s", (regla.nombre,))
                        configuracion = cur.fetchone()
                        if configuracion:
                            regla = replace(regla, umbral=configuracion[0], ventana_segundos=configuracion[1])
                    # USAR EL EXTREMO MAS RECIENTE DE LA VENTANA AUNQUE LOS EVENTOS LLEGUEN FUERA DE ORDEN.
                    cur.execute('''SELECT max(fecha_evento) FROM eventos WHERE tenant_id=%s AND sensor=%s AND tipo=%s
                        AND ip_origen=%s AND simulado=%s''',
                        (evento.tenant_id, evento.sensor, regla.tipo, evento.origen, evento.simulado))
                    fin = cur.fetchone()[0]
                    inicio = fin - timedelta(seconds=regla.ventana_segundos)
                    cur.execute('''SELECT redis_id FROM eventos WHERE tenant_id=%s AND sensor=%s AND tipo=%s
                        AND ip_origen=%s AND simulado=%s AND fecha_evento BETWEEN %s AND %s
                        ORDER BY fecha_evento, id''',
                        (evento.tenant_id, evento.sensor, regla.tipo, evento.origen, evento.simulado, inicio, fin))
                    ids = [fila[0] for fila in cur.fetchall()]
                    if not regla.alcanzada(len(ids)):
                        continue
                    # EVITAR ALERTAS REPETIDAS POR REGLA Y SENSOR DURANTE LA VENTANA.
                    cur.execute('''SELECT 1 FROM alertas a JOIN eventos e ON e.id=a.evento_id
                        WHERE a.regla=%s AND e.tenant_id=%s AND e.sensor=%s AND a.ip_origen=%s AND a.simulado=%s
                        AND a.fecha_alerta >= now() - (%s * interval '1 second') LIMIT 1''',
                        (regla.nombre, evento.tenant_id, evento.sensor, evento.origen, evento.simulado, regla.ventana_segundos))
                    if cur.fetchone():
                        continue
                    clave = hashlib.sha256(json.dumps(
                        [self.stream, evento.redis_id, regla.nombre], ensure_ascii=True
                    ).encode('utf-8')).hexdigest()
                    evidencia = json.dumps({'tipo': regla.tipo, 'sensor': evento.sensor,
                                            'stream': self.stream, 'redis_ids': ids})
                    descripcion = (f'{len(ids)} eventos {regla.tipo} en {regla.ventana_segundos} '
                                   f'segundos; umbral {regla.umbral}; requiere revision.')
                    cur.execute('''INSERT INTO alertas
                        (evento_id,regla,severidad,descripcion,ip_origen,simulado,estado,
                         umbral,ventana_segundos,cantidad,inicio_ventana,fin_ventana,evidencia,clave_deduplicacion)
                        VALUES (%s,%s,%s,%s,%s,%s,'nueva',%s,%s,%s,%s,%s,%s::jsonb,%s)
                        ON CONFLICT DO NOTHING RETURNING id''',
                        (evento_id, regla.nombre, regla.severidad, descripcion, evento.origen,
                         evento.simulado, regla.umbral, regla.ventana_segundos, len(ids), inicio,
                         fin, evidencia, clave))
                    if cur.fetchone():
                        alertas.append(regla.nombre)
                return True, alertas
