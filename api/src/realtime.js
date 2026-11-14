// EMITIR SOLO METADATOS DE ALERTAS YA CONFIRMADAS EN POSTGRESQL.
import { Server } from 'socket.io';

const ORIGENES = new Set(['http://127.0.0.1:8081', 'http://localhost:8081']);

export function createRealtime(server, repository, verifyToken) {
  let escuchaDisponible = false;
  const io = new Server(server, {
    transports: ['websocket'],
    cors: { origin: [...ORIGENES], methods: ['GET'] },
    allowRequest: (request, callback) => callback(null, ORIGENES.has(request.headers.origin)),
  });
  io.use(async (socket,next)=>{
    try {const user=await verifyToken(socket.handshake.auth?.token || '');
      if(!user||!user.tenant_id) return next(new Error('NO_AUTENTICADO'));
      socket.data.user=user; next();
    } catch {next(new Error('NO_AUTENTICADO'));}
  });
  io.on('connection', socket => {
    socket.join(`tenant:${socket.data.user.tenant_id}`);
    socket.join(`sesion:${socket.data.user.sessionHash}`);
    const timer=setTimeout(()=>socket.disconnect(true),Math.max(0,socket.data.user.exp*1000-Date.now()));
    socket.on('disconnect',()=>clearTimeout(timer));
    socket.emit('canal:estado', { disponible: escuchaDisponible });
  });
  return {
    io,
    publishChange(payload) {
      let change;try{change=JSON.parse(payload);}catch{return false;}
      if(!['eventos','alertas','mtd_acciones','mtd_decisiones','ordenes_remotas'].includes(change.tipo)||
        typeof change.tenant!=='string'||!/^[a-z0-9_]{1,80}$/.test(change.tenant)||typeof change.id!=='string')return false;
      io.to(`tenant:${change.tenant}`).emit('actividad:cambio',{tipo:change.tipo,id:change.id});
      return true;
    },
    async publishAlert(id) {
      if (typeof id !== 'string' || !/^[1-9]\d{0,18}$/.test(id)) return false;
      const alerta = await repository.alertById(id);
      if (!alerta) return false;
      io.to(`tenant:${alerta.tenant_id}`).emit('alerta:nueva', {
        id: alerta.id, regla: alerta.regla, severidad: alerta.severidad,
        fecha_alerta: alerta.fecha_alerta, simulado: alerta.simulado, sensor: alerta.sensor,
      });
      return true;
    },
    resync() { io.emit('sincronizar'); },
    listenerStatus(disponible) {
      escuchaDisponible = disponible;
      io.emit('canal:estado', { disponible });
    },
    disconnectSession(hash) { io.in(`sesion:${hash}`).disconnectSockets(true); },
  };
}
