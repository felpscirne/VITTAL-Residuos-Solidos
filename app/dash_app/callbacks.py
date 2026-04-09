import dash
from dash import html, Input, Output
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask_login import current_user

from app.dash_app.pages import (
    overview_page,
    previsoes_page,
    analise_produtos_page,
    analise_setores_page,
    analise_empresas_page,
    analise_horarios_page,
    analise_frotas_page,
    registros_page,
    auditoria_peso_page,
    gerenciar_eventos_page,
    gerenciar_arquivos_page,
    gerenciar_permissoes_page,
    visualizar_eventos_page,
    fluxo_de_caixa_page,
)


def register_global_callbacks(app):
    public_routes = {"/", "/analise-produtos", "/fluxo-de-caixa", "/visualizar-eventos"}

    page_map = {
        "/": overview_page.layout,
        "/previsoes": previsoes_page.layout,
        "/analise-produtos": analise_produtos_page.layout,
        "/analise-setores": analise_setores_page.layout,
        "/analise-empresas": analise_empresas_page.layout,
        "/analise-horarios": analise_horarios_page.layout,
        "/analise-frotas": analise_frotas_page.layout,
        "/registros": registros_page.layout,
        "/auditoria-peso": auditoria_peso_page.layout,
        "/gerenciar-eventos": gerenciar_eventos_page.layout,
        "/gerenciar-arquivos": gerenciar_arquivos_page.layout,
        "/gerenciar-permissoes": gerenciar_permissoes_page.layout,
        "/visualizar-eventos": visualizar_eventos_page.layout,
        "/fluxo-de-caixa": fluxo_de_caixa_page.layout,
    }

    def get_allowed_routes():
        if not current_user.is_authenticated:
            return []

        allowed = []
        if hasattr(current_user, "roles"):
            for role in current_user.roles:
                for page in role.pages:
                    allowed.append(page.route)
        return list(dict.fromkeys(allowed))

    @app.callback(
        Output("page-content-dynamic", "children"),
        [Input("url", "pathname")],
    )
    def display_page(pathname):
        if pathname in ["/login", "/logout", "/register"]:
            return dash.no_update

        if pathname not in page_map:
            return html.H1("404: Pagina nao encontrada", className="text-center mt-5")

        if current_user.is_authenticated:
            if pathname not in get_allowed_routes():
                return dmc.Alert(
                    "Voce nao possui permissao para acessar esta pagina.",
                    title="Acesso negado",
                    color="red",
                    variant="light",
                )
        elif pathname not in public_routes:
            return dmc.Alert(
                "Faca login com um perfil autorizado para acessar esta pagina.",
                title="Acesso restrito",
                color="yellow",
                variant="light",
            )

        return page_map[pathname]

    @app.callback(
        Output("sidebar-content", "children"),
        Input("url", "pathname"),
    )
    def update_sidebar_content(pathname):
        if pathname in ["/login", "/logout", "/register"]:
            return dash.no_update

        display_name = "Usuario"
        allowed_routes = get_allowed_routes()

        if current_user.is_authenticated:
            display_name = getattr(current_user, "name", None) or current_user.email

        def get_link(label, href, icon):
            return dmc.NavLink(
                label=label,
                href=href,
                leftSection=DashIconify(icon=icon, width=20),
                active=(pathname == href),
                variant="filled",
                color="ifsc-green",
                refresh=True,
            )

        links_gerais = []
        if current_user.is_authenticated:
            if "/" in allowed_routes:
                links_gerais.append(get_link("Visao Geral", "/", "radix-icons:dashboard"))
            if "/analise-produtos" in allowed_routes:
                links_gerais.append(get_link("Analise de Produtos", "/analise-produtos", "radix-icons:cube"))
            if "/fluxo-de-caixa" in allowed_routes:
                links_gerais.append(get_link("Fluxo de Caixa", "/fluxo-de-caixa", "radix-icons:bar-chart"))
            if "/visualizar-eventos" in allowed_routes:
                links_gerais.append(get_link("Quadro de Avisos", "/visualizar-eventos", "radix-icons:bell"))
        else:
            links_gerais.append(get_link("Visao Geral", "/", "radix-icons:dashboard"))
            links_gerais.append(get_link("Analise de Produtos", "/analise-produtos", "radix-icons:cube"))
            links_gerais.append(get_link("Fluxo de Caixa", "/fluxo-de-caixa", "radix-icons:bar-chart"))
            links_gerais.append(get_link("Quadro de Avisos", "/visualizar-eventos", "radix-icons:bell"))

        links_protegidos = []
        if "/analise-setores" in allowed_routes:
            links_protegidos.append(get_link("Analise de Setores", "/analise-setores", "radix-icons:pie-chart"))
        if "/analise-empresas" in allowed_routes:
            links_protegidos.append(get_link("Analise de Empresas", "/analise-empresas", "radix-icons:backpack"))
        if "/analise-horarios" in allowed_routes:
            links_protegidos.append(get_link("Analise de Horarios", "/analise-horarios", "radix-icons:clock"))
        if "/analise-frotas" in allowed_routes:
            links_protegidos.append(get_link("Analise de Frota", "/analise-frotas", "radix-icons:rocket"))
        if "/registros" in allowed_routes:
            links_protegidos.append(get_link("Buscar Registros", "/registros", "radix-icons:magnifying-glass"))

        links_gestao = []
        if "/previsoes" in allowed_routes:
            links_gestao.append(get_link("Previsoes", "/previsoes", "radix-icons:activity-log"))
        if "/auditoria-peso" in allowed_routes:
            links_gestao.append(get_link("Auditoria de Peso", "/auditoria-peso", "radix-icons:clipboard"))
        if "/gerenciar-eventos" in allowed_routes:
            links_gestao.append(get_link("Gerenciar Eventos", "/gerenciar-eventos", "radix-icons:calendar"))
        if "/gerenciar-arquivos" in allowed_routes:
            links_gestao.append(get_link("Gerenciar Arquivos", "/gerenciar-arquivos", "radix-icons:file"))
        if "/gerenciar-permissoes" in allowed_routes:
            links_gestao.append(get_link("Gerenciar Permissoes", "/gerenciar-permissoes", "radix-icons:lock-closed"))

        links_login = []
        if current_user.is_authenticated:
            links_login.append(
                dmc.NavLink(
                    label=f"Logout ({display_name})",
                    href="/logout",
                    leftSection=DashIconify(icon="radix-icons:exit", width=20),
                    variant="subtle",
                    color="red",
                    refresh=True,
                )
            )
        else:
            links_login.append(get_link("Login", "/login", "radix-icons:enter"))
            links_login.append(get_link("Registrar", "/register", "radix-icons:person"))

        sidebar_children = []

        if links_gerais:
            sidebar_children.extend([
                dmc.Text("Geral", size="xs", fw=500, c="dimmed", mt="md", mb="xs"),
                *links_gerais,
                dmc.Divider(my="sm"),
            ])

        if links_protegidos:
            sidebar_children.extend([
                dmc.Text("Analises", size="xs", fw=500, c="dimmed", mb="xs"),
                *links_protegidos,
                dmc.Divider(my="sm"),
            ])

        if links_gestao:
            sidebar_children.extend([
                dmc.Text("Gestao", size="xs", fw=500, c="dimmed", mb="xs"),
                *links_gestao,
                dmc.Divider(my="sm"),
            ])

        sidebar_children.extend(links_login)

        return dmc.ScrollArea(
            offsetScrollbars=True,
            type="scroll",
            children=sidebar_children,
        )
