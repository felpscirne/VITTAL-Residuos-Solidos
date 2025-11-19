import os
from app import create_app, db
from app.models import Role, Page, User
from flask_security.utils import hash_password

# (PAGES_TO_SEED e ROLES_TO_SEED continuam iguais...)
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
}

ROLES_TO_SEED = ['sem_login', 'geral', 'estudantil', 'gestao', 'superadmin']

DEFAULT_PERMISSIONS = {
    'sem_login': ['/', '/analise-produtos', '/fluxo-de-caixa'],
    'geral': ['/', '/analise-produtos', '/fluxo-de-caixa'],
    'estudantil': [
        '/', '/analise-produtos', '/fluxo-de-caixa', 
        '/analise-setores', '/analise-empresas', 
        '/analise-horarios', '/analise-frotas', '/registros'
    ],
    'gestao': [
        '/', '/analise-produtos', '/fluxo-de-caixa', 
        '/analise-setores', '/analise-empresas', 
        '/analise-horarios', '/analise-frotas', '/registros', 
        '/auditoria-peso', '/gerenciar-arquivos', '/gerenciar-permissoes'
    ],
    'superadmin': list(PAGES_TO_SEED.keys())
}

def seed_database():
    app = create_app()
    with app.app_context():
        
        # --- IMPORTANTE: Obtemos o Datastore do app ---
        # O Flask-Security anexa o datastore ao app.extensions['security'].datastore
        user_datastore = app.extensions['security'].datastore

        print(">>> Criando tabelas do banco de dados...")
        db.create_all()

        # 1. Criar Roles (Usando Datastore é mais seguro)
        print(">>> Verificando Roles...")
        for role_name in ROLES_TO_SEED:
            if not user_datastore.find_role(role_name):
                user_datastore.create_role(name=role_name, description=f"Nível: {role_name}")
                print(f"    + Role criada: {role_name}")
        db.session.commit()

        # 2. Criar/Atualizar Páginas (Continua igual, pois Page não é do Security)
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

        # 3. Resetar e Re-aplicar Permissões
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

        # 4. Criar Usuário Superadmin (CORRIGIDO)
        print(">>> Verificando Superadmin...")
        admin_email = "admin@sistema.com"
        
        if not user_datastore.find_user(email=admin_email):
            # --- CORREÇÃO AQUI: Usamos create_user ---
            # Ele gera o fs_uniquifier e hash da senha automaticamente
            user_datastore.create_user(
                email=admin_email,
                name="Super Administrador",
                password=hash_password("senha123"),
                roles=['superadmin'], # Passamos a role como lista de strings
                active=True,
                confirmed_at=None # Confirma o email
            )
            print(f"    + Superadmin criado: {admin_email} / senha123")
        
        db.session.commit()
        print("\n>>> Banco de dados sincronizado e pronto.")

if __name__ == '__main__':
    seed_database()