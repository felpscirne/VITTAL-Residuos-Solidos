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
    started_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMP,
    status        VARCHAR(20) NOT NULL DEFAULT 'running',
    source_file   VARCHAR(255),
    initiated_by  VARCHAR(255),
    files_count   INTEGER NOT NULL DEFAULT 0,
    rows_read     INTEGER NOT NULL DEFAULT 0,
    rows_valid    INTEGER NOT NULL DEFAULT 0,
    rows_new      INTEGER NOT NULL DEFAULT 0,
    rows_updated  INTEGER NOT NULL DEFAULT 0,
    deleted_rows  INTEGER NOT NULL DEFAULT 0,
    deleted_at    TIMESTAMP,
    deleted_by    VARCHAR(255),
    details       TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS pesagem (
    ticket                           INTEGER     PRIMARY KEY,
    data_hora                        TIMESTAMP   NOT NULL,
    id_produto                       INTEGER     NOT NULL REFERENCES produto(id_produto),
    id_transportadora                INTEGER              REFERENCES empresa(id_empresa),
    id_cliente                       INTEGER     NOT NULL REFERENCES empresa(id_empresa),
    id_veiculo                       INTEGER              REFERENCES veiculo(id_veiculo),
    id_setor                         INTEGER     NOT NULL REFERENCES setor(id_setor),
    peso_entrada                     REAL,
    peso_saida                       REAL,
    peso_liquido                     REAL,
    peso_embalagem_liquido           REAL,
    peso_embalagem_liquido_corrigido REAL,
    peso_nota_fiscal                 REAL,
    diferenca_peso                   REAL,
    diferenca_peso_porcentagem       REAL,
    nro_nota_fiscal                  VARCHAR(50),
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
    p.data_hora,
    pr.nome                              AS produto,
    t.nome                               AS transportadora,
    c.nome                               AS fornecedor_cliente,
    p.peso_entrada,
    p.peso_saida,
    p.peso_liquido,
    p.peso_embalagem_liquido,
    p.peso_embalagem_liquido_corrigido,
    p.peso_nota_fiscal,
    v.placa                              AS placa_veiculo,
    p.diferenca_peso,
    p.diferenca_peso_porcentagem,
    p.nro_nota_fiscal,
    s.codigo                             AS setor,
    NULL::TEXT                           AS destino_procedencia
FROM      pesagem  p
JOIN      produto  pr ON pr.id_produto  = p.id_produto
JOIN      empresa  c  ON c.id_empresa   = p.id_cliente
LEFT JOIN empresa  t  ON t.id_empresa   = p.id_transportadora
LEFT JOIN veiculo  v  ON v.id_veiculo   = p.id_veiculo
JOIN      setor    s  ON s.id_setor     = p.id_setor;
