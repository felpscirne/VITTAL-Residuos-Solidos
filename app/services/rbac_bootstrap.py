import os
from datetime import datetime
from uuid import uuid4

from flask_security.utils import hash_password
from sqlalchemy import text

from app.extensions import db

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
    "superadmin": "Superadministrador",
}

ROLES_TO_SEED = ["anonymous", "student", "operator", "management", "superadmin"]

DEFAULT_PERMISSIONS = {
    "anonymous": ["/", "/estudo-ifescs", "/analise-produtos", "/fluxo-de-caixa", "/visualizar-eventos"],
    "student": [
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
    "operator": [
        "/",
        "/estudo-ifescs",
        "/analise-produtos",
        "/fluxo-de-caixa",
        "/visualizar-eventos",
        "/gerenciar-arquivos",
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
    "superadmin": list(PAGES_TO_SEED.keys()),
}

DEFAULT_ADMIN_USER = {
    "email": os.getenv("SUPERADMIN_EMAIL", "admin@sistema.com").strip(),
    "name": os.getenv("SUPERADMIN_NAME", "Super Administrador").strip(),
    "password": os.getenv("SUPERADMIN_PASSWORD", "admin123"),
    "role": "superadmin",
}


def run_startup_migrations():
    db.create_all()

    with db.engine.begin() as conn:
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

    user_admin_sync = text(
        """
        UPDATE "user"
        SET
            name = :name,
            password = :password,
            active = :active,
            confirmed_at = COALESCE(confirmed_at, :confirmed_at),
            role_id = :role_id
        WHERE email = :email
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
        db.session.execute(
            user_admin_sync,
            {
                "name": DEFAULT_ADMIN_USER["name"],
                "email": DEFAULT_ADMIN_USER["email"],
                "password": admin_password,
                "active": True,
                "confirmed_at": datetime.utcnow(),
                "role_id": admin_role_id,
            },
        )

    return {"roles": len(ROLES_TO_SEED), "pages": len(PAGES_TO_SEED), "admin_id": admin_id}
