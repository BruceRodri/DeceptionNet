import express from 'express';
import { parseFilters } from './validation.js';

// LA API EXPONE SOLO CONSULTAS PARA EL LABORATORIO LOCAL.
export function createApp(repository, auth) {
  const app = express(); app.disable('x-powered-by');
  app.use(express.json({limit:'8kb'}));
  app.use((req, res, next) => {
    const origin = req.get('origin');
    if (['http://127.0.0.1:8081', 'http://localhost:8081'].includes(origin)) {
      res.set('Access-Control-Allow-Origin', origin); res.set('Vary', 'Origin');
    }
    res.set('Cache-Control', 'no-store'); next();
  });
  app.get('/health', async (_req, res, next) => { try { await repository.health(); res.json({ status: 'ok', database: 'ok' }); } catch (e) { next(e); } });
  app.use('/api/auth',auth.router);
  app.use('/api',auth.requireAuth);
  if(auth.alertRulesRouter) app.use('/api/alert-rules',auth.alertRulesRouter);
  if(auth.mtdRouter) app.use('/api/mtd',auth.mtdRouter);
  if(auth.remoteRouter) app.use('/api/remote/commands',auth.remoteRouter);
  if(auth.companiesRouter) app.use('/api/companies',auth.companiesRouter);
  app.get('/api/overview',async(req,res,next)=>{try{res.json(await repository.overview(req.user.tenant_id))}catch(e){next(e)}});
  app.get('/api/admin/audit',auth.requireAdmin,async (req,res,next)=>{try{res.json({data:await repository.audit(req.user.tenant_id)})}catch(e){next(e)}});
  app.post('/api/admin/check',auth.requireAdmin,async(req,res,next)=>{try{await auth.audit(req.user.id,'admin.verificacion','permitido');res.json({estado:'permitido'})}catch(e){next(e)}});
  for (const [path, method] of [['/api/events','events'], ['/api/alerts','alerts']]) {
    app.get(path, async (req, res, next) => {
      let filters; try { filters = parseFilters(req.query); } catch (e) { return res.status(400).json({ error: 'PARAMETROS_INVALIDOS', mensaje: e.message }); }
      try { res.json(await repository[method]({...filters,tenant:req.user.tenant_id})); } catch (e) { next(e); }
    });
  }
  app.get('/api/sensors', async (req, res, next) => { try { res.json({ data: await repository.sensors(req.user.tenant_id) }); } catch (e) { next(e); } });
  app.get('/api/policies',async(req,res,next)=>{try{res.json({data:await repository.policies(req.user.tenant_id)})}catch(e){next(e)}});
  for(const [path,method] of [['events','eventById'],['alerts','alertForTenant']]) app.get(`/api/${path}/:id`,async(req,res,next)=>{
    if(!/^[1-9]\d{0,18}$/.test(req.params.id))return res.status(400).json({error:'ID_INVALIDO'});
    try{const row=await repository[method](req.params.id,req.user.tenant_id);if(!row)return res.status(404).json({error:'NO_ENCONTRADO'});res.json(row)}catch(e){next(e)}
  });
  app.use((_req, res) => res.status(404).json({ error: 'NO_ENCONTRADO', mensaje: 'Ruta no encontrada' }));
  app.use((error, _req, res, _next) => { console.error('ERROR DE CONSULTA:', error.code || error.name); res.status(503).json({ error: 'SERVICIO_NO_DISPONIBLE', mensaje: 'No se pudo consultar la base de datos' }); });
  return app;
}
