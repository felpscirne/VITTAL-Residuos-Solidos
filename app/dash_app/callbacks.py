import dash
from dash import html, Input, Output, State, ALL
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask_login import current_user

from app.dash_app.pages import (
    overview_page,
    estudo_ifescs_page,
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
from app.models import Role


def register_global_callbacks(app):
    page_map = {
        "/": overview_page.layout,
        "/estudo-ifescs": estudo_ifescs_page.layout,
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
        if current_user.is_authenticated:
            role = getattr(current_user, "role_ref", None)
        else:
            role = Role.query.filter_by(name="anonymous").first()

        allowed = []
        if role:
            for page in role.pages:
                allowed.append(page.route)
        return list(dict.fromkeys(allowed))

    def nav_link(label, href, icon, pathname, scope):
        is_active = pathname == href
        return dmc.NavLink(
            label=label,
            id={"type": "nav-link", "route": href, "scope": scope},
            leftSection=DashIconify(icon=icon, width=20),
            active=is_active,
            variant="filled" if is_active else "subtle",
            color="ifsc-green" if is_active else "gray",
            style={"cursor": "pointer"},
        )

    def auth_link(label, href, icon, pathname, color="ifsc-green", variant="filled"):
        is_active = pathname == href
        item = dmc.NavLink(
            label=label,
            leftSection=DashIconify(icon=icon, width=20),
            active=is_active,
            variant=variant if is_active else "subtle",
            color=color if is_active else "gray",
        )
        return html.A(
            item,
            href=href,
            style={
                "display": "block",
                "textDecoration": "none",
                "color": "inherit",
                "marginBottom": "4px",
            },
        )

    @app.callback(
        Output("url", "pathname"),
        Input({"type": "nav-link", "route": ALL, "scope": ALL}, "n_clicks"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    def navigate_internal(_clicks, current_pathname):
        triggered = dash.ctx.triggered_id
        if not triggered or not isinstance(triggered, dict):
            return dash.no_update
        route = triggered.get("route")
        if not route or route == current_pathname:
            return dash.no_update
        return route

    @app.callback(
        Output("page-content-dynamic", "children"),
        Input("url", "pathname"),
    )
    def display_page(pathname):
        if pathname in ["/login", "/logout", "/register"]:
            return dash.no_update

        if pathname not in page_map:
            return html.H1("404: Página não encontrada", className="text-center mt-5")

        allowed_routes = get_allowed_routes()
        if pathname not in allowed_routes:
            if current_user.is_authenticated:
                return dmc.Alert(
                    "Você não possui permissão para acessar esta página.",
                    title="Acesso negado",
                    color="red",
                    variant="light",
                )
            return dmc.Alert(
                "Faça login com um perfil autorizado para acessar esta página.",
                title="Acesso restrito",
                color="yellow",
                variant="light",
            )

        return page_map[pathname]

    @app.callback(
        Output("sidebar-content", "children"),
        Output("mobile-sidebar-content", "children"),
        Input("url", "pathname"),
    )
    def update_sidebar_content(pathname):
        if pathname in ["/login", "/logout", "/register"]:
            return dash.no_update, dash.no_update

        allowed_routes = get_allowed_routes()
        display_name = "Usuário"
        if current_user.is_authenticated:
            display_name = getattr(current_user, "name", None) or current_user.email

        def build_sidebar(scope):
            links_gerais = []
            if "/" in allowed_routes:
                links_gerais.append(nav_link("Visão Geral", "/", "radix-icons:dashboard", pathname, scope))
            if "/estudo-ifescs" in allowed_routes:
                links_gerais.append(nav_link("Ambiente de Estudo", "/estudo-ifescs", "radix-icons:reader", pathname, scope))
            if "/registros" in allowed_routes:
                links_gerais.append(nav_link("Buscar Registros", "/registros", "radix-icons:magnifying-glass", pathname, scope))
            if "/visualizar-eventos" in allowed_routes:
                links_gerais.append(nav_link("Quadro de Avisos", "/visualizar-eventos", "radix-icons:bell", pathname, scope))

            links_analises = []
            if "/analise-produtos" in allowed_routes:
                links_analises.append(nav_link("Análise de Produtos", "/analise-produtos", "radix-icons:cube", pathname, scope))
            if "/fluxo-de-caixa" in allowed_routes:
                links_analises.append(nav_link("Fluxo de Caixa", "/fluxo-de-caixa", "radix-icons:bar-chart", pathname, scope))
            if "/analise-setores" in allowed_routes:
                links_analises.append(nav_link("Análise de Setores", "/analise-setores", "radix-icons:pie-chart", pathname, scope))
            if "/analise-empresas" in allowed_routes:
                links_analises.append(nav_link("Análise de Empresas", "/analise-empresas", "radix-icons:backpack", pathname, scope))
            if "/analise-horarios" in allowed_routes:
                links_analises.append(nav_link("Análise de Horários", "/analise-horarios", "radix-icons:clock", pathname, scope))
            if "/analise-frotas" in allowed_routes:
                links_analises.append(nav_link("Análise de Frota", "/analise-frotas", "radix-icons:rocket", pathname, scope))

            links_gestao = []
            if "/previsoes" in allowed_routes:
                links_gestao.append(nav_link("Previsões", "/previsoes", "radix-icons:activity-log", pathname, scope))
            if "/auditoria-peso" in allowed_routes:
                links_gestao.append(nav_link("Auditoria de Peso", "/auditoria-peso", "radix-icons:clipboard", pathname, scope))
            if "/gerenciar-eventos" in allowed_routes:
                links_gestao.append(nav_link("Gerenciar Eventos", "/gerenciar-eventos", "radix-icons:calendar", pathname, scope))
            if "/gerenciar-arquivos" in allowed_routes:
                links_gestao.append(nav_link("Gerenciar Arquivos", "/gerenciar-arquivos", "radix-icons:file", pathname, scope))
            if "/gerenciar-permissoes" in allowed_routes:
                links_gestao.append(nav_link("Gerenciar Permissões", "/gerenciar-permissoes", "radix-icons:lock-closed", pathname, scope))

            links_login = []
            if current_user.is_authenticated:
                links_login.append(
                    auth_link(
                        f"Sair ({display_name})",
                        "/logout",
                        "radix-icons:exit",
                        pathname,
                        color="red",
                        variant="subtle",
                    )
                )
            else:
                links_login.append(auth_link("Entrar", "/login", "radix-icons:enter", pathname))
                links_login.append(auth_link("Registrar", "/register", "radix-icons:person", pathname))

            sidebar_children = []
            if links_gerais:
                sidebar_children.extend(
                    [
                        dmc.Text("Geral", size="xs", fw=500, c="dimmed", mt="md", mb="xs"),
                        *links_gerais,
                        dmc.Divider(my="sm"),
                    ]
                )

            if links_analises:
                sidebar_children.extend(
                    [
                        dmc.Text("Análises", size="xs", fw=500, c="dimmed", mb="xs"),
                        *links_analises,
                        dmc.Divider(my="sm"),
                    ]
                )

            if links_gestao:
                sidebar_children.extend(
                    [
                        dmc.Text("Gestão", size="xs", fw=500, c="dimmed", mb="xs"),
                        *links_gestao,
                        dmc.Divider(my="sm"),
                    ]
                )

            sidebar_children.extend(links_login)

            return dmc.ScrollArea(
                offsetScrollbars=True,
                type="scroll",
                children=sidebar_children,
            )

        return build_sidebar("desktop"), build_sidebar("mobile")

    @app.callback(
        Output("mobile-nav-open", "data"),
        Input("burger-button", "n_clicks"),
        Input("mobile-nav-close", "n_clicks"),
        Input("mobile-nav-overlay", "n_clicks"),
        Input("url", "pathname"),
        State("mobile-nav-open", "data"),
        prevent_initial_call=True,
    )
    def update_mobile_nav_state(burger_clicks, close_clicks, overlay_clicks, pathname, is_open):
        triggered_id = dash.ctx.triggered_id
        if triggered_id == "burger-button":
            return not bool(is_open)

        if triggered_id in {"mobile-nav-close", "mobile-nav-overlay", "url"}:
            return False

        return dash.no_update

    @app.callback(
        Output("mobile-nav-overlay", "style"),
        Output("mobile-nav-panel", "style"),
        Input("mobile-nav-open", "data"),
        Input("mantine-provider", "forceColorScheme"),
    )
    def render_mobile_navbar(is_open, color_scheme):
        open_overlay_style = {
            "position": "fixed",
            "inset": "0",
            "backgroundColor": "rgba(15, 23, 42, 0.45)",
            "zIndex": 199,
            "display": "block",
        }
        open_panel_style = {
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "85vw",
            "maxWidth": "360px",
            "height": "100vh",
            "backgroundColor": "#1a1b1e" if color_scheme == "dark" else "#ffffff",
            "padding": "1rem",
            "boxShadow": "0 10px 30px rgba(0, 0, 0, 0.18)",
            "zIndex": 200,
            "overflowY": "auto",
            "display": "block",
        }
        closed_style = {"display": "none"}

        if is_open:
            return open_overlay_style, open_panel_style

        return closed_style, closed_style
