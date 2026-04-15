from dash import callback, dcc, html, no_update
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app import db
from app.models import Page, Role
from app.services.error_messages import get_safe_database_error_message
from app.services.localization import get_role_label


def get_roles_options():
    try:
        roles = Role.query.filter(Role.name != "superadmin").order_by(Role.description, Role.name).all()
        return [{"label": role.description or get_role_label(role.name), "value": str(role.id)} for role in roles]
    except Exception:
        return []


def get_pages_options():
    try:
        hidden_routes = ["/gerenciar-permissoes", "/gerenciar-arquivos"]
        pages = Page.query.filter(~Page.route.in_(hidden_routes)).order_by(Page.route).all()
        return [{"label": f"{page.description} ({page.route})", "value": str(page.id)} for page in pages]
    except Exception:
        return []


layout = html.Div(
    [
        dmc.Title("Gerenciamento de Permissoes", order=2),
        dmc.Text(
            "Controle dinamico de acesso. Selecione um perfil e defina o que ele pode visualizar.",
            c="dimmed",
            size="sm",
        ),
        dmc.Divider(variant="solid", my="md"),
        dmc.Alert(
            "As alteracoes aplicadas nesta tela atualizam imediatamente o acesso do perfil selecionado.",
            title="Atencao",
            color="yellow",
            variant="filled",
            icon=DashIconify(icon="akar-icons:triangle-alert"),
            mb="md",
        ),
        dmc.Card(
            [
                dmc.Text("Configuracao de acesso", size="lg", fw=500, mb="sm"),
                dmc.Select(
                    label="1. Selecione o perfil para editar:",
                    placeholder="Selecione um perfil...",
                    id="perm-role-select",
                    data=get_roles_options(),
                    mb="md",
                ),
                dmc.Text("2. Marque as paginas permitidas:", size="sm", fw=500, mb="xs"),
                dmc.Card(
                    children=[
                        dcc.Loading(
                            dmc.CheckboxGroup(
                                id="perm-page-checklist",
                                value=[],
                                children=dmc.Stack(
                                    [dmc.Checkbox(label=option["label"], value=option["value"]) for option in get_pages_options()],
                                    gap="sm",
                                ),
                            )
                        )
                    ],
                    withBorder=True,
                    mb="md",
                    p="md",
                ),
                dmc.Button(
                    "Salvar permissoes",
                    id="btn-save-perms",
                    color="green",
                    leftSection=DashIconify(icon="akar-icons:check"),
                    fullWidth=True,
                ),
                html.Div(id="dummy-save-perm-output"),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
        ),
    ]
)


@callback(
    Output("perm-page-checklist", "value"),
    Input("perm-role-select", "value"),
)
def load_role_permissions(role_id_str):
    if not role_id_str:
        return []

    try:
        role = Role.query.get(int(role_id_str))
        if not role:
            return []
        return [str(page.id) for page in role.pages]
    except Exception:
        return []


@callback(
    Output("dummy-save-perm-output", "children"),
    Input("btn-save-perms", "n_clicks"),
    [State("perm-role-select", "value"), State("perm-page-checklist", "value")],
    prevent_initial_call=True,
)
def save_permissions(n_clicks, role_id_str, selected_page_ids_str):
    if not role_id_str:
        return dmc.Notification(
            title="Erro",
            id="notify-error-select",
            action="show",
            message="Selecione um perfil primeiro.",
            color="red",
        )

    try:
        role = Role.query.get(int(role_id_str))
        if not role:
            return dmc.Notification(
                title="Erro",
                id="notify-error-notfound",
                action="show",
                message="Perfil nao encontrado.",
                color="red",
            )

        role.pages = []
        if selected_page_ids_str:
            for page_id in selected_page_ids_str:
                page = Page.query.get(int(page_id))
                if page:
                    role.pages.append(page)

        db.session.commit()

        return dmc.Notification(
            title="Sucesso",
            id="notify-success",
            action="show",
            message=f"Permissoes atualizadas para {role.description or get_role_label(role.name)}.",
            color="green",
        )
    except Exception:
        db.session.rollback()
        return dmc.Notification(
            title="Erro",
            id="notify-exception",
            action="show",
            message=get_safe_database_error_message(),
            color="red",
        )
