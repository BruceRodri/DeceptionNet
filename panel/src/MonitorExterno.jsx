import React,{useEffect,useState} from 'react';
import {Activity,AlertTriangle,ArrowRight,Database,Globe2,Radio,TerminalSquare} from 'lucide-react';
import TracePanel from './TracePanel.jsx';

const sensors=[
 {id:'cowrie-ssh',name:'SSH',icon:TerminalSquare,color:'cyan',desc:'Acceso remoto · Cowrie',rule:'10 conexiones por origen en la ventana configurada'},
 {id:'canary-web',name:'Web',icon:Globe2,color:'violet',desc:'Página de acceso · OpenCanary',rule:'Un intento de acceso al formulario señuelo'},
 {id:'canary-bd',name:'MySQL',icon:Database,color:'amber',desc:'Base de datos simulada · OpenCanary',rule:'Un intento de autenticación al señuelo'}
];
const eventName=t=>({'cowrie.session.connect':'Conexión SSH','cowrie.session.closed':'Sesión SSH cerrada','cowrie.login.success':'Autenticación aceptada','cowrie.login.failed':'Autenticación fallida','cowrie.command.input':'Comando registrado','opencanary.http.3000':'Solicitud web','opencanary.http.3001':'Intento de acceso web','opencanary.http.3003':'Redirección web','opencanary.mysql.9003':'Conexión MySQL','opencanary.mysql.8001':'Intento de acceso MySQL'})[t]||t||'Sin actividad';
const ruleName=t=>({'multiples_conexiones':'Múltiples conexiones SSH','autenticaciones_fallidas':'Autenticaciones fallidas','intento_acceso_web_local':'Intento de acceso web','intento_acceso_mysql_local':'Intento de acceso MySQL'})[t]||t||'Sin alertas';
const time=d=>d?new Date(d).toLocaleString('es-EC',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'Sin registros';

const ruleKeys={'cowrie-ssh':'multiples_conexiones','canary-web':'intento_acceso_web_local','canary-bd':'intento_acceso_mysql_local'};
const ruleLabels={multiples_conexiones:'Conexiones SSH',intento_acceso_web_local:'Intentos de acceso Web',intento_acceso_mysql_local:'Intentos de acceso MySQL'};
function AlertSettings({session,rules,onSaved}){
 const [message,setMessage]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function save(e){e.preventDefault();setBusy(true);setError('');setMessage('');const form=new FormData(e.currentTarget),payload={};for(const k of Object.keys(ruleLabels))payload[k]={umbral:Number(form.get(k+'_umbral')),ventana_segundos:Number(form.get(k+'_ventana'))};try{const r=await fetch('/api/alert-rules',{method:'POST',headers:{Authorization:`Bearer ${session.token}`,'Content-Type':'application/json'},body:JSON.stringify(payload)});const body=await r.json();if(!r.ok)throw Error(body.mensaje||'No se pudo guardar la configuración.');await onSaved();setMessage('Configuración guardada. Se aplicará a los próximos eventos.')}catch(err){setError(err.message)}finally{setBusy(false)}}
 if(!rules)return null;
 return <section id="configurar-alertas" className="card alert-settings"><div className="section-head"><div><span className="eyebrow">REGLAS DEL LABORATORIO</span><h2>Configurar alertas</h2><p>Elige cuántos intentos del mismo origen deben ocurrir dentro de cada ventana.</p></div></div>{session.rol==='admin'?<form onSubmit={save} key={JSON.stringify(rules)}><div className="alert-settings-grid">{Object.entries(ruleLabels).map(([k,label])=><article key={k}><strong>{label}</strong><label>Cantidad mínima<input type="number" name={k+'_umbral'} min="1" max="1000" required defaultValue={rules[k].umbral}/></label><label>Ventana en segundos<input type="number" name={k+'_ventana'} min="10" max="86400" required defaultValue={rules[k].ventana_segundos}/></label></article>)}</div><button className="button primary" disabled={busy}>{busy?'Guardando…':'Guardar reglas'}</button></form>:<p>Solo un administrador puede modificar estas reglas.</p>}{message&&<p className="success-message" role="status">{message}</p>}{error&&<p className="error-message" role="alert">{error}</p>}<p className="card-note">El detector cuenta eventos por señuelo y origen; los eventos existentes dentro de la ventana pueden contar. Tras una alerta, se evita repetir la misma regla y origen durante esa ventana. Web y MySQL cuentan intentos de autenticación, no visitas o conexiones sin inicio de sesión.</p></section>;
}

export default function MonitorExterno({data,live,liveAlert,onExplain,onDetail,onViewSensor,onDefense,Flow,Timeline,Tag,session}){
 const [rules,setRules]=useState(null),[rulesError,setRulesError]=useState('');
 async function loadRules(){const r=await fetch('/api/alert-rules',{headers:{Authorization:`Bearer ${session.token}`},cache:'no-store'});if(!r.ok)throw Error('No se pudieron cargar las reglas del laboratorio.');setRules(await r.json());setRulesError('')}
 useEffect(()=>{if(session.tenant_id==='lab')loadRules().catch(e=>setRulesError(e.message));},[session.token,session.tenant_id]);
 return <>
  <div className="page-heading monitor-heading"><div><span className="eyebrow">OBSERVA LO QUE SUCEDE FUERA DEL PANEL</span><h1>Tres señuelos. <span>Un monitoreo en vivo.</span></h1><p>Inicia los intentos en otra ventana de PowerShell o del navegador y observa aquí sus registros.</p></div><Tag tone="violet"><Radio size={14}/> Datos confirmados</Tag></div>
  {session.tenant_id!=='lab'&&<div className="notice"><AlertTriangle size={18}/><span>Los tres señuelos locales pertenecen al Laboratorio local. Este usuario ve únicamente los datos de su organización.</span></div>}
  {session.tenant_id==='lab'&&<p><a className="button" href="#configurar-alertas">Configurar alertas ↓</a></p>}
  <TracePanel data={data} session={session} live={live} liveAlert={liveAlert} onDetail={onDetail} onDefense={onDefense}/>
  <div className="monitor-sensors">{sensors.map(s=>{const info=data.overview.monitoreo.find(x=>x.sensor===s.id)||{},Icon=s.icon;return <article className={`monitor-sensor ${s.color} ${live?.tipo==='eventos'&&String(live.id)===String(info.evento_id)?'monitor-flash':''}`} key={s.id}>
   <div className="monitor-top"><span className="monitor-icon"><Icon size={24}/></span><span className="monitor-id">SEÑUELO / {s.name.toUpperCase()}</span><Radio size={16}/></div>
   <h2>{s.name}</h2><p>{s.desc}</p><div className="monitor-rule"><b>REGLA DE DETECCIÓN</b><span>{session.tenant_id==='lab'?(rules?`${rules[ruleKeys[s.id]].umbral} ${s.id==='cowrie-ssh'?'conexiones':'intentos'} por origen en ${rules[ruleKeys[s.id]].ventana_segundos} segundos`:'Consultando configuración…'):'Señuelo del laboratorio local'}</span></div>
   <div className="monitor-observation"><span>ÚLTIMO EVENTO <small>· historial</small></span><strong>{eventName(info.evento_tipo)}</strong><small>{time(info.evento_fecha)}{info.evento_origen?` · ${info.evento_origen}`:''}</small></div>
   <div className="monitor-alert"><span><AlertTriangle size={14}/> ÚLTIMA ALERTA · historial</span><strong>{ruleName(info.alerta_regla)}</strong><small>{info.alerta_id?`#${info.alerta_id} · ${time(info.fecha_alerta)}${info.alerta_simulado?' · dato simulado':''}`:'Aún no hay alertas registradas'}</small></div>
   <div className="monitor-actions"><button onClick={()=>onViewSensor(s.id,'events')}>Ver eventos <ArrowRight size={14}/></button><button onClick={()=>onViewSensor(s.id,'alerts')}>Ver alertas <ArrowRight size={14}/></button></div>
  </article>})}</div>
  {rulesError&&<p className="error-message" role="alert">{rulesError}</p>}
  {session.tenant_id==='lab'&&<AlertSettings session={session} rules={rules} onSaved={loadRules}/>}
  <Flow data={data} live={live} onExplain={onExplain}/>
  <div className="monitor-bottom"><section className="card"><div className="section-head"><div><span className="eyebrow">ACTIVIDAD CONFIRMADA</span><h2>El recorrido en tiempo real</h2></div><Activity size={19}/></div><Timeline rows={data.overview.recientes} limit={7} onDetail={onDetail}/><p className="card-note">Se muestran los eventos más recientes de tu organización. Haz clic en uno para ver el detalle.</p></section>
   <section className="card monitor-steps"><div className="section-head"><div><span className="eyebrow">ASÍ LO PRESENTAS</span><h2>Dos ventanas, un recorrido</h2></div></div><ol><li><b>Deja este panel abierto.</b><span>Selecciona Presentar y colócalo a un lado de la pantalla.</span></li><li><b>Abre PowerShell o el navegador.</b><span>Inicia cada prueba en esa otra ventana, usando únicamente el laboratorio local.</span></li><li><b>Observa el resultado aquí.</b><span>El evento llega primero; una alerta aparece al cumplirse la regla. No toda alerta provoca MTD.</span></li></ol><div className="notice">El panel muestra lo ocurrido. Los intentos se realizan desde fuera, sin envíos automáticos.</div></section></div>
 </>;
}
