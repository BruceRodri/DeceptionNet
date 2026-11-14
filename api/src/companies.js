import express from 'express';
import crypto from 'node:crypto';
import { hashPassword } from './auth.js';

export function createCompaniesRouter(pool, auth) {
  const router = express.Router();
  router.get('/', async (req,res,next) => {
    try {
      const global = req.user.tenant_id === 'lab' && req.user.rol === 'admin';
      const data = await pool.query(`SELECT o.id,o.nombre,o.simulada,o.creada_en,
        (SELECT count(*)::int FROM sensores_registro s WHERE s.tenant_id=o.id) AS sensores
        FROM organizaciones o WHERE ($1::boolean OR o.id=$2) ORDER BY o.creada_en,o.nombre`,[global,req.user.tenant_id]);
      res.json({data:data.rows,puede_registrar:global,actual:req.user.tenant_id});
    } catch(e) {next(e);}
  });
  router.post('/', auth.requireAdmin, async (req,res,next) => {
    if(req.user.tenant_id!=='lab')return res.status(403).json({error:'SOLO_ADMINISTRADOR_LOCAL'});
    const {nombre,usuario,password}=req.body||{};
    if(Object.keys(req.body||{}).some(k=>!['nombre','usuario','password'].includes(k)) ||
      typeof nombre!=='string'||nombre.trim().length<2||nombre.trim().length>80||
      typeof usuario!=='string'||!/^[a-zA-Z0-9_]{3,60}$/.test(usuario)||
      typeof password!=='string'||password.length<12||password.length>128)
      return res.status(400).json({error:'DATOS_INVALIDOS',mensaje:'Nombre de 2 a 80 caracteres, usuario de 3 a 60 letras, números o guion bajo y contraseña de 12 a 128 caracteres.'});
    let client;
    try {
      const hash=await hashPassword(password), id='org_'+crypto.randomBytes(16).toString('hex');
      client=await pool.connect();await client.query('BEGIN');
      await client.query('SELECT registrar_empresa_panel($1,$2,$3,$4)',[id,nombre.trim(),usuario,hash]);
      await client.query("INSERT INTO auditoria_local(usuario_id,accion,resultado,detalle) VALUES($1,'empresa.registro','creada',$2)",[req.user.id,id]);
      await client.query('COMMIT');res.status(201).json({id,nombre:nombre.trim(),usuario,estado:'pendiente_de_agente'});
    } catch(e) {
      if(client)await client.query('ROLLBACK').catch(()=>{});
      if(e.code==='23505')return res.status(409).json({error:'REGISTRO_DUPLICADO',mensaje:'Ya existe una empresa o un usuario con ese nombre.'});
      next(e);
    } finally {client?.release();}
  });
  return router;
}
