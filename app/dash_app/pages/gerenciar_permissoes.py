from dash import dcc, html, callback, no_update
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from app import db
from app.models import Role, Page

def get_roles_options():
    try:
        roles = Role.query.filter(Role.name != 'superadmin').all() # NÀO MEXER AQUI SOB NENHUMA CIRCUNSTÂNCIA, REPITO, NENHUMA!
        return [{'label': r.name.capitalize(), 'value': r.id} for r in roles]
    except Exception:
        return []

def get_pages_options():
    try:
        hidden_routes = ['/gerenciar-permissoes', '/gerenciar-arquivos']
        
        pages = Page.query.filter(
            ~Page.route.in_(hidden_routes) 
        ).order_by(Page.route).all()
        
        return [{'label': f"{p.description} ({p.route})", 'value': p.id} for p in pages]
    except Exception:
        return []

layout = html.Div([
    html.H1('Gerenciamento de Permissões'),
    html.P('Controle dinâmico de acesso. Selecione uma função e defina o que ela pode ver.'),
    html.Hr(),
    
    dbc.Alert(
        [
            html.I(className="bi bi-exclamation-triangle-fill me-2"),
            "Atenção: Alterações aqui afetam imediatamente o acesso dos usuários daquela função."
        ],
        color="warning", className="mb-4"
    ),

    dbc.Card([
        dbc.CardHeader("Configuração de Acesso"),
        dbc.CardBody([
            
            html.Label("1. Selecione a Função (Role) para editar:", className="fw-bold mb-2"),
            dcc.Dropdown(
                id='perm-role-select',
                options=get_roles_options(),
                placeholder="Selecione uma função...",
                className="mb-4",
                style={'color': 'black'} 
            ),
            
            html.Label("2. Marque as páginas permitidas:", className="fw-bold mb-2"),
            
            dbc.Card(
                dbc.CardBody(
                    dcc.Loading(
                        dbc.Checklist(
                            id='perm-page-checklist',
                            options=get_pages_options(),
                            value=[],
                            switch=True, 
                            inline=False,
                            label_style={"color": "var(--bs-body-color)"},
                        )
                    )
                ),
                className="mb-3 border" 
            ),
            
            dbc.Button(
                [html.I(className="bi bi-save me-2"), "Salvar Permissões"],
                id="btn-save-perms", 
                color="success", 
                className="mt-2",
                disabled=True
            ),
            
            html.Div(id='output-save-perms', className="mt-3")
        ])
    ], className="dbc") 
])



@callback(
    [Output('perm-page-checklist', 'value'),
     Output('btn-save-perms', 'disabled')],
    Input('perm-role-select', 'value')
)
def load_role_permissions(role_id):
    if not role_id:
        return [], True
    try:
        role = Role.query.get(role_id)
        if not role:
            return [], True
        page_ids = [page.id for page in role.pages]
        return page_ids, False
    except Exception as e:
        return [], True

@callback(
    Output('output-save-perms', 'children'),
    Input('btn-save-perms', 'n_clicks'),
    [State('perm-role-select', 'value'),
     State('perm-page-checklist', 'value')],
    prevent_initial_call=True
)
def save_permissions(n_clicks, role_id, selected_page_ids):
    if not role_id or selected_page_ids is None:
        return dbc.Alert("Erro: Seleção inválida.", color="danger")
    try:
        role = Role.query.get(role_id)
        role.pages.clear()
        
        if selected_page_ids:
            new_pages = Page.query.filter(Page.id.in_(selected_page_ids)).all()
            role.pages.extend(new_pages)
        
        db.session.commit()
        return dbc.Alert(f"Sucesso! Permissões atualizadas para '{role.name}'.", color="success", dismissable=True)
    except Exception as e:
        db.session.rollback()
        return dbc.Alert(f"Erro ao salvar: {e}", color="danger")