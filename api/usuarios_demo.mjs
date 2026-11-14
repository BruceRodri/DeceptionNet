// CREAR Y DESACTIVAR USUARIOS TEMPORALES DE LAS EMPRESAS SIMULADAS.
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {promisify} from 'node:util';

// El asistente manual solo necesita módulos nativos de Node; conserva el mismo
// formato y parámetros scrypt utilizados por la autenticación del panel.
const scrypt=promisify(crypto.scrypt);
async function hashPassword(password){
  const salt=crypto.randomBytes(16);
  const key=await scrypt(password,salt,32,{N:32768,r:8,p:1,maxmem:128*1024*1024});
  return `scrypt$32768$8$1$${salt.toString('hex')}$${key.toString('hex')}`;
}

function sql(query){
  const result=spawnSync('docker',['compose','exec','-T','postgres','sh','-c','psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],{input:query,encoding:'utf8'});
  if(result.status!==0)throw new Error('NO SE PUDIERON ACTUALIZAR LOS USUARIOS DE DEMOSTRACION');
}
const mode=process.argv[2];
if(mode==='crear'){
  let input='';for await(const chunk of process.stdin){input+=chunk;if(input.length>2048)throw new Error('ENTRADA DEMASIADO GRANDE');}
  const {passwordA,passwordB}=JSON.parse(input);input='';
  if(typeof passwordA!=='string'||typeof passwordB!=='string'||passwordA.length<12||passwordB.length<12||passwordA.length>128||passwordB.length>128||passwordA===passwordB)throw new Error('LAS CONTRASENAS DEBEN SER DIFERENTES Y TENER ENTRE 12 Y 128 CARACTERES');
  const suffix=crypto.randomBytes(5).toString('hex'),userA=`demo_manual_a_${suffix}`,userB=`demo_manual_b_${suffix}`;
  const [hashA,hashB]=await Promise.all([hashPassword(passwordA),hashPassword(passwordB)]);
  sql(`INSERT INTO usuarios_locales(usuario,password_hash,rol,tenant_id,prueba) VALUES ('${userA}','${hashA}','admin','empresa_a',true),('${userB}','${hashB}','admin','empresa_b',true);`);
  console.log(`USUARIO DE EMPRESA A: ${userA}`);
  console.log(`USUARIO DE EMPRESA B: ${userB}`);
  console.log('GUARDA LOS NOMBRES PARA INICIAR SESION Y DESACTIVARLOS AL FINAL.');
}else if(mode==='desactivar'){
  const [userA,userB]=process.argv.slice(3);
  if(!/^demo_manual_a_[a-f0-9]{10}$/.test(userA||'')||!/^demo_manual_b_[a-f0-9]{10}$/.test(userB||'')||userA.slice(-10)!==userB.slice(-10))throw new Error('INDICA LOS DOS USUARIOS DE LA MISMA DEMOSTRACION');
  sql(`UPDATE usuarios_locales SET activo=false WHERE prueba=true AND usuario IN ('${userA}','${userB}');`);
  console.log('USUARIOS DE DEMOSTRACION DESACTIVADOS');
}else{
  console.error('USO: EJECUTA EL ASISTENTE DE POWERSHELL O INDICA desactivar Y LOS DOS USUARIOS');
  process.exitCode=1;
}
