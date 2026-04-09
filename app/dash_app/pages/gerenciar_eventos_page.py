import dash
from dash import dcc, html, callback, dash_table, no_update
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from datetime import datetime
from flask_login import current_user

from app import db
from app.models import Event
# Certifique-se que o data_repository foi criado no passo anterior
from app.application.analytics import get_list_setores 

# --- Layout ---
layout = html.Div([
    dmc.Title('Gerenciar Eventos Operacionais', order=2),
    dmc.Text('Histórico de manutenções, paradas e mudanças de padrão.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Grid(
        gutter="md",
        children=[
            # --- Coluna 1: Formulário (Só Gestão vê) ---
            dmc.GridCol([
                dmc.Card([
                    dmc.Text("Novo Evento", size="lg", fw=500, mb="sm"),
                    
                    # Título
                    dmc.TextInput(
                        label="Título do Evento",
                        placeholder="Ex: Manutenção da Balança",
                        id="evt-title",
                        mb="sm"
                    ),
                    
                    # Tipo
                    dmc.Select(
                        label="Tipo",
                        id="evt-type",
                        data=[
                            {'label': 'Manutenção Técnica', 'value': 'Manutenção'},
                            {'label': 'Mudança de Escala', 'value': 'Escala'},
                            {'label': 'Feriado/Parada', 'value': 'Parada'},
                            {'label': 'Outro', 'value': 'Outro'}
                        ],
                        value='Manutenção',
                        mb="sm"
                    ),

                    # Data
                    dmc.DatePickerInput(
                        type="range",
                        label="Período (Início e Fim)",
                        placeholder="Selecione as datas",
                        id='evt-date-range',
                        valueFormat="DD/MM/YYYY",
                        mb="sm",
                        clearable=True
                    ),
                    
                    # Setores Afetados (Multi-Select)
                    dmc.Group([
                        dmc.Text("Setores Afetados", size="sm", fw=500),
                        dmc.Button("Todos", id="btn-all-sectors", variant="subtle", size="compact-xs"),
                    ], justify="space-between", mb=5),
                    
                    dmc.MultiSelect(
                        id="evt-sectors",
                        placeholder="Selecione um ou mais setores...",
                        data=[], 
                        className="mb-3",
                        searchable=True,
                        nothingFoundMessage="Nenhum setor encontrado",
                        maxValues=50,
                    ),

                    # Descrição
                    dmc.Textarea(
                        label="Descrição/Observações",
                        placeholder="Detalhes adicionais...",
                        id="evt-desc",
                        minRows=3,
                        mb="md"
                    ),

                    # Botão Salvar
                    dmc.Button(
                        "Salvar Evento", 
                        id="btn-save-event", 
                        color="green", 
                        fullWidth=True,
                        leftSection=DashIconify(icon="fluent:save-24-regular")
                    ),
                ], withBorder=True, shadow="sm", radius="md")
            ], span={"base": 12, "md": 4}, id="col-form-event"),

            # --- Coluna 2: Lista de Eventos (Todos veem) ---
            dmc.GridCol([
                dmc.Card([
                    dmc.Text("Histórico de Eventos", size="lg", fw=500, mb="sm"),
                    
                    dmc.ScrollArea(
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
                            style_table={'minWidth': '100%'},
                            style_header={
                                "backgroundColor": "#f8f9fa", 
                                "color": "#000", 
                                "fontWeight": "bold", 
                                "fontFamily": "sans-serif"
                            },
                            style_data={
                                "backgroundColor": "#fff", 
                                "color": "#000",
                                "fontFamily": "sans-serif",
                                "whiteSpace": "normal",
                                "height": "auto",
                            },
                            style_cell={'border': '1px solid #dee2e6', 'padding': '10px', 'textAlign': 'left'},
                            page_size=10
                        ),
                        offsetScrollbars=True,
                        type="auto"
                    ),
                    
                    dmc.Group([
                        dmc.Button(
                            "Excluir Selecionado", 
                            id="btn-delete-event", 
                            color="red", 
                            variant="outline", 
                            size="sm", 
                            disabled=True,
                            leftSection=DashIconify(icon="fluent:delete-24-regular")
                        ),
                    ], id="div-btn-delete", mt="md"),
                    
                    html.Div(id="evt-msg-output", className="mt-2")
                ], withBorder=True, shadow="sm", radius="md", style={"height": "100%"})
            ], span={"base": 12, "md": 8}, id="col-list-event")
        ]
    )
])

# --- Callbacks ---

# 1. Controla Visibilidade por Role (Gestão vs Outros)
@callback(
    [Output('col-form-event', 'style'),
     Output('col-list-event', 'span'),
     Output('div-btn-delete', 'style')],
    Input('url', 'pathname')
)
def update_layout_by_role(pathname):
    if not current_user.is_authenticated:
         return {'display': 'none'}, {"base": 12, "md": 12}, {'display': 'none'}

    role = current_user.role
    if role in ['gestao', 'superadmin']:
        return {'display': 'block'}, {"base": 12, "md": 8}, {'display': 'block'}
    else:
        return {'display': 'none'}, {"base": 12, "md": 12}, {'display': 'none'}

# 2. Carregar Setores + Lógica do botão "Todos"
@callback(
    Output('evt-sectors', 'data'),
    Output('evt-sectors', 'value'), # Atualiza o valor selecionado
    Input('url', 'pathname'),
    Input('btn-all-sectors', 'n_clicks'),
    State('evt-sectors', 'data'),
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
                # print("DEBUG: Buscando lista de setores no banco...")
                lista = get_list_setores() 
                # print(f"DEBUG: Setores encontrados: {lista}")
                
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
     Output('evt-date-range', 'value'),
     Output('evt-sectors', 'value', allow_duplicate=True)],
    [Input('url', 'pathname'),
     Input('btn-save-event', 'n_clicks'),
     Input('btn-delete-event', 'n_clicks')],
    [State('evt-title', 'value'),
     State('evt-type', 'value'),
     State('evt-date-range', 'value'),
     State('evt-sectors', 'value'),
     State('evt-desc', 'value'),
     State('table-events', 'selected_rows'),
     State('table-events', 'data'),
     State('evt-sectors', 'data')],
    prevent_initial_call=True
)
def manage_events(pathname, n_save, n_delete, title, etype, date_range, sectors, desc, selected_rows, rows, sectors_opts):
    msg = ""
    user_can_edit = current_user.is_authenticated and current_user.role in ['gestao', 'superadmin']
    
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'init'

    # Default returns (no change)
    ret_title = no_update
    ret_desc = no_update
    ret_type = no_update
    ret_daterange = no_update
    ret_sectors = no_update
    
    # SALVAR
    if trigger_id == 'btn-save-event' and user_can_edit:
        # date_range is [start, end]
        if not title or not date_range or len(date_range) != 2:
            msg = dmc.Alert("Preencha Título e Datas.", color="yellow", variant="filled")
        else:
            try:
                start_date_str = date_range[0]
                end_date_str = date_range[1]

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
                     msg = dmc.Alert(f"Muitos setores selecionados ({len(sectors_str)} caracteres). Limite 255.", color="red", variant="filled")
                else:
                    new_event = Event(
                        title=title,
                        event_type=etype,
                        start_date=datetime.strptime(start_date_str.split('T')[0], '%Y-%m-%d'),
                        end_date=datetime.strptime(end_date_str.split('T')[0], '%Y-%m-%d'),
                        affected_sectors=sectors_str,
                        description=desc
                    )
                    db.session.add(new_event)
                    db.session.commit()
                    msg = dmc.Alert("Evento criado com sucesso!", color="green", variant="filled")
                    
                    # Clear Form
                    ret_title = ""
                    ret_desc = ""
                    ret_type = "Manutenção" # Default
                    ret_daterange = None
                    ret_sectors = []

            except Exception as e:
                db.session.rollback()
                msg = dmc.Alert(f"Erro ao salvar: {e}", color="red", variant="filled")

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
                    msg = dmc.Alert("Evento excluído.", color="green", variant="filled")
        except Exception as e:
            msg = dmc.Alert(f"Erro ao excluir: {e}", color="red", variant="filled")

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

    return events_data, msg, btn_disabled, ret_title, ret_desc, ret_type, ret_daterange, ret_sectors

@callback(
    Output('btn-delete-event', 'disabled', allow_duplicate=True),
    Input('table-events', 'selected_rows'),
    prevent_initial_call=True
)
def toggle_delete(selected_rows):
    return not selected_rows
