-- ASOCIAR LOS AGENTES Y SENSORES REALES DE LAS EMPRESAS SIMULADAS.
BEGIN;
INSERT INTO agentes(tenant_id,nombre,simulado) VALUES ('empresa_a','agente-remoto-a',true),('empresa_b','agente-remoto-b',true) ON CONFLICT(tenant_id,nombre) DO NOTHING;
INSERT INTO sensores_registro(tenant_id,nombre,agente_id,simulado)
SELECT tenant_id,CASE tenant_id WHEN 'empresa_a' THEN 'sensor-remoto-a' ELSE 'sensor-remoto-b' END,id,true FROM agentes
WHERE (tenant_id='empresa_a' AND nombre='agente-remoto-a') OR (tenant_id='empresa_b' AND nombre='agente-remoto-b') ON CONFLICT(tenant_id,nombre) DO NOTHING;
INSERT INTO versiones_esquema(version) VALUES ('017_agentes') ON CONFLICT DO NOTHING;
COMMIT;
