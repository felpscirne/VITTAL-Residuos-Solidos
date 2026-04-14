from datetime import datetime
from uuid import uuid4

from flask_security.utils import hash_password
from sqlalchemy import text

from app.extensions import db

PAGES_TO_SEED = {
    "/": "Visao Geral (Dashboard)",
    "/estudo-ifescs": "Ambiente de Estudo IFEsCS",
    "/previsoes": "Previsoes com Prophet",
    "/analise-produtos": "Analise de Produtos",
    "/fluxo-de-caixa": "Fluxo de Caixa (Entrada vs Saida)",
    "/analise-setores": "Analise de Setores",
    "/analise-empresas": "Analise de Empresas",
    "/analise-horarios": "Analise de Horarios",
    "/analise-frotas": "Analise de Frota",
    "/registros": "Buscar Registros",
    "/auditoria-peso": "Auditoria de Peso",
    "/gerenciar-arquivos": "Gerenciar Arquivos (.ods)",
    "/gerenciar-permissoes": "Gerenciar Permissoes de Acesso",
    "/gerenciar-eventos": "Gerenciar Eventos",
    "/visualizar-eventos": "Quadro de Avisos e Eventos",
}

ROLES_TO_SEED = ["sem_login", "geral", "estudantil", "gestao", "superadmin"]

DEFAULT_PERMISSIONS = {
    "sem_login": ["/", "/estudo-ifescs", "/analise-produtos", "/fluxo-de-caixa", "/visualizar-eventos"],
    "geral": ["/", "/estudo-ifescs", "/analise-produtos", "/fluxo-de-caixa", "/visualizar-eventos"],
    "estudantil": [
        "/",
        "/estudo-ifescs",
        "/analise-produtos",
        "/fluxo-de-caixa",
        "/analise-setores",
        "/analise-empresas",
        "/analise-horarios",
        "/analise-frotas",
        "/registros",
        "/visualizar-eventos",
    ],
    "gestao": [
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
    "superadmin": list(PAGES_TO_SEED.keys()),
}

DEFAULT_ADMIN_USER = {
    "email": "admin@sistema.com",
    "name": "Super Administrador",
    "password": "senha123",
    "role": "superadmin",
}


def run_startup_migrations():
    db.create_all()

    with db.engine.begin() as conn:
        conn.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS role_id INTEGER'))
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE constraint_name = 'user_role_id_fkey'
                          AND table_name = 'user'
                    ) THEN
                        ALTER TABLE "user"
                        ADD CONSTRAINT user_role_id_fkey
                        FOREIGN KEY (role_id) REFERENCES role(id);
                    END IF;
                END $$;
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

    user_insert = text(
        """
        INSERT INTO "user" (name, email, password, active, confirmed_at, fs_uniquifier, role_id)
        VALUES (:name, :email, :password, :active, :confirmed_at, :fs_uniquifier, :role_id)
        ON CONFLICT (email) DO NOTHING
        RETURNING id
        """
    )

    user_select = text(
        """
        SELECT id
        FROM "user"
        WHERE email = :email
        """
    )

    user_role_update = text(
        """
        UPDATE "user"
        SET role_id = (
            SELECT r.id
            FROM role r
            WHERE r.name = :role_name
        )
        WHERE email = :email
        """
    )

    with db.session.begin():
        for role_name in ROLES_TO_SEED:
            db.session.execute(
                role_upsert,
                {"name": role_name, "description": f"Nivel: {role_name}"},
            )

        for route, description in PAGES_TO_SEED.items():
            db.session.execute(
                page_upsert,
                {"route": route, "description": description},
            )

        for role_name, routes in DEFAULT_PERMISSIONS.items():
            for route in routes:
                db.session.execute(
                    permission_upsert,
                    {"role_name": role_name, "route": route},
                )

        roles_users_exists = db.session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'roles_users'
                )
                """
            )
        ).scalar()

        if roles_users_exists:
            db.session.execute(
                text(
                    """
                    UPDATE "user" u
                    SET role_id = ru.role_id
                    FROM roles_users ru
                    WHERE u.id = ru.user_id
                      AND u.role_id IS NULL
                    """
                )
            )

        admin_password = hash_password(DEFAULT_ADMIN_USER["password"])
        admin_unique = str(uuid4())
        admin_role_id = db.session.execute(
            text("SELECT id FROM role WHERE name = :role_name"),
            {"role_name": DEFAULT_ADMIN_USER["role"]},
        ).scalar_one()
        inserted_admin = db.session.execute(
            user_insert,
            {
                "name": DEFAULT_ADMIN_USER["name"],
                "email": DEFAULT_ADMIN_USER["email"],
                "password": admin_password,
                "active": True,
                "confirmed_at": datetime.utcnow(),
                "fs_uniquifier": admin_unique,
                "role_id": admin_role_id,
            },
        ).scalar()

        if inserted_admin is None:
            admin_id = db.session.execute(
                user_select,
                {"email": DEFAULT_ADMIN_USER["email"]},
            ).scalar_one()
        else:
            admin_id = inserted_admin

        db.session.execute(
            user_role_update,
            {
                "email": DEFAULT_ADMIN_USER["email"],
                "role_name": DEFAULT_ADMIN_USER["role"],
            },
        )

    with db.engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS roles_users'))

    return {"roles": len(ROLES_TO_SEED), "pages": len(PAGES_TO_SEED), "admin_id": admin_id}
