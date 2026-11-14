// ACEPTAR SOLO CAMBIOS DEL GATEWAY AUTORIZADOS PARA EL LABORATORIO.
import express from 'express';

export function createMtdRouter(pool, auth) {
  const router=express.Router();
  router.get('/',async(req,res,next)=>{
    try {
      const config=await pool.query('SELECT sensor,puerto,actualizado_en FROM mtd_config WHERE tenant_id=$1 AND sensor=$2',[req.user.tenant_id,'cowrie-ssh']);
      const acciones=await pool.query(`SELECT id,alerta_id,sensor,puerto_destino,puerto_anterior,tipo,estado,motivo,
        solicitada_en,terminada_en,duracion_ms,detalle FROM mtd_acciones WHERE tenant_id=$1 ORDER BY id DESC LIMIT 30`,[req.user.tenant_id]);
      const decisiones=await pool.query('SELECT id,alerta_id,puntuacion,resultado,motivo,accion_id,creada_en FROM mtd_decisiones WHERE tenant_id=$1 ORDER BY id DESC LIMIT 15',[req.user.tenant_id]);
      res.json({config:config.rows[0]||null,acciones:acciones.rows,decisiones:decisiones.rows});
    } catch(e){next(e);}
  });
  router.post('/manual',auth.requireAdmin,async(req,res,next)=>{
    if(req.user.tenant_id!=='lab') return res.status(403).json({error:'GATEWAY_NO_DISPONIBLE_PARA_TENANT'});
    const {puerto,motivo,clave}=req.body||{};
    if(![2201,2202,2203].includes(puerto)||typeof motivo!=='string'||motivo.trim().length<4||motivo.length>180||
       typeof clave!=='string'||!/^[a-zA-Z0-9_-]{16,80}$/.test(clave)) return res.status(400).json({error:'SOLICITUD_INVALIDA'});
    const key=`${req.user.tenant_id}:${req.user.id}:${clave}`;
    let client;
    try {
      client=await pool.connect();await client.query('BEGIN');
      const inserted=await client.query(`INSERT INTO mtd_acciones(tenant_id,sensor,puerto_destino,tipo,motivo,clave,solicitado_por)
        VALUES ($1,'cowrie-ssh',$2,'manual',$3,$4,$5) ON CONFLICT (clave) DO NOTHING RETURNING id,estado,puerto_destino`,
        [req.user.tenant_id,puerto,motivo.trim(),key,req.user.id]);
      const row=inserted.rows[0]||(await client.query('SELECT id,estado,puerto_destino FROM mtd_acciones WHERE clave=$1',[key])).rows[0];
      if(!row||row.puerto_destino!==puerto){await client.query('ROLLBACK');return res.status(409).json({error:'CLAVE_EN_CONFLICTO'});}
      if(inserted.rows.length) await client.query("INSERT INTO auditoria_local(usuario_id,accion,resultado,detalle) VALUES ($1,'mtd.manual','solicitado',$2)",[req.user.id,`ACCION ${row.id}, PUERTO ${puerto}`]);
      await client.query('COMMIT');res.status(inserted.rows.length?202:200).json(row);
    } catch(e){if(client)await client.query('ROLLBACK').catch(()=>{});next(e);} finally{client?.release();}
  });
  return router;
}
