import dash
from dash import dcc, html, Input, Output, State, ClientsideFunction, callback_context
import dash_bootstrap_components as dbc
from flask_login import current_user

from app import db
from app.models import Role, Page

from .pages import (
    overview, 
    analise_setores,
    analise_empresas,
    analise_produtos,
    analise_horarios,
    analise_frotas,
    auditoria_peso,
    registros,
    fluxo_de_caixa,
    gerenciar_arquivos,
    gerenciar_permissoes,
    gerenciar_eventos,
    visualizar_eventos
)


PAGE_MAP = {
    '/': overview.layout,
    '/analise-setores': analise_setores.layout,
    '/analise-empresas': analise_empresas.layout,
    '/analise-produtos': analise_produtos.layout,
    '/analise-horarios': analise_horarios.layout,
    '/analise-frotas': analise_frotas.layout,
    '/auditoria-peso': auditoria_peso.layout,
    '/registros': registros.layout,
    '/fluxo-de-caixa': fluxo_de_caixa.layout,
    '/gerenciar-arquivos': gerenciar_arquivos.layout,
    '/gerenciar-permissoes': gerenciar_permissoes.layout,
    '/gerenciar-eventos': gerenciar_eventos.layout,
    '/visualizar-eventos': visualizar_eventos.layout
}

# Layouts de erro
access_denied_layout = dbc.Container([
    html.H1("Acesso Negado", className="text-danger mt-5"),
    html.P("Você não tem permissão para acessar este recurso."),
    dcc.Link(dbc.Button("Ir para a Visão Geral"), href="/"),
], className="mt-5")

login_required_layout = dbc.Container([
    html.H1("Login Necessário", className="mt-5"),
    html.P("Você precisa fazer login para acessar este recurso."),
    html.A(dbc.Button("Fazer Login"), href="/login"),
    html.A(dbc.Button("Registrar", outline=True, color="secondary", className="ms-2"), href="/register"),
], className="mt-5")


def register_global_callbacks(app):

    @app.callback(
        Output('page-content-dynamic', 'children'),
        [Input('url', 'pathname')]
    )
    def display_page(pathname):
        
        # Ignora rotas de autenticação do Flask
        if pathname in ['/login', '/logout', '/register']:
            return dash.no_update
        
        if current_user.is_authenticated:
        
            try:
                user_role_name = current_user.role 
            except:
                user_role_name = 'geral'
        else:
            user_role_name = 'sem_login'

        permission_granted = False
        
        if user_role_name == 'superadmin':
            permission_granted = True 
        else:
            permission = db.session.query(Page).join(Role.pages).filter(
                Role.name == user_role_name,
                Page.route == pathname
            ).first()
            
            if permission:
                permission_granted = True
            if pathname == '/' and not permission:
               
                 pass
        
        if not permission_granted:
            if user_role_name == 'sem_login':
                return login_required_layout
            else:
                return access_denied_layout
        
        return PAGE_MAP.get(pathname, html.H1("404: Página não encontrada", className="text-center mt-5"))


    @app.callback(
        Output('sidebar-content', 'children'),
        Input('url', 'pathname')
    )
    def update_sidebar_content(pathname):
        if pathname in ['/login', '/logout', '/register']:
            return dash.no_update

        if current_user.is_authenticated:
            user_role_name = current_user.role
            try:
                display_name = current_user.name if current_user.name else current_user.email
            except:
                display_name = current_user.email
        else:
            user_role_name = 'sem_login'
            display_name = ""
            
        allowed_routes = []
        if user_role_name == 'superadmin':
            allowed_routes = list(PAGE_MAP.keys())
        else:
            role = Role.query.filter_by(name=user_role_name).first()
            if role:
                allowed_routes = [p.route for p in role.pages]

        
        links_gerais = []
        if '/' in allowed_routes:
            links_gerais.append(dbc.NavLink('Visao Geral', href='/', active="exact"))
        if '/analise-produtos' in allowed_routes:
            links_gerais.append(dbc.NavLink('Analise de Produtos', href='/analise-produtos', active="exact"))
        if '/fluxo-de-caixa' in allowed_routes:
            links_gerais.append(dbc.NavLink('Fluxo de Caixa', href='/fluxo-de-caixa', active="exact"))
        if '/visualizar-eventos' in allowed_routes:
            links_gerais.append(dbc.NavLink('Quadro de Avisos', href='/visualizar-eventos', active="exact"))

        links_protegidos = []
        if '/analise-setores' in allowed_routes:
             links_protegidos.append(dbc.NavLink('Analise de Setores', href='/analise-setores', active="exact"))
        if '/analise-empresas' in allowed_routes:
            links_protegidos.append(dbc.NavLink('Analise de Empresas', href='/analise-empresas', active="exact"))
        if '/analise-horarios' in allowed_routes:
             links_protegidos.append(dbc.NavLink('Analise de Horários', href='/analise-horarios', active="exact"))
        if '/analise-frotas' in allowed_routes:
            links_protegidos.append(dbc.NavLink('Analise de Frota', href='/analise-frotas', active="exact"))
        if '/registros' in allowed_routes:
            links_protegidos.append(dbc.NavLink('Buscar Registros', href='/registros', active="exact"))

        links_gestao = []
        if '/auditoria-peso' in allowed_routes:
            links_gestao.append(dbc.NavLink('Auditoria de Peso', href='/auditoria-peso', active="exact", className="text-warning"))
        if '/gerenciar-eventos' in allowed_routes:
            links_gestao.append(dbc.NavLink('Gerenciar Eventos', href='/gerenciar-eventos', active="exact", className="text-danger"))
        if '/gerenciar-arquivos' in allowed_routes:
            links_gestao.append(dbc.NavLink('Gerenciar Arquivos', href='/gerenciar-arquivos', active="exact", className="text-info"))
        if '/gerenciar-permissoes' in allowed_routes:
            links_gestao.append(dbc.NavLink('Gerenciar Permissões', href='/gerenciar-permissoes', active="exact", className="text-danger"))

        # Links de Login/Logout
        if current_user.is_authenticated:
            links_login = [dbc.NavLink(f"Logout ({display_name})", href="/logout", active="exact", className="mt-5", external_link=True)]
        else:
            links_login = [
                dbc.NavLink("Login", href="/login", active="exact", className="mt-5", external_link=True),
                dbc.NavLink("Registrar", href="/register", active="exact", external_link=True)
            ]

        return [
            html.H2("IFEsCS", className="text-white"),
            dbc.Nav(links_gerais, vertical=True, pills=True),
            dbc.Nav(links_protegidos, vertical=True, pills=True),
            dbc.Nav(links_gestao, vertical=True, pills=True),
            dbc.Nav(links_login, vertical=True, pills=True),
        ]

    @app.callback(
        [Output('sidebar', 'className'),
         Output('page-content', 'className'),
         Output('sidebar-state', 'data')],
        [Input('btn-collapse', 'n_clicks')],
        [State('sidebar-state', 'data')],
        prevent_initial_call=True
    )
    def toggle_sidebar_collapse(n_clicks, current_state):
        ctx = dash.callback_context 
        if not ctx.triggered:
             return dash.no_update

        if current_state == 'open':
            return 'sidebar navbar-dark bg-dark collapsed', 'content collapsed', 'collapsed'
        else: 
            return 'sidebar navbar-dark bg-dark', 'content', 'open'

    app.clientside_callback(
        """
        function(switch_on) {
            var theme = switch_on ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', theme);
            return window.dash_clientside.no_update;
        }
        """,
        Output('dummy-theme-output', 'children'),
        Input("theme-switch", "value")
    )