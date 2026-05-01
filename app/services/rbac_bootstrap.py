import os

from sqlalchemy import text

from app.extensions import db

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")

PAGES_TO_SEED = {
    "/": "Visão Geral do Painel",
    "/estudo-ifescs": "Ambiente de Estudo IFEsCS",
    "/previsoes": "Previsões com Prophet",
    "/analise-produtos": "Análise de Produtos",
    "/fluxo-de-caixa": "Fluxo de Caixa (Entrada vs Saída)",
    "/analise-setores": "Análise de Setores",
    "/analise-empresas": "Análise de Empresas",
    "/analise-horarios": "Análise de Horários",
    "/analise-frotas": "Analise de Frota",
    "/registros": "Buscar Registros",
    "/auditoria-peso": "Auditoria de Peso",
    "/gerenciar-arquivos": "Gerenciar Arquivos (.ods)",
    "/gerenciar-permissoes": "Gerenciar Permissões de Acesso",
    "/gerenciar-eventos": "Gerenciar Eventos",
    "/visualizar-eventos": "Quadro de Avisos e Eventos",
}

ROLE_DESCRIPTIONS = {
    "anonymous": "Sem login",
    "student": "Estudantil",
    "operator": "Operador",
    "management": "Gestão",
}

ROLES_TO_SEED = ["anonymous", "student", "operator", "management"]

DEFAULT_PERMISSIONS = {
    "anonymous": ["/", "/estudo-ifescs", "/visualizar-eventos"],
    "student": ["/", "/estudo-ifescs", "/registros", "/visualizar-eventos"],
    "operator": [
        "/",
        "/estudo-ifescs",
        "/analise-produtos",
        "/fluxo-de-caixa",
        "/analise-setores",
        "/analise-empresas",
        "/analise-horarios",
        "/analise-frotas",
        "/registros",
        "/gerenciar-arquivos",
        "/visualizar-eventos",
    ],
    "management": [
        "/",
        "/estudo-ifescs",
        "/previsoes",
        "/analise-produtos",
        "/fluxo-de-caixa",
        "/analise-setores",
        "/analise-empresas",
        "/analise-horarios",
        "/analise-frotas",
        "/registros",
        "/auditoria-peso",
        "/gerenciar-arquivos",
        "/gerenciar-permissoes",
        "/gerenciar-eventos",
        "/visualizar-eventos",
    ],
}

def _ensure_import_auditoria_table(conn):
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS import_auditoria (
                id SERIAL PRIMARY KEY,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMPTZ,
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                source_file VARCHAR(255),
                initiated_by VARCHAR(255),
                files_count INTEGER NOT NULL DEFAULT 0,
                rows_read INTEGER NOT NULL DEFAULT 0,
                rows_valid INTEGER NOT NULL DEFAULT 0,
                rows_new INTEGER NOT NULL DEFAULT 0,
                rows_updated INTEGER NOT NULL DEFAULT 0,
                deleted_rows INTEGER NOT NULL DEFAULT 0,
                deleted_at TIMESTAMPTZ,
                deleted_by VARCHAR(255),
                details TEXT,
                error_message TEXT
            )
            """
        )
    )

    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'running'"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS source_file VARCHAR(255)"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS initiated_by VARCHAR(255)"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS files_count INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_read INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_valid INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_new INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_updated INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS deleted_rows INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(255)"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS details TEXT"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS error_message TEXT"))


def _drop_registro_view(conn):
    conn.execute(text("DROP VIEW IF EXISTS registro"))


def _recreate_registro_view(conn):
    conn.execute(
        text(
            f"""
            CREATE OR REPLACE VIEW registro AS
            SELECT
                p.ticket,
                v.placa AS placa,
                (p.data_hora AT TIME ZONE '{APP_TIMEZONE}') AS data_hora,
                pr.nome AS produto,
                t.nome AS transportadora,
                c.nome AS fornecedor_cliente,
                p.peso_entrada::DOUBLE PRECISION AS peso_entrada,
                p.peso_saida::DOUBLE PRECISION AS peso_saida,
                p.peso_liquido::DOUBLE PRECISION AS peso_liquido,
                p.peso_embalagem_liquido::DOUBLE PRECISION AS peso_embalagem_liquido,
                p.peso_embalagem_liquido_corrigido::DOUBLE PRECISION AS peso_embalagem_liquido_corrigido,
                p.peso_nota_fiscal::DOUBLE PRECISION AS peso_nota_fiscal,
                v.placa AS placa_veiculo,
                p.diferenca_peso::DOUBLE PRECISION AS diferenca_peso,
                p.diferenca_peso_porcentagem::DOUBLE PRECISION AS diferenca_peso_porcentagem,
                p.nro_nota_fiscal,
                p.tipo_de_residuo,
                s.codigo AS setor,
                NULL::TEXT AS destino_procedencia
            FROM pesagem p
            JOIN produto pr ON pr.id_produto = p.id_produto
            JOIN empresa c ON c.id_empresa = p.id_cliente
            LEFT JOIN empresa t ON t.id_empresa = p.id_transportadora
            LEFT JOIN veiculo v ON v.id_veiculo = p.id_veiculo
            JOIN setor s ON s.id_setor = p.id_setor
            """
        )
    )


def _ensure_database_business_standards(conn):
    _ensure_import_auditoria_table(conn)

    _drop_registro_view(conn)
    conn.execute(text("ALTER TABLE pesagem ADD COLUMN IF NOT EXISTS import_audit_id INTEGER"))
    conn.execute(text("ALTER TABLE pesagem ADD COLUMN IF NOT EXISTS tipo_de_residuo TEXT"))
    conn.execute(
        text(
            """
            UPDATE pesagem p
            SET tipo_de_residuo = pr.nome
            FROM produto pr
            WHERE pr.id_produto = p.id_produto
              AND COALESCE(BTRIM(p.tipo_de_residuo), '') <> COALESCE(BTRIM(pr.nome), '')
            """
        )
    )
    conn.execute(text("UPDATE event SET created_at = COALESCE(created_at, start_date, end_date, NOW()) WHERE created_at IS NULL"))
    conn.execute(text("ALTER TABLE event ALTER COLUMN created_at SET DEFAULT NOW()"))
    conn.execute(text("ALTER TABLE event ALTER COLUMN created_at SET NOT NULL"))
    conn.execute(
        text(
            """
            UPDATE pesagem p
            SET import_audit_id = NULL
            WHERE import_audit_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM import_auditoria ia
                  WHERE ia.id = p.import_audit_id
              )
            """
        )
    )
    _recreate_registro_view(conn)

    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_event_start_date ON event (start_date)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_event_end_date ON event (end_date)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pesagem_import_audit_id ON pesagem (import_audit_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_import_auditoria_started_at ON import_auditoria (started_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_import_auditoria_status ON import_auditoria (status)"))

    conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'event_date_order_check'
                ) THEN
                    ALTER TABLE event
                    ADD CONSTRAINT event_date_order_check
                    CHECK (start_date <= end_date);
                END IF;
            END
            $$;
            """
        )
    )

    conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'pesagem_import_audit_id_fkey'
                ) THEN
                    ALTER TABLE pesagem
                    ADD CONSTRAINT pesagem_import_audit_id_fkey
                    FOREIGN KEY (import_audit_id)
                    REFERENCES import_auditoria(id)
                    ON DELETE SET NULL;
                END IF;
            END
            $$;
            """
        )
    )


def run_startup_migrations():
    db.create_all()

    with db.engine.begin() as conn:
        _ensure_database_business_standards(conn)
        conn.execute(
            text(
                """
                ALTER TABLE event
                ALTER COLUMN affected_sectors TYPE TEXT
                """
            )
        )

    role_upsert = text(
        """
        INSERT INTO role (name, description)
        VALUES (:name, :description)
        ON CONFLICT (name) DO UPDATE
        SET description = EXCLUDED.description
        """
    )

    page_upsert = text(
        """
        INSERT INTO page (route, description)
        VALUES (:route, :description)
        ON CONFLICT (route) DO UPDATE
        SET description = EXCLUDED.description
        """
    )

    permission_upsert = text(
        """
        INSERT INTO role_page_permission (role_id, page_id)
        SELECT r.id, p.id
        FROM role r
        JOIN page p ON r.name = :role_name AND p.route = :route
        ON CONFLICT DO NOTHING
        """
    )

    role_permission_count = text(
        """
        SELECT COUNT(*)
        FROM role_page_permission rp
        JOIN role r ON r.id = rp.role_id
        WHERE r.name = :role_name
        """
    )

    with db.session.begin():
        for role_name in ROLES_TO_SEED:
            db.session.execute(
                role_upsert,
                {"name": role_name, "description": ROLE_DESCRIPTIONS[role_name]},
            )

        for route, description in PAGES_TO_SEED.items():
            db.session.execute(
                page_upsert,
                {"route": route, "description": description},
            )

        for role_name, routes in DEFAULT_PERMISSIONS.items():
            existing_permissions = db.session.execute(
                role_permission_count,
                {"role_name": role_name},
            ).scalar_one()
            if existing_permissions:
                continue

            for route in routes:
                db.session.execute(
                    permission_upsert,
                    {"role_name": role_name, "route": route},
                )

    return {"roles": len(ROLES_TO_SEED), "pages": len(PAGES_TO_SEED)}
