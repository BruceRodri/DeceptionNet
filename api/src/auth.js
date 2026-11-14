// AUTENTICAR USUARIOS LOCALES CON SCRYPT Y SESIONES JWT REVOCABLES.
import crypto from 'node:crypto';
import { promisify } from 'node:util';
import jwt from 'jsonwebtoken';
import express from 'express';

const scrypt = promisify(crypto.scrypt);
const opciones = { N: 32768, r: 8, p: 1, maxmem: 128*1024*1024 };
const digest = value => crypto.createHash('sha256').update(value).digest('hex');
const seguro = (a,b) => { const x=Buffer.from(String(a)),y=Buffer.from(String(b)); return x.length===y.length && crypto.timingSafeEqual(x,y); };
export async function hashPassword(password) {
  const salt=crypto.randomBytes(16); const clave=await scrypt(password,salt,32,opciones);
  return `scrypt$32768$8$1$${salt.toString('hex')}$${clave.toString('hex')}`;
}
export async function verifyPassword(password, stored) {
  const [alg,n,r,p,salt,hash]=String(stored).split('$');
  if(alg!=='scrypt'||n!=='32768'||r!=='8'||p!=='1'||!/^[0-9a-f]{32}$/.test(salt||'')||!/^[0-9a-f]{64}$/.test(hash||'')) return false;
  const actual=await scrypt(password,Buffer.from(salt,'hex'),32,opciones);
  return crypto.timingSafeEqual(actual,Buffer.from(hash,'hex'));
}
const extraer = request => {
  const header=request.headers.authorization || '';
  return header.startsWith('Bearer ') ? header.slice(7) : '';
};

export function createAuth(pool, secret, bootstrap) {
  const attempts=new Map();
  let onLogout=()=>{};
  async function audit(user,action,result,detail='') {
    await pool.query('INSERT INTO auditoria_local(usuario_id,accion,resultado,detalle) VALUES ($1,$2,$3,$4)', [user,action,result,detail]);
  }
  async function verify(token) {
    let claims;
    try { claims=jwt.verify(token,secret,{ algorithms:['HS256'],issuer:'deceptionnet-local',audience:'deceptionnet-panel' }); }
    catch { return null; }
    if(typeof claims.jti!=='string'||!/^[a-f0-9]{64}$/.test(claims.jti)) return null;
    const hash=digest(claims.jti);
    const r=await pool.query(`SELECT u.id,u.usuario,u.rol,u.tenant_id,s.vence_en FROM sesiones_locales s
      JOIN usuarios_locales u ON u.id=s.usuario_id WHERE s.id_hash=$1 AND s.revocada_en IS NULL
      AND s.vence_en>now() AND u.activo=true`,[hash]);
    if(!r.rows.length) return null;
    const user=r.rows[0];
    if(String(user.id)!==claims.sub || user.rol!==claims.rol || user.tenant_id!==claims.tenant) return null;
    return {...user,sessionHash:hash,exp:claims.exp};
  }
  async function requireAuth(req,res,next) {
    try { const user=await verify(extraer(req)); if(!user) return res.status(401).json({error:'NO_AUTENTICADO'}); req.user=user; next(); }
    catch { res.status(503).json({error:'AUTENTICACION_NO_DISPONIBLE'}); }
  }
  function requireAdmin(req,res,next) {
    if(req.user.rol==='admin') return next();
    audit(req.user.id,'admin.acceso','denegado').then(()=>res.status(403).json({error:'PROHIBIDO'})).catch(()=>res.status(503).json({error:'AUDITORIA_NO_DISPONIBLE'}));
  }
  const router=express.Router();
  router.get('/setup-status',async (_req,res,next)=>{try {const r=await pool.query('SELECT count(*)::int AS n FROM usuarios_locales WHERE prueba=false'); res.json({requiere_configuracion:r.rows[0].n===0});}catch(e){next(e)}});
  router.post('/setup',async (req,res,next)=>{
    const {codigo,admin_password,analista_password}=req.body || {};
    if(!seguro(codigo||'',bootstrap)||typeof admin_password!=='string'||typeof analista_password!=='string'||
       admin_password.length<12||analista_password.length<12||admin_password.length>128||analista_password.length>128||admin_password===analista_password)
      return res.status(400).json({error:'CONFIGURACION_INVALIDA',mensaje:'Código incorrecto o contraseñas inválidas (mínimo 12 caracteres y diferentes).'});
    try {
      const [a,b]=await Promise.all([hashPassword(admin_password),hashPassword(analista_password)]);
      const client=await pool.connect();
      try { await client.query('BEGIN'); await client.query('SELECT pg_advisory_xact_lock(772110)');
        const actual=await client.query('SELECT count(*)::int AS n FROM usuarios_locales WHERE prueba=false');
        if(actual.rows[0].n) {await client.query('ROLLBACK');return res.status(409).json({error:'YA_CONFIGURADO'});}
        await client.query("INSERT INTO usuarios_locales(usuario,password_hash,rol,tenant_id) VALUES ('admin',$1,'admin','lab'),('analista',$2,'analista','lab')",[a,b]);
        await client.query("INSERT INTO auditoria_local(accion,resultado,detalle) VALUES ('configuracion.inicial','permitido','Usuarios locales creados')");
        await client.query('COMMIT'); res.status(201).json({estado:'configurado'});
      } catch(e) {await client.query('ROLLBACK');throw e;} finally {client.release();}
    } catch(e) {next(e);}
  });
  router.post('/login',async (req,res,next)=>{
    const {usuario,password}=req.body || {};
    if(typeof usuario!=='string'||typeof password!=='string'||usuario.length>80||password.length>128||password.length<1) return res.status(400).json({error:'ENTRADA_INVALIDA'});
    const key=req.ip; const ahora=Date.now(); let intento=attempts.get(key);
    if(!intento||ahora-intento.inicio>60000) {intento={inicio:ahora,n:0};attempts.set(key,intento);}
    if(intento.n>=10) return res.status(429).json({error:'DEMASIADOS_INTENTOS'});
    intento.n++;
    try {
      const r=await pool.query('SELECT id,usuario,password_hash,rol,tenant_id,activo FROM usuarios_locales WHERE usuario=$1',[usuario]);
      const user=r.rows[0];
      const dummy='scrypt$32768$8$1$'+'0'.repeat(32)+'$'+'0'.repeat(64);
      const coincide=await verifyPassword(password,user?.password_hash||dummy);
      if(!user||!user.activo||!coincide) {await audit(user?.id||null,'sesion.inicio','denegado');return res.status(401).json({error:'CREDENCIALES_INVALIDAS'});}
      attempts.delete(key);
      const jti=crypto.randomBytes(32).toString('hex');
      const token=jwt.sign({rol:user.rol,tenant:user.tenant_id},secret,{algorithm:'HS256',subject:String(user.id),jwtid:jti,expiresIn:'10m',issuer:'deceptionnet-local',audience:'deceptionnet-panel'});
      await pool.query("INSERT INTO sesiones_locales(id_hash,usuario_id,vence_en) VALUES ($1,$2,now()+interval '10 minutes')",[digest(jti),user.id]);
      await audit(user.id,'sesion.inicio','permitido');
      res.json({token,usuario:user.usuario,rol:user.rol,tenant_id:user.tenant_id,expires_in:600});
    } catch(e) {next(e);}
  });
  router.post('/logout',requireAuth,async (req,res,next)=>{
    try {await pool.query('UPDATE sesiones_locales SET revocada_en=now() WHERE id_hash=$1',[req.user.sessionHash]); await audit(req.user.id,'sesion.cierre','permitido'); onLogout(req.user.sessionHash); res.json({estado:'cerrada'});}
    catch(e){next(e);}
  });
  return {router,verify,requireAuth,requireAdmin,audit,
    setLogoutHandler(handler){onLogout=handler;}};
}
