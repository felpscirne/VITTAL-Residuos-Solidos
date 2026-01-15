import dash
from dash import dcc, html, Input, Output, State, ClientsideFunction, callback_context
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask_login import current_user

from app import db
from app.models import Role, Page
from app.dash_app.pages import (
    overview,
    analise_produtos,
    analise_setores,
    analise_empresas,
    analise_horarios,
    analise_frotas,
    registros,
    auditoria_peso,
    gerenciar_eventos,
    gerenciar_arquivos,
    gerenciar_permissoes,
    visualizar_eventos,
    fluxo_de_caixa
)

def register_global_callbacks(app):

    PAGE_MAP = {
        "/": overview.layout,
        "/analise-produtos": analise_produtos.layout,
        "/analise-setores": analise_setores.layout,
        "/analise-empresas": analise_empresas.layout,
        "/analise-horarios": analise_horarios.layout,
        "/analise-frotas": analise_frotas.layout,
        "/registros": registros.layout,
        "/auditoria-peso": auditoria_peso.layout,
        "/gerenciar-eventos": gerenciar_eventos.layout,
        "/gerenciar-arquivos": gerenciar_arquivos.layout,
        "/gerenciar-permissoes": gerenciar_permissoes.layout,
        "/visualizar-eventos": visualizar_eventos.layout,
        "/fluxo-de-caixa": fluxo_de_caixa.layout,
    }

    @app.callback(
        Output('page-content-dynamic', 'children'),
        [Input('url', 'pathname')]
    )
    def display_page(pathname):
        if pathname in ['/login', '/logout', '/register']:
            return dash.no_update
        return PAGE_MAP.get(pathname, html.H1("404: Página não encontrada", className="text-center mt-5"))

    @app.callback(
        Output('sidebar-content', 'children'),
        Input('url', 'pathname')
    )
    def update_sidebar_content(pathname):
        if pathname in ['/login', '/logout', '/register']:
            return dash.no_update

        display_name = "Usuário"
        allowed_routes = []
        
        if current_user.is_authenticated:
            display_name = getattr(current_user, 'name', None) or current_user.email
            
            if hasattr(current_user, 'roles'):
                for role in current_user.roles:
                    for p in role.pages:
                        allowed_routes.append(p.route)

        def get_link(label, href, icon):
            return dmc.NavLink(
                label=label,
                href=href,
                leftSection=DashIconify(icon=icon, width=20),
                active=(pathname == href),
                variant="filled",
                color="blue",
                refresh=True
            )

        links_gerais = []
        if '/' in allowed_routes:
            links_gerais.append(get_link('Visão Geral', '/', "radix-icons:dashboard"))
        if '/analise-produtos' in allowed_routes:
            links_gerais.append(get_link('Análise de Produtos', '/analise-produtos', "radix-icons:cube"))
        if '/fluxo-de-caixa' in allowed_routes:
            links_gerais.append(get_link('Fluxo de Caixa', '/fluxo-de-caixa', "radix-icons:bar-chart"))
        if '/visualizar-eventos' in allowed_routes:
            links_gerais.append(get_link('Quadro de Avisos', '/visualizar-eventos', "radix-icons:bell"))

        links_protegidos = []
        if '/analise-setores' in allowed_routes:
             links_protegidos.append(get_link('Análise de Setores', '/analise-setores', "radix-icons:pie-chart"))
        if '/analise-empresas' in allowed_routes:
            links_protegidos.append(get_link('Análise de Empresas', '/analise-empresas', "radix-icons:backpack"))
        if '/analise-horarios' in allowed_routes:
             links_protegidos.append(get_link('Análise de Horários', '/analise-horarios', "radix-icons:clock"))
        if '/analise-frotas' in allowed_routes:
            links_protegidos.append(get_link('Análise de Frota', '/analise-frotas', "radix-icons:rocket"))
        if '/registros' in allowed_routes:
            links_protegidos.append(get_link('Buscar Registros', '/registros', "radix-icons:magnifying-glass"))

        links_gestao = []
        if '/auditoria-peso' in allowed_routes:
            links_gestao.append(get_link('Auditoria de Peso', '/auditoria-peso', "radix-icons:clipboard"))
        if '/gerenciar-eventos' in allowed_routes:
            links_gestao.append(get_link('Gerenciar Eventos', '/gerenciar-eventos', "radix-icons:calendar"))
        if '/gerenciar-arquivos' in allowed_routes:
            links_gestao.append(get_link('Gerenciar Arquivos', '/gerenciar-arquivos', "radix-icons:file"))
        if '/gerenciar-permissoes' in allowed_routes:
            links_gestao.append(get_link('Gerenciar Permissões', '/gerenciar-permissoes', "radix-icons:lock-closed"))

        # Links de Login/Logout
        links_login = []
        if current_user.is_authenticated:
            links_login.append(dmc.NavLink(
                label=f"Logout ({display_name})", 
                href="/logout", 
                leftSection=DashIconify(icon="radix-icons:exit", width=20),
                variant="subtle",
                color="red",
                refresh=True
            ))
        else:
            links_login.append(get_link("Login", "/login", "radix-icons:enter"))
            links_login.append(get_link("Registrar", "/register", "radix-icons:person"))

        return dmc.ScrollArea(
            offsetScrollbars=True,
            type="scroll",
            children=[
                dmc.Text("Geral", size="xs", fw=500, c="dimmed", mt="md", mb="xs"),
                *links_gerais,
                dmc.Divider(my="sm"),
                
                dmc.Text("Análises", size="xs", fw=500, c="dimmed", mb="xs"),
                *links_protegidos,
                dmc.Divider(my="sm"),
                
                dmc.Text("Gestão", size="xs", fw=500, c="dimmed", mb="xs"),
                *links_gestao,
                
                dmc.Divider(my="sm"),
                 *links_login
            ]
        )
