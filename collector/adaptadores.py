"""ADAPTAR COWRIE AL ESQUEMA COMUN SIN COPIAR CONTRASEÑAS."""
def adaptar_cowrie(evento, raw_event_id):
    datos = {
        'tenant_id': 'lab', 'sensor': 'cowrie-ssh', 'raw_event_id': raw_event_id,
        'eventid': str(evento.get('eventid', '')), 'timestamp': str(evento.get('timestamp', '')),
        'src_ip': str(evento.get('src_ip', '')), 'session': str(evento.get('session', '')),
        'simulado': 'false',
    }
    if evento.get('username'):
        datos['username'] = str(evento['username'])
    if evento.get('eventid') == 'cowrie.command.input':
        datos['input'] = str(evento.get('input', ''))
    return datos
