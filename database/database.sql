DROP DATABASE IF EXISTS projeto;
CREATE DATABASE projeto
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'pt_BR.UTF-8'
    LC_CTYPE   = 'pt_BR.UTF-8'
    TEMPLATE   = template0;

\c projeto;

-- -----------------------------------------------------------------------------
-- Autenticação e autorização da plataforma
-- Roles representam os tipos de usuário da aplicação.
-- -----------------------------------------------------------------------------

CREATE TABLE role (
    id          SERIAL       PRIMARY KEY,
    name        VARCHAR(80)  NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE TABLE page (
    id          SERIAL        PRIMARY KEY,
    route       VARCHAR(255)  NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE TABLE "user" (
    id             SERIAL        PRIMARY KEY,
    name           VARCHAR(100),
    email          VARCHAR(120)  NOT NULL UNIQUE,
    password       VARCHAR(255)  NOT NULL,
    active         BOOLEAN,
    confirmed_at   TIMESTAMP,
    fs_uniquifier  VARCHAR(255)  NOT NULL UNIQUE
);

CREATE TABLE roles_users (
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE role_page_permission (
    role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    page_id INTEGER NOT NULL REFERENCES page(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, page_id)
);

INSERT INTO role (name, description)
VALUES
    ('sem_login', 'Nível: sem_login'),
    ('geral', 'Nível: geral'),
    ('estudantil', 'Nível: estudantil'),
    ('gestao', 'Nível: gestao'),
    ('superadmin', 'Nível: superadmin')
ON CONFLICT (name) DO UPDATE
SET description = EXCLUDED.description;

INSERT INTO page (route, description)
VALUES
    ('/', 'Visão Geral (Dashboard)'),
    ('/analise-produtos', 'Análise de Produtos'),
    ('/fluxo-de-caixa', 'Fluxo de Caixa (Entrada vs Saída)'),
    ('/analise-setores', 'Análise de Setores'),
    ('/analise-empresas', 'Análise de Empresas'),
    ('/analise-horarios', 'Análise de Horários'),
    ('/analise-frotas', 'Análise de Frota'),
    ('/registros', 'Buscar Registros'),
    ('/auditoria-peso', 'Auditoria de Peso'),
    ('/gerenciar-arquivos', 'Gerenciar Arquivos (.ods)'),
    ('/gerenciar-permissoes', 'Gerenciar Permissões de Acesso'),
    ('/gerenciar-eventos', 'Gerenciar Eventos'),
    ('/visualizar-eventos', 'Quadro de Avisos e Eventos')
ON CONFLICT (route) DO UPDATE
SET description = EXCLUDED.description;

INSERT INTO role_page_permission (role_id, page_id)
SELECT r.id, p.id
FROM (
    VALUES
        ('sem_login', '/'),
        ('sem_login', '/analise-produtos'),
        ('sem_login', '/fluxo-de-caixa'),
        ('sem_login', '/visualizar-eventos'),
        ('geral', '/'),
        ('geral', '/analise-produtos'),
        ('geral', '/fluxo-de-caixa'),
        ('geral', '/visualizar-eventos'),
        ('estudantil', '/'),
        ('estudantil', '/analise-produtos'),
        ('estudantil', '/fluxo-de-caixa'),
        ('estudantil', '/analise-setores'),
        ('estudantil', '/analise-empresas'),
        ('estudantil', '/analise-horarios'),
        ('estudantil', '/analise-frotas'),
        ('estudantil', '/registros'),
        ('estudantil', '/visualizar-eventos'),
        ('gestao', '/'),
        ('gestao', '/analise-produtos'),
        ('gestao', '/fluxo-de-caixa'),
        ('gestao', '/analise-setores'),
        ('gestao', '/analise-empresas'),
        ('gestao', '/analise-horarios'),
        ('gestao', '/analise-frotas'),
        ('gestao', '/registros'),
        ('gestao', '/auditoria-peso'),
        ('gestao', '/gerenciar-arquivos'),
        ('gestao', '/gerenciar-permissoes'),
        ('gestao', '/gerenciar-eventos'),
        ('gestao', '/visualizar-eventos'),
        ('superadmin', '/'),
        ('superadmin', '/analise-produtos'),
        ('superadmin', '/fluxo-de-caixa'),
        ('superadmin', '/analise-setores'),
        ('superadmin', '/analise-empresas'),
        ('superadmin', '/analise-horarios'),
        ('superadmin', '/analise-frotas'),
        ('superadmin', '/registros'),
        ('superadmin', '/auditoria-peso'),
        ('superadmin', '/gerenciar-arquivos'),
        ('superadmin', '/gerenciar-permissoes'),
        ('superadmin', '/gerenciar-eventos'),
        ('superadmin', '/visualizar-eventos')
) AS perms(role_name, route)
JOIN role r ON r.name = perms.role_name
JOIN page p ON p.route = perms.route
ON CONFLICT DO NOTHING;

CREATE TABLE produto (
    id_produto  SERIAL       PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL UNIQUE,
    descricao   TEXT
);

CREATE TABLE empresa (
    id_empresa  SERIAL       PRIMARY KEY,
    nome        VARCHAR(150) NOT NULL UNIQUE,
    papel       VARCHAR(20)  NOT NULL
                    CHECK (papel IN ('cliente','transportadora','ambos','interno'))
);

CREATE TABLE veiculo (
    id_veiculo  SERIAL      PRIMARY KEY,
    placa       VARCHAR(20)  NOT NULL UNIQUE,
    id_empresa  INTEGER      REFERENCES empresa(id_empresa) ON DELETE SET NULL
);

CREATE TABLE setor (
    id_setor  SERIAL      PRIMARY KEY,
    codigo    VARCHAR(30)  NOT NULL UNIQUE,
    nome      VARCHAR(100),
    tipo      VARCHAR(20)  NOT NULL
                CHECK (tipo IN ('coleta','destino','ajuste','interno'))
);

CREATE TABLE pesagem (
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
    nro_nota_fiscal                  VARCHAR(50)
);

CREATE INDEX idx_pesagem_data_hora  ON pesagem (data_hora);
CREATE INDEX idx_pesagem_id_setor   ON pesagem (id_setor);
CREATE INDEX idx_pesagem_id_cliente ON pesagem (id_cliente);
CREATE INDEX idx_pesagem_id_produto ON pesagem (id_produto);
CREATE INDEX idx_pesagem_id_veiculo ON pesagem (id_veiculo);

CREATE TABLE event (
    id               SERIAL       PRIMARY KEY,
    title            VARCHAR(100) NOT NULL,
    description      TEXT,
    event_type       VARCHAR(50),
    start_date       TIMESTAMP    NOT NULL,
    end_date         TIMESTAMP    NOT NULL,
    affected_sectors VARCHAR(255),
    created_at       TIMESTAMP    DEFAULT NOW()
);

CREATE VIEW registro AS
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