"""POLITICA ADAPTATIVA LIMITADA AL GATEWAY SSH DE LABORATORIO."""
import logging
import os
import time
from pathlib import Path
import psycopg

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG=logging.getLogger('controlador')
COOLDOWN=int(os.getenv('MTD_COOLDOWN_SEGUNDOS','20'))
POLITICA=os.getenv('MTD_POLITICA','adaptativa')
if POLITICA not in ('adaptativa','estatica','periodica'): raise ValueError('POLITICA NO PERMITIDA')
if COOLDOWN < 1: raise ValueError('COOLDOWN DEBE SER POSITIVO')
PUERTOS=(2201,2202,2203)


def evaluar(regla,sensor,simulado,origen,gateway_ip):
    """PUNTUAR SIN CONSIDERAR MALICIOSOS LOS EVENTOS AISLADOS."""
    riesgo={'multiples_conexiones':60,'autenticaciones_fallidas':40}.get(regla,0)
    if sensor!='cowrie-ssh': return riesgo,'SENSOR NO HABILITADO'
    if simulado: return riesgo,'EVENTO SIMULADO NO AUTORIZA MTD AUTOMATICO'
    if not gateway_ip: return riesgo,'GATEWAY SIN IP DE ORIGEN CONFIRMADA'
    if origen==gateway_ip: return riesgo,'VERIFICACION INTERNA DEL GATEWAY'
    if riesgo<60: return riesgo,'RIESGO POR DEBAJO DEL UMBRAL'
    return riesgo,'UMBRAL DE RIESGO ALCANZADO'


def procesar(db):
    """SERIALIZAR CURSOR, DECISION Y SOLICITUD EN UNA TRANSACCION."""
    with db.transaction():
        cursor=db.execute("SELECT ultima_alerta FROM mtd_control_estado WHERE tenant_id='lab' FOR UPDATE").fetchone()[0]
        alerta=db.execute('''SELECT a.id,a.regla,a.simulado,a.ip_origen,e.sensor FROM alertas a
            JOIN eventos e ON e.id=a.evento_id WHERE e.tenant_id='lab' AND a.id>%s ORDER BY a.id LIMIT 1''',(cursor,)).fetchone()
        if not alerta: return False
        id_alerta,regla,simulado,origen,sensor=alerta
        config=db.execute("SELECT puerto,gateway_ip FROM mtd_config WHERE tenant_id='lab' AND sensor='cowrie-ssh'").fetchone()
        puntuacion,motivo=evaluar(regla,sensor,simulado,origen,config[1])
        if POLITICA != 'adaptativa': motivo=f'POLITICA EXPERIMENTAL {POLITICA.upper()}: SIN ACCION POR ALERTA'
        resultado='sin_accion'; accion_id=None
        if motivo=='UMBRAL DE RIESGO ALCANZADO':
            reciente=db.execute('''SELECT 1 FROM mtd_acciones WHERE tenant_id='lab' AND sensor='cowrie-ssh'
                AND estado IN ('solicitada','en_proceso','aplicada')
                AND solicitada_en>=now()-(%s*interval '1 second') LIMIT 1''',(COOLDOWN,)).fetchone()
            if reciente:
                resultado='cooldown'; motivo=f'COOLDOWN DE {COOLDOWN} SEGUNDOS'
            else:
                puerto=PUERTOS[(PUERTOS.index(config[0])+1)%len(PUERTOS)]
                accion=db.execute('''INSERT INTO mtd_acciones(tenant_id,sensor,puerto_destino,tipo,motivo,clave,alerta_id)
                    VALUES ('lab','cowrie-ssh',%s,'adaptativo',%s,%s,%s)
                    ON CONFLICT (clave) DO NOTHING RETURNING id''',
                    (puerto,f'RIESGO {puntuacion}; ALERTA {id_alerta}',f'alerta:lab:{id_alerta}',id_alerta)).fetchone()
                if accion: accion_id=accion[0]; resultado='solicitada'
                else: motivo='ACCION YA SOLICITADA'
        db.execute('''INSERT INTO mtd_decisiones(tenant_id,alerta_id,sensor,puntuacion,resultado,motivo,accion_id)
            VALUES ('lab',%s,%s,%s,%s,%s,%s) ON CONFLICT (tenant_id,alerta_id) DO NOTHING''',
            (id_alerta,sensor,puntuacion,resultado,motivo,accion_id))
        db.execute("UPDATE mtd_control_estado SET ultima_alerta=%s WHERE tenant_id='lab'",(id_alerta,))
        LOG.info('ALERTA %s: RIESGO=%s DECISION=%s',id_alerta,puntuacion,resultado)
    return True


def ejecutar():
    clave=Path('/run/secrets/controlador_db_password').read_text(encoding='ascii').strip()
    with psycopg.connect(host='postgres',dbname=os.environ['POSTGRES_DB'],user='dn_mtd_control',
                         password=clave,autocommit=True,connect_timeout=5) as db:
        if not db.execute('SELECT pg_try_advisory_lock(772130)').fetchone()[0]:
            raise RuntimeError('OTRO CONTROLADOR ESTA ACTIVO')
        LOG.info('CONTROLADOR ACTIVO; COOLDOWN=%s SEGUNDOS',COOLDOWN)
        while True:
            if not procesar(db): time.sleep(1)


if __name__=='__main__':
    while True:
        try: ejecutar()
        except (psycopg.Error,OSError,RuntimeError) as error:
            LOG.error('CONTROLADOR INTERRUMPIDO: %s; REINTENTO EN 5 SEGUNDOS',type(error).__name__)
            time.sleep(5)
