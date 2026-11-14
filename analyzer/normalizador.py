"""NORMALIZACION DE MENSAJES SIN ALMACENAR CONTRASEÑAS."""
from dataclasses import dataclass
from datetime import datetime, timezone
import logging


@dataclass(frozen=True)
class Evento:
    """CAMPOS PERMITIDOS PARA EL ANALISIS Y LA PERSISTENCIA."""
    redis_id: str
    tenant_id: str
    raw_event_id: str | None
    sensor: str
    tipo: str
    fecha: datetime
    origen: str | None
    sesion: str | None
    usuario: str | None
    comando: str | None
    simulado: bool


def normalizar(redis_id, datos):
    """CONVERTIR EL MENSAJE A CAMPOS CONTROLADOS Y SIN CONTRASEÑA."""
    try:
        fecha = datetime.fromisoformat(datos.get('timestamp', '').replace('Z', '+00:00'))
        if fecha.tzinfo is None:
            raise ValueError('FECHA SIN ZONA HORARIA')
    except (ValueError, AttributeError, OverflowError):
        logging.warning('FECHA INVALIDA EN %s; SE USA LA FECHA DE REDIS', redis_id)
        fecha = datetime.fromtimestamp(int(redis_id.split('-')[0]) / 1000, timezone.utc)
    return Evento(
        redis_id=redis_id, tenant_id=datos.get('tenant_id', 'lab') or 'lab',
        raw_event_id=datos.get('raw_event_id') or None,
        sensor=datos.get('sensor', ''), tipo=datos.get('eventid', ''),
        fecha=fecha, origen=datos.get('src_ip', '').strip() or None,
        sesion=datos.get('session') or None, usuario=datos.get('username') or None,
        comando=datos.get('input') or None,
        simulado=datos.get('simulado', '').lower() in ('true', '1', 'si'),
    )
