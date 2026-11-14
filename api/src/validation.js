// VALIDAR FILTROS Y EVITAR CONSULTAS SIN LIMITE.
export function parseFilters(query) {
  const allowed = new Set(['page', 'limit', 'sensor', 'simulado']);
  for (const key of Object.keys(query)) if (!allowed.has(key)) throw new Error(`Parámetro no permitido: ${key}`);
  const number = (value, fallback, max) => {
    if (value === undefined) return fallback;
    if (typeof value !== 'string' || !/^[1-9]\d*$/.test(value)) throw new Error('La página y el límite deben ser enteros positivos');
    const n = Number(value); if (!Number.isSafeInteger(n) || n > max) throw new Error('Página o límite fuera de rango'); return n;
  };
  const page = number(query.page, 1, 100000); const limit = number(query.limit, 20, 100);
  if (query.sensor !== undefined && (typeof query.sensor !== 'string' || !/^[a-zA-Z0-9_-]{1,80}$/.test(query.sensor))) throw new Error('Sensor inválido');
  if (query.simulado !== undefined && !['true', 'false'].includes(query.simulado)) throw new Error('simulado debe ser true o false');
  return { page, limit, sensor: query.sensor, simulated: query.simulado === undefined ? undefined : query.simulado === 'true' };
}
