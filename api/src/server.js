import fs from 'node:fs';
import { createServer } from 'node:http';
import pg from 'pg';
import { createRepository } from './repository.js';
import { createApp } from './app.js';
import { createRealtime } from './realtime.js';
import { startAlertListener } from './listener.js';
import { createAuth } from './auth.js';
import { createMtdRouter } from './mtd.js';
import { createRemoteRouter } from './remote.js';
import { createCompaniesRouter } from './companies.js';
import { createAlertRulesRouter } from './alertRules.js';

const password = fs.readFileSync('/run/secrets/api_db_password', 'utf8').trim();
const config = { host: 'postgres', database: process.env.POSTGRES_DB, user: 'dn_api_lectura', password,
  connectionTimeoutMillis: 5000, options: '-c default_transaction_read_only=on' };
const pools=Object.fromEntries(['lab','empresa_a','empresa_b'].map(tenant=>[tenant,new pg.Pool({
  ...config,user:`dn_rls_${tenant}`,password:fs.readFileSync(`/run/secrets/rls_${tenant}_password`,'utf8').trim(),max:3
})]));
const authPassword=fs.readFileSync('/run/secrets/auth_db_password','utf8').trim();
const jwtSecret=fs.readFileSync('/run/secrets/jwt_secret','utf8').trim();
const bootstrap=fs.readFileSync('/run/secrets/bootstrap_token','utf8').trim();
const authPool=new pg.Pool({host:'postgres',database:process.env.POSTGRES_DB,user:'dn_api_auth',password:authPassword,max:5,connectionTimeoutMillis:5000});
// Cada empresa nueva consulta con su identidad RLS; SET LOCAL se revierte al liberar la transacción.
function dynamicPool(tenant) {
  if(!/^org_[a-f0-9]{32}$/.test(tenant))return null;
  return {async query(sql,args) {
    const client=await authPool.connect();
    try {await client.query('BEGIN READ ONLY');await client.query(`SET LOCAL ROLE "dn_rls_${tenant}"`);
      const result=await client.query(sql,args);await client.query('COMMIT');return result;
    }catch(e){await client.query('ROLLBACK').catch(()=>{});throw e;}finally{client.release();}
  }};
}
const repository = createRepository(pools,dynamicPool);
const auth=createAuth(authPool,jwtSecret,bootstrap);
auth.alertRulesRouter=createAlertRulesRouter(authPool,auth);
auth.mtdRouter=createMtdRouter(authPool,auth);
auth.remoteRouter=createRemoteRouter(authPool,auth);
auth.companiesRouter=createCompaniesRouter(authPool,auth);
const server = createServer(createApp(repository,auth));
const realtime = createRealtime(server, repository, auth.verify);
auth.setLogoutHandler(hash=>realtime.disconnectSession(hash));
const stopListener = startAlertListener(config, realtime);
server.listen(3000, '0.0.0.0', () => console.log('API LOCAL INICIADA EN EL PUERTO 3000'));
process.on('SIGTERM', () => { stopListener(); realtime.io.close(() => server.close(() => {Object.values(pools).forEach(pool=>pool.end());authPool.end();})); });
