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
        roles = Role.query.order_by(Role.description, Role.name).all()
        return [{"label": role.description or get_role_label(role.name), "value": str(role.id)} for role in roles]
    except Exception:
        return []


def get_pages_options():
    try:
        hidden_routes = ["/gerenciar-permissoes"]
        pages = Page.query.filter(~Page.route.in_(hidden_routes)).order_by(Page.description, Page.route).all()
        return [{"label": f"{page.description} ({page.route})", "value": str(page.id)} for page in pages]
    except Exception:
        return []


layout = html.Div(
    [
        dmc.Title("Gerenciamento de permissões", order=2),
        dmc.Text(
            "Controle dinâmico de acesso. Selecione um perfil e defina quais páginas ele pode visualizar.",
            c="dimmed",
            size="sm",
        ),
        dmc.Divider(variant="solid", my="md"),
        dmc.Card(
            [
                dmc.Text("Configuração de acesso", size="lg", fw=500, mb="sm"),
                dmc.Select(
                    label="1. Selecione o perfil para editar",
                    placeholder="Selecione um perfil...",
                    id="perm-role-select",
                    data=get_roles_options(),
                    mb="md",
                ),
                dmc.Text("2. Marque as páginas permitidas", size="sm", fw=500, mb="xs"),
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
                    "Salvar permissões",
                    id="btn-save-perms",
                    color="green",
                    leftSection=DashIconify(icon="akar-icons:check"),
                    fullWidth=True,
                ),
                html.Div(id="perm-save-feedback", style={"paddingTop": "12px"}),
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
    [Output("dummy-save-perm-output", "children"), Output("perm-save-feedback", "children")],
    Input("btn-save-perms", "n_clicks"),
    [State("perm-role-select", "value"), State("perm-page-checklist", "value")],
    prevent_initial_call=True,
)
def save_permissions(n_clicks, role_id_str, selected_page_ids_str):
    if not role_id_str:
        feedback = dmc.Alert(
            "Selecione um perfil antes de salvar.",
            color="red",
            variant="light",
            title="Não foi possível salvar",
            icon=DashIconify(icon="akar-icons:triangle-alert"),
        )
        return no_update, feedback

    try:
        role = Role.query.get(int(role_id_str))
        if not role:
            feedback = dmc.Alert(
                "O perfil selecionado não foi encontrado.",
                color="red",
                variant="light",
                title="Não foi possível salvar",
                icon=DashIconify(icon="akar-icons:triangle-alert"),
            )
            return no_update, feedback

        role.pages = []
        if selected_page_ids_str:
            for page_id in selected_page_ids_str:
                page = Page.query.get(int(page_id))
                if page:
                    role.pages.append(page)

        db.session.commit()

        feedback = dmc.Alert(
            f"Permissões salvas com sucesso para o perfil {role.description or get_role_label(role.name)}.",
            color="green",
            variant="light",
            title="Alterações salvas",
            icon=DashIconify(icon="akar-icons:check"),
        )
        return "", feedback
    except Exception:
        db.session.rollback()
        feedback = dmc.Alert(
            get_safe_database_error_message(),
            color="red",
            variant="light",
            title="Erro ao salvar",
            icon=DashIconify(icon="akar-icons:triangle-alert"),
        )
        return no_update, feedback
