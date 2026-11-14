"""VALIDAR INTEGRIDAD, DESTINO Y VIGENCIA DE UNA ORDEN REMOTA."""
from datetime import datetime,timezone
import hashlib,hmac,json,uuid
def validar_orden(order,tenant,token):
    if not isinstance(order,dict) or set(order)!={'id','tenant_id','sensor','puerto','vence_en','firma'}:raise ValueError('ORDEN INVALIDA')
    order=dict(order);signature=order.pop('firma')
    if not isinstance(signature,str):raise ValueError('FIRMA INVALIDA')
    raw=json.dumps(order,sort_keys=True,separators=(',',':')).encode()
    expected=hmac.new(token.encode(),raw,hashlib.sha256).hexdigest()
    uuid.UUID(order['id'])
    if not hmac.compare_digest(signature,expected) or order['tenant_id']!=tenant or order['sensor']!='sensor-remoto-'+tenant[-1] or type(order['puerto']) is not int or order['puerto'] not in (2301,2302):raise ValueError('ORDEN NO AUTORIZADA')
    expiry=datetime.fromisoformat(order['vence_en'])
    if expiry.tzinfo is None or expiry<=datetime.now(timezone.utc):raise ValueError('ORDEN CADUCADA')
    return order
