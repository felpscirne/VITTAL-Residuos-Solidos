from datetime import datetime
from uuid import uuid4

from flask_security.utils import hash_password
from sqlalchemy import text

from app.extensions import db

PAGES_TO_SEED = {
    '/': 'Visão Geral (Dashboard)',
    '/analise-produtos': 'Análise de Produtos',
    '/fluxo-de-caixa': 'Fluxo de Caixa (Entrada vs Saída)',
    '/analise-setores': 'Análise de Setores',
    '/analise-empresas': 'Análise de Empresas',
    '/analise-horarios': 'Análise de Horários',
    '/analise-frotas': 'Análise de Frota',
    '/registros': 'Buscar Registros',
    '/auditoria-peso': 'Auditoria de Peso',
    '/gerenciar-arquivos': 'Gerenciar Arquivos (.ods)',
    '/gerenciar-permissoes': 'Gerenciar Permissões de Acesso',
    '/gerenciar-eventos': 'Gerenciar Eventos',
    '/visualizar-eventos': 'Quadro de Avisos e Eventos',
}

ROLES_TO_SEED = ['sem_login', 'geral', 'estudantil', 'gestao', 'superadmin']

DEFAULT_PERMISSIONS = {
    'sem_login': ['/', '/analise-produtos', '/fluxo-de-caixa', '/visualizar-eventos'],
    'geral': ['/', '/analise-produtos', '/fluxo-de-caixa', '/visualizar-eventos'],
    'estudantil': [
        '/', '/analise-produtos', '/fluxo-de-caixa',
        '/analise-setores', '/analise-empresas',
        '/analise-horarios', '/analise-frotas', '/registros',
        '/visualizar-eventos',
    ],
    'gestao': [
        '/', '/analise-produtos', '/fluxo-de-caixa',
        '/analise-setores', '/analise-empresas',
        '/analise-horarios', '/analise-frotas', '/registros',
        '/auditoria-peso', '/gerenciar-arquivos', '/gerenciar-permissoes', '/gerenciar-eventos',
        '/visualizar-eventos',
    ],
    'superadmin': list(PAGES_TO_SEED.keys()),
}

DEFAULT_ADMIN_USER = {
    'email': 'admin@sistema.com',
    'name': 'Super Administrador',
    'password': 'senha123',
    'role': 'superadmin',
}


def run_startup_migrations():
    db.create_all()

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
        INSERT INTO "user" (name, email, password, active, confirmed_at, fs_uniquifier)
        VALUES (:name, :email, :password, :active, :confirmed_at, :fs_uniquifier)
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

    user_role_insert = text(
        """
        INSERT INTO roles_users (user_id, role_id)
        SELECT u.id, r.id
        FROM "user" u
        JOIN role r ON u.email = :email AND r.name = :role_name
        ON CONFLICT DO NOTHING
        """
    )

    with db.session.begin():
        for role_name in ROLES_TO_SEED:
            db.session.execute(
                role_upsert,
                {
                    'name': role_name,
                    'description': f'Nível: {role_name}',
                },
            )

        for route, description in PAGES_TO_SEED.items():
            db.session.execute(
                page_upsert,
                {
                    'route': route,
                    'description': description,
                },
            )

        for role_name, routes in DEFAULT_PERMISSIONS.items():
            for route in routes:
                db.session.execute(
                    permission_upsert,
                    {
                        'role_name': role_name,
                        'route': route,
                    },
                )

        admin_password = hash_password(DEFAULT_ADMIN_USER['password'])
        admin_unique = str(uuid4())
        inserted_admin = db.session.execute(
            user_insert,
            {
                'name': DEFAULT_ADMIN_USER['name'],
                'email': DEFAULT_ADMIN_USER['email'],
                'password': admin_password,
                'active': True,
                'confirmed_at': datetime.utcnow(),
                'fs_uniquifier': admin_unique,
            },
        ).scalar()

        if inserted_admin is None:
            admin_id = db.session.execute(
                user_select,
                {'email': DEFAULT_ADMIN_USER['email']},
            ).scalar_one()
        else:
            admin_id = inserted_admin

        db.session.execute(
            user_role_insert,
            {
                'email': DEFAULT_ADMIN_USER['email'],
                'role_name': DEFAULT_ADMIN_USER['role'],
            },
        )

    return {
        'roles': len(ROLES_TO_SEED),
        'pages': len(PAGES_TO_SEED),
        'admin_id': admin_id,
    }