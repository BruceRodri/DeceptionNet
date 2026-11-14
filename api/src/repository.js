// CONSULTAS PARAMETRIZADAS SOBRE LAS COLUMNAS PERMITIDAS.
export function createRepository(pools, dynamicPool) {
  const poolFor = tenant => {const pool=pools[tenant] || dynamicPool?.(tenant);if(!pool)throw new Error('TENANT_NO_DISPONIBLE');return pool;};
  return {
    async health() { await poolFor('lab').query('SELECT 1'); },
    async overview(tenant) {
      const pool=poolFor(tenant);
      const window=Number(process.env.VENTANA_SEGUNDOS||300);
      const [totals, trend, severity, windowCounts, latest, monitoring] = await Promise.all([
        pool.query(`SELECT (SELECT count(*)::int FROM eventos WHERE tenant_id=$1) eventos,
          (SELECT count(*)::int FROM alertas WHERE tenant_id=$1) alertas,
          (SELECT count(DISTINCT sensor)::int FROM eventos WHERE tenant_id=$1) sensores,
          (SELECT count(*)::int FROM eventos WHERE tenant_id=$1 AND fecha_recepcion>now()-interval '30 minutes') recientes`,[tenant]),
        pool.query(`WITH buckets AS (SELECT generate_series(now()-interval '30 minutes',now()-interval '3 minutes',interval '3 minutes') AS inicio)
          SELECT inicio,(SELECT count(*)::int FROM eventos WHERE tenant_id=$1 AND fecha_recepcion>=inicio AND fecha_recepcion<inicio+interval '3 minutes') eventos,
          (SELECT count(*)::int FROM alertas WHERE tenant_id=$1 AND fecha_alerta>=inicio AND fecha_alerta<inicio+interval '3 minutes') alertas FROM buckets ORDER BY inicio`,[tenant]),
        pool.query('SELECT severidad,count(*)::int cantidad FROM alertas WHERE tenant_id=$1 GROUP BY severidad',[tenant]),
        pool.query(`SELECT ip_origen,count(*)::int cantidad,max(fecha_evento) ultima FROM eventos WHERE tenant_id=$1
          AND sensor='cowrie-ssh' AND tipo='cowrie.session.connect' AND simulado=false
          AND fecha_evento>now()-($2*interval '1 second') AND fecha_evento<=now() GROUP BY ip_origen ORDER BY cantidad DESC LIMIT 6`,[tenant,window]),
        pool.query(`SELECT id,sensor,tipo,fecha_evento,fecha_recepcion,ip_origen,simulado,usuario,comando FROM eventos WHERE tenant_id=$1 ORDER BY id DESC LIMIT 12`,[tenant]),
        pool.query(`SELECT s.sensor,e.id AS evento_id,e.tipo AS evento_tipo,e.fecha_recepcion AS evento_fecha,e.ip_origen AS evento_origen,e.simulado AS evento_simulado,
          a.id AS alerta_id,a.regla AS alerta_regla,a.fecha_alerta,a.severidad,a.simulado AS alerta_simulado
          FROM unnest($2::text[]) AS s(sensor)
          LEFT JOIN LATERAL (SELECT id,tipo,fecha_recepcion,ip_origen,simulado FROM eventos
            WHERE tenant_id=$1 AND sensor=s.sensor ORDER BY id DESC LIMIT 1) e ON true
          LEFT JOIN LATERAL (SELECT a.id,a.regla,a.fecha_alerta,a.severidad,a.simulado FROM alertas a JOIN eventos ev ON ev.id=a.evento_id
            WHERE ev.tenant_id=$1 AND ev.sensor=s.sensor ORDER BY a.id DESC LIMIT 1) a ON true`,
          [tenant,['cowrie-ssh','canary-web','canary-bd']])
      ]);
      return {totales:totals.rows[0],tendencia:trend.rows,severidad:severity.rows,ventana:windowCounts.rows,recientes:latest.rows,monitoreo:monitoring.rows,
        reglas:{conexiones:Number(process.env.UMBRAL_CONEXIONES||10),fallos:Number(process.env.UMBRAL_FALLOS||5),ventana_segundos:window},
        politica_mtd:process.env.MTD_POLITICA||'adaptativa',actualizado_en:new Date().toISOString()};
    },
    async events({ page, limit, sensor, simulated, tenant }) {
      const pool=poolFor(tenant);
      const args = [tenant]; const conditions = ['tenant_id = $1'];
      if (sensor) { args.push(sensor); conditions.push(`sensor = $${args.length}`); }
      if (simulated !== undefined) { args.push(simulated); conditions.push(`simulado = $${args.length}`); }
      const where = conditions.join(' AND ');
      const total = Number((await pool.query(`SELECT count(*) AS n FROM eventos WHERE ${where}`, args)).rows[0].n);
      const values = [...args, limit, (page - 1) * limit];
      const rows = (await pool.query(`SELECT id,sensor,tipo,fecha_evento,fecha_recepcion,ip_origen,simulado,usuario,comando
        FROM eventos WHERE ${where} ORDER BY id DESC LIMIT $${args.length + 1} OFFSET $${args.length + 2}`, values)).rows;
      return { data: rows, pagination: { page, limit, total, pages: Math.ceil(total / limit) } };
    },
    async alerts({ page, limit, sensor, simulated, tenant }) {
      const pool=poolFor(tenant);
      const args = [tenant]; const conditions = ['e.tenant_id = $1'];
      if (sensor) { args.push(sensor); conditions.push(`e.sensor = $${args.length}`); }
      if (simulated !== undefined) { args.push(simulated); conditions.push(`a.simulado = $${args.length}`); }
      const where = conditions.join(' AND ');
      const total = Number((await pool.query(`SELECT count(*) AS n FROM alertas a JOIN eventos e ON e.id=a.evento_id WHERE ${where}`, args)).rows[0].n);
      const rows = (await pool.query(`SELECT a.id,a.evento_id,a.regla,a.severidad,a.descripcion,a.ip_origen,
        a.fecha_alerta,a.simulado,a.estado,a.umbral,a.ventana_segundos,a.cantidad,e.sensor
        FROM alertas a JOIN eventos e ON e.id=a.evento_id WHERE ${where} ORDER BY a.id DESC
        LIMIT $${args.length + 1} OFFSET $${args.length + 2}`, [...args, limit, (page - 1) * limit])).rows;
      return { data: rows, pagination: { page, limit, total, pages: Math.ceil(total / limit) } };
    },
    async sensors(tenant) {
      const pool=poolFor(tenant);
      return (await pool.query(`SELECT sensor,count(*)::int AS eventos,max(fecha_evento) AS ultimo_evento
        FROM eventos WHERE tenant_id=$1 GROUP BY sensor ORDER BY sensor`, [tenant])).rows;
    },
    async alertById(id) {
      for (const pool of Object.values(pools)) {
      const result = await pool.query(`SELECT a.id,a.regla,a.severidad,a.fecha_alerta,a.simulado,e.sensor,e.tenant_id
        FROM alertas a JOIN eventos e ON e.id=a.evento_id
        WHERE a.id=$1`, [id]);
      if(result.rows[0])return result.rows[0];
      }
      return null;
    },
    async eventById(id,tenant) {return (await poolFor(tenant).query('SELECT id,sensor,tipo,fecha_evento,fecha_recepcion,ip_origen,simulado,usuario,comando FROM eventos WHERE id=$1',[id])).rows[0]||null;},
    async alertForTenant(id,tenant) {return (await poolFor(tenant).query('SELECT id,evento_id,regla,severidad,descripcion,fecha_alerta,simulado FROM alertas WHERE id=$1',[id])).rows[0]||null;},
    async policies(tenant) {return (await poolFor(tenant).query('SELECT id,nombre,activa,sensor_id FROM politicas_mtd ORDER BY id')).rows;},
    async audit(tenant) {return (await poolFor(tenant).query('SELECT id,usuario_id,accion,resultado,fecha,detalle FROM auditoria_local ORDER BY id DESC LIMIT 100')).rows;},
  };
}
