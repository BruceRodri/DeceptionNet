"""ADAPTAR EVENTOS OPENCANARY AL ESQUEMA COMUN SIN COPIAR CREDENCIALES."""
from datetime import datetime, timezone


def adaptar_opencanary(evento, sensor, raw_event_id):
    """SELECCIONAR SOLO METADATOS PERMITIDOS DE UN EVENTO DE RED."""
    origen = str(evento.get('src_host', '')).strip()
    codigo = evento.get('logtype')
    if not origen or not isinstance(codigo, int):
        return None
    fecha = datetime.fromisoformat(str(evento['utc_time']).replace('Z', '+00:00'))
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    servicio = 'http' if sensor == 'canary-web' else 'mysql'
    return {'tenant_id': 'lab', 'sensor': sensor, 'raw_event_id': raw_event_id,
            'eventid': f'opencanary.{servicio}.{codigo}',
            'timestamp': fecha.isoformat(), 'src_ip': origen, 'session': '',
            'simulado': 'false'}
