-- Base para identificar agentes de cualquier organización registrada.
-- Las credenciales solo se guardan como huellas SHA-256; no habilita el ingreso todavía.
BEGIN;
CREATE TABLE IF NOT EXISTS agentes_credenciales (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 tenant_id text NOT NULL,
 agente_id bigint NOT NULL,
 token_hash bytea NOT NULL UNIQUE CHECK (octet_length(token_hash)=32),
 creada_en timestamptz NOT NULL DEFAULT now(),
 vence_en timestamptz,
 revocada_en timestamptz,
 CONSTRAINT credencial_agente_empresa_fk FOREIGN KEY (tenant_id,agente_id)
   REFERENCES agentes (tenant_id,id) ON DELETE CASCADE,
 CONSTRAINT credencial_vencimiento_valido CHECK (vence_en IS NULL OR vence_en>creada_en)
);
CREATE INDEX IF NOT EXISTS agentes_credenciales_agente_idx ON agentes_credenciales (tenant_id,agente_id);
REVOKE ALL ON agentes_credenciales FROM PUBLIC;
INSERT INTO versiones_esquema(version) VALUES ('024_identidad_agentes') ON CONFLICT DO NOTHING;
COMMIT;
