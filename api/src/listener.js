// ESCUCHAR NOTIFICACIONES DE POSTGRESQL Y REINTENTAR SI SE INTERRUMPE LA CONEXION.
import pg from 'pg';

export function startAlertListener(config, realtime) {
  let client; let timer; let stopped = false;
  function retry(actual) {
    if (client !== actual || stopped) return;
    client = undefined;
    realtime.listenerStatus(false);
    actual.end().catch(() => {});
    console.error('ESCUCHA DE ALERTAS DESCONECTADA; REINTENTO EN 3 SEGUNDOS');
    timer = setTimeout(connect, 3000);
  }
  async function connect() {
    if (stopped) return;
    const actual = new pg.Client(config); client = actual;
    actual.on('error', () => retry(actual));
    actual.on('end', () => retry(actual));
    actual.on('notification', event => {
      if(event.channel==='dn_actividad')realtime.publishChange(event.payload);
      if (event.channel === 'dn_alertas') {
        realtime.publishAlert(event.payload).catch(() => {
          console.error('NO SE PUDO CONSULTAR LA ALERTA; SE SOLICITA SINCRONIZACION');
          realtime.resync();
        });
      }
    });
    try {
      await actual.connect();
      await actual.query('LISTEN dn_alertas');
      await actual.query('LISTEN dn_actividad');
      if (client !== actual || stopped) return;
      console.log('ESCUCHA DE ALERTAS POSTGRESQL ACTIVA');
      realtime.listenerStatus(true);
      realtime.resync();
    } catch (_error) { retry(actual); }
  }
  connect();
  return () => { stopped = true; clearTimeout(timer); if (client) client.end().catch(() => {}); };
}
