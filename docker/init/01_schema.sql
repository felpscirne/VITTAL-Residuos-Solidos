CREATE TABLE IF NOT EXISTS produto (
    id_produto  SERIAL       PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL UNIQUE,
    descricao   TEXT
);

CREATE TABLE IF NOT EXISTS empresa (
    id_empresa  SERIAL       PRIMARY KEY,
    nome        VARCHAR(150) NOT NULL UNIQUE,
    papel       VARCHAR(20)  NOT NULL
                    CHECK (papel IN ('cliente','transportadora','ambos','interno'))
);

CREATE TABLE IF NOT EXISTS veiculo (
    id_veiculo  SERIAL       PRIMARY KEY,
    placa       VARCHAR(20)  NOT NULL UNIQUE,
    id_empresa  INTEGER      REFERENCES empresa(id_empresa) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS setor (
    id_setor  SERIAL      PRIMARY KEY,
    codigo    VARCHAR(30)  NOT NULL UNIQUE,
    nome      VARCHAR(100),
    tipo      VARCHAR(20)  NOT NULL
                CHECK (tipo IN ('coleta','destino','ajuste','interno'))
);

CREATE TABLE IF NOT EXISTS import_auditoria (
    id            SERIAL PRIMARY KEY,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMPTZ,
    status        VARCHAR(20) NOT NULL DEFAULT 'running',
    source_file   VARCHAR(255),
    initiated_by  VARCHAR(255),
    files_count   INTEGER NOT NULL DEFAULT 0,
    rows_read     INTEGER NOT NULL DEFAULT 0,
    rows_valid    INTEGER NOT NULL DEFAULT 0,
    rows_new      INTEGER NOT NULL DEFAULT 0,
    rows_updated  INTEGER NOT NULL DEFAULT 0,
    deleted_rows  INTEGER NOT NULL DEFAULT 0,
    deleted_at    TIMESTAMPTZ,
    deleted_by    VARCHAR(255),
    details       TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS pesagem (
    ticket                           INTEGER     PRIMARY KEY,
    data_hora                        TIMESTAMPTZ NOT NULL,
    id_produto                       INTEGER     NOT NULL REFERENCES produto(id_produto),
    id_transportadora                INTEGER              REFERENCES empresa(id_empresa),
    id_cliente                       INTEGER     NOT NULL REFERENCES empresa(id_empresa),
    id_veiculo                       INTEGER              REFERENCES veiculo(id_veiculo),
    id_setor                         INTEGER     NOT NULL REFERENCES setor(id_setor),
    peso_entrada                     NUMERIC(18,3),
    peso_saida                       NUMERIC(18,3),
    peso_liquido                     NUMERIC(18,3),
    peso_embalagem_liquido           NUMERIC(18,3),
    peso_embalagem_liquido_corrigido NUMERIC(18,3),
    peso_nota_fiscal                 NUMERIC(18,3),
    diferenca_peso                   NUMERIC(18,3),
    diferenca_peso_porcentagem       NUMERIC(12,4),
    nro_nota_fiscal                  VARCHAR(50),
    tipo_de_residuo                  TEXT,
    import_audit_id                  INTEGER REFERENCES import_auditoria(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pesagem_data_hora  ON pesagem (data_hora);
CREATE INDEX IF NOT EXISTS idx_pesagem_id_setor   ON pesagem (id_setor);
CREATE INDEX IF NOT EXISTS idx_pesagem_id_cliente ON pesagem (id_cliente);
CREATE INDEX IF NOT EXISTS idx_pesagem_id_produto ON pesagem (id_produto);
CREATE INDEX IF NOT EXISTS idx_pesagem_id_veiculo ON pesagem (id_veiculo);
CREATE INDEX IF NOT EXISTS idx_pesagem_import_audit_id ON pesagem (import_audit_id);
CREATE INDEX IF NOT EXISTS idx_import_auditoria_started_at ON import_auditoria (started_at);
CREATE INDEX IF NOT EXISTS idx_import_auditoria_status ON import_auditoria (status);

CREATE OR REPLACE VIEW registro AS
SELECT
    p.ticket,
    v.placa                              AS placa,
    (p.data_hora AT TIME ZONE 'America/Sao_Paulo') AS data_hora,
    pr.nome                              AS produto,
    t.nome                               AS transportadora,
    c.nome                               AS fornecedor_cliente,
    p.peso_entrada::DOUBLE PRECISION,
    p.peso_saida::DOUBLE PRECISION,
    p.peso_liquido::DOUBLE PRECISION,
    p.peso_embalagem_liquido::DOUBLE PRECISION,
    p.peso_embalagem_liquido_corrigido::DOUBLE PRECISION,
    p.peso_nota_fiscal::DOUBLE PRECISION,
    v.placa                              AS placa_veiculo,
    p.diferenca_peso::DOUBLE PRECISION,
    p.diferenca_peso_porcentagem::DOUBLE PRECISION,
    p.nro_nota_fiscal,
    p.tipo_de_residuo,
    s.codigo                             AS setor,
    NULL::TEXT                           AS destino_procedencia
FROM      pesagem  p
JOIN      produto  pr ON pr.id_produto  = p.id_produto
JOIN      empresa  c  ON c.id_empresa   = p.id_cliente
LEFT JOIN empresa  t  ON t.id_empresa   = p.id_transportadora
LEFT JOIN veiculo  v  ON v.id_veiculo   = p.id_veiculo
JOIN      setor    s  ON s.id_setor     = p.id_setor;
