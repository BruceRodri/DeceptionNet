import express from 'express';

const defaults=()=>({
 multiples_conexiones:{umbral:Number(process.env.UMBRAL_CONEXIONES||10),ventana_segundos:Number(process.env.VENTANA_SEGUNDOS||300)},
 intento_acceso_web_local:{umbral:1,ventana_segundos:Number(process.env.VENTANA_SEGUNDOS||300)},
 intento_acceso_mysql_local:{umbral:1,ventana_segundos:Number(process.env.VENTANA_SEGUNDOS||300)}
});
export function createAlertRulesRouter(pool,auth){
 const router=express.Router();
 router.use((req,res,next)=>req.user.tenant_id==='lab'?next():res.status(403).json({error:'SOLO_LABORATORIO'}));
 router.get('/',async(req,res,next)=>{try{const result=defaults();const rows=await pool.query('SELECT regla,umbral,ventana_segundos FROM configuracion_alertas');for(const row of rows.rows)result[row.regla]={umbral:row.umbral,ventana_segundos:row.ventana_segundos};res.json(result)}catch(e){next(e)}});
 router.post('/',auth.requireAdmin,async(req,res,next)=>{
  const reglas=req.body, names=Object.keys(defaults());
  if(!reglas||typeof reglas!=='object'||Array.isArray(reglas)||Object.keys(reglas).length!==names.length||!names.every(name=>{const r=reglas[name];return r&&Number.isInteger(r.umbral)&&r.umbral>=1&&r.umbral<=1000&&Number.isInteger(r.ventana_segundos)&&r.ventana_segundos>=10&&r.ventana_segundos<=86400}))return res.status(400).json({error:'PARAMETROS_INVALIDOS',mensaje:'Usa umbrales de 1 a 1000 y ventanas de 10 a 86400 segundos.'});
  let client;try{client=await pool.connect();await client.query('BEGIN');for(const name of names){const r=reglas[name];await client.query(`INSERT INTO configuracion_alertas(regla,umbral,ventana_segundos) VALUES ($1,$2,$3) ON CONFLICT (regla) DO UPDATE SET umbral=EXCLUDED.umbral,ventana_segundos=EXCLUDED.ventana_segundos,actualizado_en=now()`,[name,r.umbral,r.ventana_segundos]);}await client.query("INSERT INTO auditoria_local(usuario_id,accion,resultado,detalle) VALUES ($1,'alertas.configuracion','permitido',$2)",[req.user.id,JSON.stringify(reglas)]);await client.query('COMMIT');res.json({estado:'guardada'});}catch(e){if(client)await client.query('ROLLBACK').catch(()=>{});next(e)}finally{client?.release()}
 });
 return router;
}
