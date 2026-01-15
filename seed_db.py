import os
from app import create_app, db
from app.models import Role, Page, User
from flask_security.utils import hash_password
from datetime import datetime

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
    'gerenciar-eventos': 'Gerenciar Eventos',
    '/visualizar-eventos': 'Quadro de Avisos e Eventos'
}

ROLES_TO_SEED = ['sem_login', 'geral', 'estudantil', 'gestao', 'superadmin']

DEFAULT_PERMISSIONS = {
    'sem_login': ['/', '/analise-produtos', '/fluxo-de-caixa', '/visualizar-eventos'],
    'geral': ['/', '/analise-produtos', '/fluxo-de-caixa', '/visualizar-eventos'],
    'estudantil': [
        '/', '/analise-produtos', '/fluxo-de-caixa', 
        '/analise-setores', '/analise-empresas', 
        '/analise-horarios', '/analise-frotas', '/registros',
        '/visualizar-eventos'
    ],
    'gestao': [
        '/', '/analise-produtos', '/fluxo-de-caixa', 
        '/analise-setores', '/analise-empresas', 
        '/analise-horarios', '/analise-frotas', '/registros', 
        '/auditoria-peso', '/gerenciar-arquivos', '/gerenciar-permissoes', '/gerenciar-eventos',
        '/visualizar-eventos'
    ],
    'superadmin': list(PAGES_TO_SEED.keys())
}

def seed_database():
    app = create_app()
    with app.app_context():
        
       
        user_datastore = app.extensions['security'].datastore

        print(">>> Criando tabelas do banco de dados...")
        db.create_all()

        print(">>> Verificando Roles...")
        for role_name in ROLES_TO_SEED:
            if not user_datastore.find_role(role_name):
                user_datastore.create_role(name=role_name, description=f"Nível: {role_name}")
                print(f"    + Role criada: {role_name}")
        db.session.commit()

        print(">>> Verificando Páginas...")
        for route, desc in PAGES_TO_SEED.items():
            page = Page.query.filter_by(route=route).first()
            if not page:
                page = Page(route=route, description=desc)
                db.session.add(page)
                print(f"    + Página criada: {route}")
            else:
                page.description = desc
        db.session.commit()

        print(">>> Sincronizando Permissões...")
        for role_name, routes in DEFAULT_PERMISSIONS.items():
            role = user_datastore.find_role(role_name) # Usa datastore
            if not role: continue
            
            role.pages = [] 
            for route in routes:
                page = Page.query.filter_by(route=route).first()
                if page:
                    role.pages.append(page)
        db.session.commit()

        print(">>> Verificando Superadmin...")
        admin_email = "admin@sistema.com"
        
        if not user_datastore.find_user(email=admin_email):
       
            user_datastore.create_user(
                email=admin_email,
                name="Super Administrador",
                password=hash_password("senha123"),
                roles=['superadmin'],
                active=True,
                confirmed_at=datetime.now()
            )
            print(f"    + Superadmin criado: {admin_email} / senha123")
        
        db.session.commit()
        print("\n>>> Banco de dados sincronizado e pronto.")

if __name__ == '__main__':
    seed_database()