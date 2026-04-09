from dash import dcc, html, callback, no_update
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from app import db
from app.models import Role, Page
from app.services.error_messages import get_safe_database_error_message

def get_roles_options():
    try:
        roles = Role.query.filter(Role.name != 'superadmin').all() # NÀO MEXER AQUI SOB NENHUMA CIRCUNSTÂNCIA, REPITO, NENHUMA!
        return [{'label': r.name.capitalize(), 'value': str(r.id)} for r in roles] # dmc.Select requires string values
    except Exception:
        return []

def get_pages_options():
    try:
        hidden_routes = ['/gerenciar-permissoes', '/gerenciar-arquivos']
        
        pages = Page.query.filter(
            ~Page.route.in_(hidden_routes) 
        ).order_by(Page.route).all()
        
        return [{'label': f"{p.description} ({p.route})", 'value': str(p.id)} for p in pages] # dmc.CheckboxGroup values should be strings ideally
    except Exception:
        return []

layout = html.Div([
    dmc.Title('Gerenciamento de Permissões (RBAC)', order=2),
    dmc.Text('Controle dinâmico de acesso. Selecione uma função e defina o que ela pode ver.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Alert(
        "Atenção: Alterações aqui afetam imediatamente o acesso dos usuários daquela função.",
        title="Cuidado",
        color="yellow", 
        variant="filled",
        icon=DashIconify(icon="akar-icons:triangle-alert"),
        mb="md"
    ),

    dmc.Card([
        dmc.Text("Configuração de Acesso", size="lg", fw=500, mb="sm"),
        
        dmc.Select(
            label="1. Selecione a Função (Role) para editar:",
            placeholder="Selecione uma função...",
            id='perm-role-select',
            data=get_roles_options(), # Will be loaded dynamically if needed, but nice to have initial
            mb="md"
        ),
        
        dmc.Text("2. Marque as páginas permitidas:", size="sm", fw=500, mb="xs"),
        
        dmc.Card(
            children=[
                 dcc.Loading(
                    dmc.CheckboxGroup(
                        id='perm-page-checklist',
                        value=[],
                        children=dmc.Stack(
                            [dmc.Checkbox(label=opt['label'], value=opt['value']) for opt in get_pages_options()],
                            gap="sm"
                        )
                    )
                )
            ],
            withBorder=True,
            mb="md",
            p="md"
        ),
        
        dmc.Button(
            "Salvar Permissões",
            id="btn-save-perms",
            color="green",
            leftSection=DashIconify(icon="akar-icons:check"),
            fullWidth=True
        ),
        
        html.Div(id='dummy-save-perm-output')
        
    ], withBorder=True, shadow="sm", radius="md")
])

@callback(
    Output('perm-page-checklist', 'value'),
    Input('perm-role-select', 'value')
)
def load_role_permissions(role_id_str):
    if not role_id_str:
        return []
    
    try:
        role_id = int(role_id_str)
        role = Role.query.get(role_id)
        if not role:
            return []
        
        # Returns list of strings IDs
        return [str(page.id) for page in role.pages]
    except Exception:
        return []

@callback(
    Output('dummy-save-perm-output', 'children'),
    Input('btn-save-perms', 'n_clicks'),
    [State('perm-role-select', 'value'),
     State('perm-page-checklist', 'value')],
    prevent_initial_call=True
)
def save_permissions(n_clicks, role_id_str, selected_page_ids_str):
    if not role_id_str:
        return dmc.Notification(
            title="Erro",
            id="notify-error-select",
            action="show",
            message="Selecione uma função primeiro!",
            color="red",
        )
        
    try:
        role_id = int(role_id_str)
        role = Role.query.get(role_id)
        if not role:
            return dmc.Notification(
                title="Erro",
                id="notify-error-notfound",
                action="show",
                message="Função não encontrada",
                color="red",
            )

        # Clear existing
        role.pages = []
        
        # Add new
        if selected_page_ids_str:
            for pid_str in selected_page_ids_str:
                page = Page.query.get(int(pid_str))
                if page:
                    role.pages.append(page)
        
        db.session.commit()
        
        return dmc.Notification(
            title="Sucesso",
            id="notify-success",
            action="show",
            message=f"Permissões atualizadas para {role.name}!",
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
