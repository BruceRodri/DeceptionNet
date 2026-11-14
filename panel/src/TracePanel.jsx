import React,{useEffect,useRef,useState} from 'react';
import {Activity,ArrowRight,Bell,CheckCircle2,Clock3,Globe2,Network,Radio,ShieldCheck,TerminalSquare} from 'lucide-react';

const sensorNames={'cowrie-ssh':'SSH · Cowrie','canary-web':'Web · OpenCanary','canary-bd':'MySQL · OpenCanary','sensor-remoto-a':'Señuelo remoto A','sensor-remoto-b':'Señuelo remoto B'};
const eventNames={'cowrie.session.connect':'Conexión SSH','cowrie.session.closed':'Sesión SSH cerrada','cowrie.login.failed':'Autenticación fallida','cowrie.login.success':'Autenticación aceptada','cowrie.command.input':'Comando registrado','opencanary.http.3000':'Solicitud web','opencanary.http.3001':'Intento de acceso web','opencanary.http.3003':'Redirección web','opencanary.mysql.9003':'Conexión MySQL','opencanary.mysql.8001':'Intento de acceso MySQL','honeypot.http.request':'Solicitud web remota'};
const ruleNames={'multiples_conexiones':'Múltiples conexiones SSH','autenticaciones_fallidas':'Autenticaciones fallidas','intento_acceso_web_local':'Intento de acceso web','intento_acceso_mysql_local':'Intento de acceso MySQL','multiples_conexiones_web':'Múltiples solicitudes web'};
const time=d=>d?new Date(d).toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';
const API=import.meta.env.VITE_API_BASE||'';
const decisionName=x=>({'sin_accion':'Sin cambio solicitado','cooldown':'En periodo de espera','solicitada':'Cambio solicitado'})[x]||x;

function responseFor(alert,actions,decisions){
 if(!alert)return {label:'Sin respuesta vinculada',detail:'La respuesta aparece cuando existe una decisión para una alerta.',tone:'muted'};
 const decision=decisions.find(d=>String(d.alerta_id)===String(alert.id));
 const action=actions.find(a=>String(a.alerta_id)===String(alert.id))||actions.find(a=>decision?.accion_id&&String(a.id)===String(decision.accion_id));
 if(action){
  if(action.estado==='aplicada')return {label:'Cambio MTD aplicado',detail:`Gateway :${action.puerto_anterior||'—'} → :${action.puerto_destino}. ${action.puerto_anterior&&action.puerto_anterior!==action.puerto_destino?'El puerto anterior se desactiva en el gateway.':'Consulta el historial para más detalles.'}`,tone:'success'};
  if(action.estado==='fallida'||action.estado==='revertida')return {label:action.estado==='revertida'?'Cambio revertido':'Cambio fallido',detail:'Consulta el historial MTD para revisar el resultado.',tone:'danger'};
  return {label:'Cambio en proceso',detail:`Estado registrado: ${action.estado}. Aún no se confirma el cambio.`,tone:'pending'};
 }
 if(decision)return {label:decisionName(decision.resultado),detail:decision.motivo==='SENSOR NO HABILITADO'?'La política MTD automática solo actúa sobre el gateway SSH.':decision.motivo==='VERIFICACION INTERNA DEL GATEWAY'?'El origen corresponde a una comprobación del gateway.':decision.motivo||'Consulta el historial de decisiones.',tone:decision.resultado==='sin_accion'?'muted':'pending'};
 return {label:'Sin decisión visible',detail:'No hay una decisión para esta alerta en el historial consultado.',tone:'muted'};
}

export default function TracePanel({data,session,live,liveAlert,onDetail,onDefense}){
 const [choice,setChoice]=useState('event'),[linkedEvent,setLinkedEvent]=useState(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const alertTime=useRef(0);
 const alerts=data.latestAlerts.data;
 useEffect(()=>{if(liveAlert?.id){alertTime.current=Date.now();setChoice(`alert:${liveAlert.id}`)}},[liveAlert?.id]);
 useEffect(()=>{if(live?.tipo==='eventos'&&Date.now()-alertTime.current>3500)setChoice('event')},[live?.id,live?.tipo]);
 const alertId=choice.startsWith('alert:')?choice.slice(6):null;
 const latestInteraction=data.overview.recientes.find(e=>e.tipo!=='cowrie.session.closed')||data.overview.recientes[0];
 const alert=alertId?alerts.find(a=>String(a.id)===alertId):alerts.find(a=>String(a.evento_id)===String(latestInteraction?.id));
 useEffect(()=>{
  if(!alertId||!alert?.evento_id){setLinkedEvent(null);setLoading(false);return;}
  const controller=new AbortController();setLinkedEvent(null);setError('');setLoading(true);
  fetch(`${API}/api/events/${alert.evento_id}`,{signal:controller.signal,headers:{Authorization:`Bearer ${session.token}`},cache:'no-store'})
   .then(r=>{if(!r.ok)throw Error('No se pudo consultar el evento relacionado.');return r.json()})
   .then(e=>{setLinkedEvent(e);setLoading(false)})
   .catch(e=>{if(e.name!=='AbortError'){setError(e.message);setLoading(false)}});
  return()=>controller.abort();
 },[alertId,alert?.evento_id,session.token]);
 const event=alertId?linkedEvent:latestInteraction;
 const response=responseFor(alert,data.mtd.acciones,data.mtd.decisiones);
 const waiting=alertId&&!alert;
 const stages=[
  {icon:Globe2,title:'1 · Origen',label:event?.ip_origen||'Esperando actividad',detail:event?'IP observada por el señuelo':'Haz una prueba desde otra ventana.',tone:'blue'},
  {icon:Radio,title:'2 · Señuelo',label:event?(sensorNames[event.sensor]||event.sensor):'Sin evento',detail:event?`${eventNames[event.tipo]||event.tipo}${event.comando?`: ${event.comando}`:''}`:'El sensor registrará la interacción.',tone:'cyan'},
  {icon:Network,title:'3 · Análisis',label:event?'Evento guardado':'En espera',detail:event?`Evento #${event.id} · ${time(event.fecha_recepcion)}`:'Aún no hay un evento seleccionado.',tone:'violet'},
  {icon:Bell,title:'4 · Alerta',label:alert?(ruleNames[alert.regla]||alert.regla):'Sin alerta vinculada',detail:alert?`#${alert.id} · ${time(alert.fecha_alerta)}${alert.simulado?' · Simulada':''}`:'El evento puede no alcanzar una regla.',tone:alert?'amber':'muted'},
  {icon:ShieldCheck,title:'5 · Respuesta',label:response.label,detail:response.detail,tone:response.tone}
 ];
 return <section className="trace-card" aria-labelledby="trace-title"><div className="trace-head"><div><span className="eyebrow">SIGUE UNA INTERACCIÓN REAL</span><h2 id="trace-title">Del primer contacto a la respuesta</h2><p>Selecciona un evento o una alerta guardada para ver su recorrido.</p></div><label className="trace-select"><span>Registro seleccionado</span><select value={choice} onChange={e=>setChoice(e.target.value)}><option value="event">Última interacción recibida</option>{alerts.map(a=><option key={a.id} value={`alert:${a.id}`}>Alerta #{a.id} · {ruleNames[a.regla]||a.regla}</option>)}</select></label></div>
 {(waiting||loading)&&<p className="trace-info"><Clock3 size={15}/> Consultando el evento y la alerta confirmados…</p>}{error&&<p className="trace-error" role="alert">{error}</p>}
 <div className="trace-stages">{stages.map((s,i)=>{const Icon=s.icon;return <React.Fragment key={s.title}><article className={`trace-stage ${s.tone}`}><span className="trace-icon"><Icon size={21}/></span><span className="trace-stage-title">{s.title}</span><strong>{s.label}</strong><small>{s.detail}</small></article>{i<stages.length-1&&<span className="trace-arrow"><ArrowRight size={17}/></span>}</React.Fragment>})}</div>
 <div className="trace-footer"><span><Activity size={15}/> {event?.simulado?'Dato simulado':event?'Registro del sensor':'Esperando registros'} · El origen puede ser la IP de un proxy.</span><div>{event&&<button onClick={()=>onDetail({item:event,kind:'event'})}>Ver evento <ArrowRight size={14}/></button>}{alert&&<button onClick={()=>onDetail({item:alert,kind:'alert'})}>Ver alerta <ArrowRight size={14}/></button>}<button onClick={onDefense}>Ver MTD <ArrowRight size={14}/></button></div></div>
 <p className="trace-limit"><CheckCircle2 size={15}/> MTD cambia el puerto del gateway SSH; el sistema no confirma un bloqueo general de la IP y el puerto directo 2222 sigue disponible.</p>
 </section>;
}
