// AUTORIZAR SOLO CAMBIOS DE PUERTOS DE SENUEL0S DE LA ORGANIZACION.
import express from 'express';
import crypto from 'node:crypto';
export function createRemoteRouter(pool,auth){
 const router=express.Router();
 router.get('/',auth.requireAdmin,async(req,res,next)=>{try{
  const r=await pool.query('SELECT id,sensor,puerto,estado,creada_en,vence_en,resultado,confirmada_en FROM ordenes_remotas WHERE tenant_id=$1 ORDER BY creada_en DESC LIMIT 30',[req.user.tenant_id]);res.json({data:r.rows});
 }catch(e){next(e)}});
 router.post('/',auth.requireAdmin,async(req,res,next)=>{
  const tenant=req.user.tenant_id;
  if(!['empresa_a','empresa_b'].includes(tenant))return res.status(403).json({error:'TENANT_SIN_AGENTE'});
  const {puerto,clave,ttl_segundos}=req.body||{};
  if(Object.keys(req.body||{}).some(x=>!['puerto','clave','ttl_segundos'].includes(x))||![2301,2302].includes(puerto)||typeof clave!=='string'||!/^[a-zA-Z0-9_-]{16,80}$/.test(clave)||!Number.isInteger(ttl_segundos)||ttl_segundos<5||ttl_segundos>120)return res.status(400).json({error:'ORDEN_INVALIDA'});
  const sensor='sensor-remoto-'+tenant.slice(-1);let client;
  try{client=await pool.connect();await client.query('BEGIN');
   const r=await client.query(`INSERT INTO ordenes_remotas(id,tenant_id,sensor,puerto,clave,solicitado_por,vence_en)
    VALUES($1,$2,$3,$4,$5,$6,now()+($7*interval '1 second')) ON CONFLICT(tenant_id,clave) DO NOTHING RETURNING id,puerto,estado`,[crypto.randomUUID(),tenant,sensor,puerto,clave,req.user.id,ttl_segundos]);
   const row=r.rows[0]||(await client.query('SELECT id,puerto,estado FROM ordenes_remotas WHERE tenant_id=$1 AND clave=$2',[tenant,clave])).rows[0];
   if(!row||row.puerto!==puerto){await client.query('ROLLBACK');return res.status(409).json({error:'CLAVE_EN_CONFLICTO'});}
   if(r.rowCount)await client.query("INSERT INTO auditoria_local(usuario_id,accion,resultado,detalle) VALUES($1,'mtd.remoto','solicitado',$2)",[req.user.id,`ORDEN ${row.id}`]);
   await client.query('COMMIT');res.status(r.rowCount?202:200).json(row);
  }catch(e){if(client)await client.query('ROLLBACK').catch(()=>{});next(e)}finally{client?.release()}
 });
 return router;
}
