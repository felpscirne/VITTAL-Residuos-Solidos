import dash
from dash import dcc, html, Input, Output, State, ClientsideFunction, callback_context
import dash_bootstrap_components as dbc
from flask_login import current_user


from .pages import (
    overview, 
    analise_setores,
    analise_empresas,
    analise_produtos,
    analise_horarios,
    analise_frotas,
    auditoria_peso,
    registros,
    fluxo_de_caixa
)

PAGE_PERMISSIONS = {
    'sem_login': [
        '/',
        '/analise-produtos',
        '/fluxo-de-caixa',
    ],
    'geral': [
        '/',
        '/analise-produtos',
        '/fluxo-de-caixa',
    ],
    'estudantil': [
        '/',
        '/analise-produtos',
        '/analise-setores',
        '/analise-empresas',
        '/fluxo-de-caixa',
        '/analise-frotas',
        '/registros',
    ],
    'gestao': [
        '/',
        '/analise-produtos',
        '/analise-horarios',
        '/analise-setores',
        '/analise-empresas',
        '/fluxo-de-caixa',
        '/analise-frotas',
        '/registros',
        '/auditoria-peso',
    ],
}

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
        

        if pathname in ['/login', '/logout', '/register']:
            return dash.no_update

        if current_user.is_authenticated:
            user_role = current_user.role 
        else:
            user_role = 'sem_login'

        if user_role == 'superadmin':
            allowed_pages_for_role = list(PAGE_MAP.keys()) # Superadmin vê tudo
        else:
            allowed_pages_for_role = PAGE_PERMISSIONS.get(user_role, [])
        
        if pathname not in allowed_pages_for_role:
            if user_role == 'sem_login':
                return login_required_layout
            else:
                return access_denied_layout
        
        page_layout = PAGE_MAP.get(pathname, "404: Página não encontrada")
        return page_layout

 
    @app.callback(
        Output('sidebar-content', 'children'),
        Input('url', 'pathname') 
    )
    def update_sidebar_content(pathname):
        if current_user.is_authenticated:
            user_role = current_user.role
        else:
            user_role = 'sem_login'
            
        if user_role == 'superadmin':
            allowed_pages_for_role = list(PAGE_MAP.keys())
        else:
            allowed_pages_for_role = PAGE_PERMISSIONS.get(user_role, [])

        # Cria os links com base na role
        links_gerais = []
        if '/' in allowed_pages_for_role:
            links_gerais.append(dbc.NavLink('Visão Geral', href='/', active="exact"))
        if '/analise-produtos' in allowed_pages_for_role:
            links_gerais.append(dbc.NavLink('Análise de Produtos', href='/analise-produtos', active="exact"))
        if '/fluxo-de-caixa' in allowed_pages_for_role:
            links_gerais.append(dbc.NavLink('Fluxo de Caixa', href='/fluxo-de-caixa', active="exact"))

        links_protegidos = []
        if '/analise-setores' in allowed_pages_for_role:
             links_protegidos.append(dbc.NavLink('Análise de Setores', href='/analise-setores', active="exact"))
        if '/analise-empresas' in allowed_pages_for_role:
            links_protegidos.append(dbc.NavLink('Análise de Empresas', href='/analise-empresas', active="exact"))
        if '/analise-horarios' in allowed_pages_for_role:
             links_protegidos.append(dbc.NavLink('Análise de Horários', href='/analise-horarios', active="exact"))
        if '/analise-frotas' in allowed_pages_for_role:
            links_protegidos.append(dbc.NavLink('Análise de Frota', href='/analise-frotas', active="exact"))
        if '/registros' in allowed_pages_for_role:
            links_protegidos.append(dbc.NavLink('Buscar Registros', href='/registros', active="exact"))

        links_gestao = []
        if '/auditoria-peso' in allowed_pages_for_role:
            links_gestao.append(dbc.NavLink('Auditoria de Peso', href='/auditoria-peso', active="exact", className="text-warning"))
        
        if current_user.is_authenticated:
            links_login = [dbc.NavLink(f"Logout ({current_user.name})", href="/logout", active="exact", className="mt-5", external_link=True)]
        else:
            links_login = [
                dbc.NavLink("Login", href="/login", active="exact", className="mt-5", external_link=True),
                dbc.NavLink("Registrar", href="/register", active="exact", external_link=True)
            ]

        return [
            html.H2("IFEsCS", className="text-white"),
            html.H5("Plataforma Web de Análise", className="text-white"),
            html.Hr(className="text-white"),
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
        else: # current_state == 'collapsed'
            return 'sidebar navbar-dark bg-dark', 'content', 'open'

    app.clientside_callback(
        """
        function(switch_on) {
            // 'switch_on' é True para claro, False para escuro
            var theme = switch_on ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', theme);
            return window.dash_clientside.no_update;
        }
        """,
        Output('dummy-theme-output', 'children'),
        Input("theme-switch", "value")
    )