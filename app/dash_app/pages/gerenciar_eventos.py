import dash
from dash import dcc, html, callback, dash_table, no_update
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime
from flask_login import current_user

from app import db
from app.models import Event
# Certifique-se que o data_repository foi criado no passo anterior
from app.services.data_repository import get_list_setores 

# --- Layout ---
layout = html.Div([
    html.H1('Eventos e Ocorrências'),
    html.P('Histórico de manutenções, paradas e mudanças de padrão.'),
    html.Hr(),

    dbc.Row([
        # --- Coluna 1: Formulário (Só Gestão vê) ---
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Novo Evento"),
                dbc.CardBody([
                    # Título
                    html.Label("Título do Evento:", className="fw-bold"),
                    dbc.Input(id="evt-title", placeholder="Ex: Manutenção da Balança", className="mb-3"),
                    
                    # Tipo
                    html.Label("Tipo:", className="fw-bold"),
                    dcc.Dropdown(
                        id="evt-type",
                        options=[
                            {'label': 'Manutenção Técnica', 'value': 'Manutenção'},
                            {'label': 'Mudança de Escala', 'value': 'Escala'},
                            {'label': 'Feriado/Parada', 'value': 'Parada'},
                            {'label': 'Outro', 'value': 'Outro'}
                        ],
                        value='Manutenção',
                        className="mb-3",
                        style={'color': 'black'}
                    ),

                    # Data
                    html.Label("Período (Início e Fim):", className="fw-bold"),
                    dcc.DatePickerRange(
                        id='evt-date-range',
                        display_format='DD/MM/YYYY',
                        start_date_placeholder_text="Início",
                        end_date_placeholder_text="Fim",
                        className="mb-3 d-block",
                    ),
                    
                    # Setores Afetados (Multi-Select)
                    html.Div([
                        html.Label("Setores Afetados:", className="fw-bold mt-2"),
                        # Botão pequeno para selecionar todos
                        dbc.Button("Todos", id="btn-all-sectors", size="sm", color="link", className="p-0 ms-2"),
                    ], className="d-flex align-items-center"),
                    
                    dcc.Dropdown(
                        id="evt-sectors",
                        placeholder="Selecione um ou mais setores...",
                        multi=True, # <--- PERMITE MÚLTIPLOS
                        className="mb-3",
                        style={'color': 'black'}
                    ),

                    # Descrição
                    html.Label("Descrição/Observações:", className="fw-bold"),
                    dbc.Textarea(id="evt-desc", placeholder="Detalhes adicionais...", className="mb-3"),

                    # Botão Salvar
                    dbc.Button("Salvar Evento", id="btn-save-event", color="success", className="w-100")
                ])
            ], className="dbc h-100")
        ], md=4, id="col-form-event"),

        # --- Coluna 2: Lista de Eventos (Todos veem) ---
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Histórico de Eventos"),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='table-events',
                        columns=[
                            {'name': 'Data Início', 'id': 'start'},
                            {'name': 'Data Fim', 'id': 'end'},
                            {'name': 'Título', 'id': 'title'},
                            {'name': 'Tipo', 'id': 'type'},
                            {'name': 'Setores Afetados', 'id': 'sectors'},
                        ],
                        data=[],
                        row_selectable='single',
                        style_table={'overflowX': 'auto'},
                        style_header={
                            "backgroundColor": "var(--bs-tertiary-bg)",
                            "color": "var(--bs-body-color)",
                            "fontWeight": "bold"
                        },
                        style_data={
                            "backgroundColor": "var(--bs-body-bg)",
                            "color": "var(--bs-body-color)",
                            "whiteSpace": "normal",
                            "height": "auto",
                        },
                        page_size=10
                    ),
                    
                    html.Div([
                        dbc.Button("Excluir Selecionado", id="btn-delete-event", color="danger", size="sm", className="mt-2", disabled=True),
                    ], id="div-btn-delete"),
                    
                    html.Div(id="evt-msg-output", className="mt-2")
                ])
            ], className="dbc h-100")
        ], md=8, id="col-list-event")
    ])
])

# --- Callbacks ---

# 1. Controla Visibilidade por Role (Gestão vs Outros)
@callback(
    [Output('col-form-event', 'style'),
     Output('col-list-event', 'md'),
     Output('div-btn-delete', 'style')],
    Input('url', 'pathname')
)
def update_layout_by_role(pathname):
    if not current_user.is_authenticated:
         return {'display': 'none'}, 12, {'display': 'none'}

    role = current_user.role
    if role in ['gestao', 'superadmin']:
        return {'display': 'block'}, 8, {'display': 'block'}
    else:
        return {'display': 'none'}, 12, {'display': 'none'}

# 2. Carregar Setores + Lógica do botão "Todos"
@callback(
    Output('evt-sectors', 'options'),
    Output('evt-sectors', 'value'), # Atualiza o valor selecionado
    Input('url', 'pathname'),
    Input('btn-all-sectors', 'n_clicks'),
    State('evt-sectors', 'options'),
)
def load_and_select_sectors(pathname, n_clicks, current_options):
    ctx = dash.callback_context
    
    # Determina quem disparou o callback
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'init'

    # Se for carregamento inicial ('init') ou navegação ('url')
    if trigger_id in ['init', 'url']:
        # Verifica se estamos na página certa
        if pathname == '/gerenciar-eventos':
            try:
                print("DEBUG: Buscando lista de setores no banco...")
                lista = get_list_setores() 
                print(f"DEBUG: Setores encontrados: {lista}")
                
                if not lista:
                    return [], no_update
                    
                options = [{'label': s, 'value': s} for s in lista]
                return options, no_update
            except Exception as e:
                print(f"DEBUG: Erro ao buscar setores: {e}")
                return [], no_update
        return no_update, no_update

    # Botão "Todos" clicado
    if trigger_id == 'btn-all-sectors' and current_options:
        all_values = [opt['value'] for opt in current_options]
        return no_update, all_values

    return no_update, no_update

# 3. Salvar, Excluir e Listar
@callback(
    [Output('table-events', 'data'),
     Output('evt-msg-output', 'children'),
     Output('btn-delete-event', 'disabled'),
     Output('evt-title', 'value'),
     Output('evt-desc', 'value'),
     Output('evt-type', 'value'),
     Output('evt-date-range', 'start_date'),
     Output('evt-date-range', 'end_date'),
     Output('evt-sectors', 'value', allow_duplicate=True)],
    [Input('url', 'pathname'),
     Input('btn-save-event', 'n_clicks'),
     Input('btn-delete-event', 'n_clicks')],
    [State('evt-title', 'value'),
     State('evt-type', 'value'),
     State('evt-date-range', 'start_date'),
     State('evt-date-range', 'end_date'),
     State('evt-sectors', 'value'),
     State('evt-desc', 'value'),
     State('table-events', 'selected_rows'),
     State('table-events', 'data'),
     State('evt-sectors', 'options')],
    prevent_initial_call=True
)
def manage_events(pathname, n_save, n_delete, title, etype, start, end, sectors, desc, selected_rows, rows, sectors_opts):
    msg = ""
    user_can_edit = current_user.is_authenticated and current_user.role in ['gestao', 'superadmin']
    
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'init'

    # Default returns (no change)
    ret_title = no_update
    ret_desc = no_update
    ret_type = no_update
    ret_start = no_update
    ret_end = no_update
    ret_sectors = no_update
    
    # SALVAR
    if trigger_id == 'btn-save-event' and user_can_edit:
        if not title or not start or not end:
            msg = dbc.Alert("Preencha Título e Datas.", color="warning", dismissable=True)
        else:
            try:
                 # Check logic: All Selected?
                is_all_selected = False
                total_opts = len(sectors_opts) if sectors_opts else 0
                selected_qty = len(sectors) if sectors else 0
                
                if selected_qty > 0 and selected_qty == total_opts:
                    is_all_selected = True

                if not sectors or is_all_selected:
                    sectors_str = "Geral (Todos)"
                else:
                    sectors_str = ", ".join(sectors)
                
                if len(sectors_str) > 255:
                     msg = dbc.Alert(f"Muitos setores selecionados ({len(sectors_str)} caracteres). Limite 255.", color="danger", dismissable=True)
                else:
                    new_event = Event(
                        title=title,
                        event_type=etype,
                        start_date=datetime.strptime(start.split('T')[0], '%Y-%m-%d'),
                        end_date=datetime.strptime(end.split('T')[0], '%Y-%m-%d'),
                        affected_sectors=sectors_str,
                        description=desc
                    )
                    db.session.add(new_event)
                    db.session.commit()
                    msg = dbc.Alert("Evento criado com sucesso!", color="success", dismissable=True)
                    
                    # Clear Form
                    ret_title = ""
                    ret_desc = ""
                    ret_type = "Manutenção" # Default
                    ret_start = None
                    ret_end = None
                    ret_sectors = []

            except Exception as e:
                db.session.rollback()
                msg = dbc.Alert(f"Erro ao salvar: {e}", color="danger")

    # EXCLUIR
    if trigger_id == 'btn-delete-event' and selected_rows and user_can_edit:
        try:
            row_data = rows[selected_rows[0]]
            evt_id = row_data.get('id')
            if evt_id:
                event_to_del = Event.query.get(evt_id)
                if event_to_del:
                    db.session.delete(event_to_del)
                    db.session.commit()
                    msg = dbc.Alert("Evento excluído.", color="success", dismissable=True)
        except Exception as e:
            msg = dbc.Alert(f"Erro ao excluir: {e}", color="danger")

    # LISTAR (Sempre recarrega a tabela para refletir mudanças)
    events_data = []
    try:
        events = Event.query.order_by(Event.start_date.desc()).all()
        for e in events:
            events_data.append({
                'id': e.id,
                'title': e.title,
                'type': e.event_type,
                'start': e.start_date.strftime('%d/%m/%Y'),
                'end': e.end_date.strftime('%d/%m/%Y'),
                'sectors': e.affected_sectors or "Geral"
            })
    except:
        pass

    btn_disabled = True 

    return events_data, msg, btn_disabled, ret_title, ret_desc, ret_type, ret_start, ret_end, ret_sectors

@callback(
    Output('btn-delete-event', 'disabled', allow_duplicate=True),
    Input('table-events', 'selected_rows'),
    prevent_initial_call=True
)
def toggle_delete(selected_rows):
    return not selected_rows