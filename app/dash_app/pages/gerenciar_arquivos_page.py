from dash import dcc, html, callback, dash_table, no_update, callback_context
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from app.application.file_management import build_default_file_management_service

file_management = build_default_file_management_service()

layout = html.Div([
    dmc.Title('Gerenciamento de Arquivos e Dados', order=2),
    dmc.Text('Faça upload de planilhas e processe os dados para atualizar o dashboard.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),
    
    dmc.Card([
        dmc.Text("Processamento de Dados (ETL)", size="lg", fw=500, mb="sm"),
        
        dmc.Grid(
            gutter="md",
            children=[
                dmc.GridCol([
                    dmc.Text("Após adicionar ou remover arquivos na lista abaixo, clique no botão para processar os dados e atualizar o banco de dados.", size="sm", mb="md"),
                    dmc.Button(
                        "Rodar Script de Importação",
                        id="btn-run-etl", 
                        color="indigo", 
                        leftSection=DashIconify(icon="akar-icons:database"),
                        disabled=False
                    ),
                ], span={"base": 12, "md": 8}),
                dmc.GridCol([
                    # Spinner e Status
                    dcc.Loading(
                        id="loading-etl",
                        type="default",
                        children=html.Div(id="dummy-loading-output")
                    )
                ], span={"base": 12, "md": 4}, style={"display": "flex", "alignItems": "center", "justifyContent": "center"})
            ]
        ),
        
        # Alerta de Status
        dmc.Alert(
            id="alert-etl-status",
            children="Aguardando comando...",
            color="gray",
            variant="filled", 
            mt="md",
            style={'whiteSpace': 'pre-wrap'}
        ),
        
        # Intervalo para verificar o status a cada 2 segundos
        dcc.Interval(id='interval-etl-status', interval=2000, n_intervals=0, disabled=True)
    ], withBorder=True, shadow="sm", radius="md", mb="md"),

    dmc.Grid(
        gutter="md",
        children=[
            dmc.GridCol([
                dmc.Card([
                    dmc.Text("Upload de Novo Arquivo", size="lg", fw=500, mb="sm"),
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            DashIconify(icon="bi:cloud-upload", width=40, height=40),
                            html.Br(),
                            dmc.Text('Arraste ou Clique para Selecionar', fw=700),
                            dmc.Text('Apenas arquivos .ods', c="dimmed", size="xs")
                        ]),
                        style={
                            'width': '100%', 'height': '150px', 'lineHeight': '30px',
                            'borderWidth': '2px', 'borderStyle': 'dashed',
                            'borderRadius': '10px', 'textAlign': 'center',
                            'borderColor': '#e9ecef',
                            'cursor': 'pointer',
                            'display': 'flex', 'flexDirection': 'column', 
                            'justifyContent': 'center', 'alignItems': 'center'
                        },
                        multiple=False 
                    ),
                    html.Div(id='output-upload-status', className="mt-3")
                ], withBorder=True, shadow="sm", radius="md", style={"height": "100%"}) 
            ], span={"base": 12, "md": 5}),

            dmc.GridCol([
                dmc.Card([
                    dmc.Group([
                        dmc.Text("Arquivos no Servidor", size="lg", fw=500),
                        dmc.Button(
                            "Atualizar Lista",
                            id="btn-refresh-files",
                            variant="subtle",
                            color="gray",
                            size="sm",
                            leftSection=DashIconify(icon="fluent:arrow-clockwise-24-regular")
                        )
                    ], justify="space-between", mb="sm"),
                    
                    dmc.ScrollArea(
                        dash_table.DataTable(
                            id='tabela-arquivos',
                            columns=[
                                {'name': 'Nome do Arquivo', 'id': 'filename'},
                                {'name': 'Tamanho', 'id': 'size'},
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
                                "fontFamily": "sans-serif"
                            },
                            style_cell={'textAlign': 'left', 'padding': '10px', 'border': '1px solid #dee2e6'},
                        ),
                        offsetScrollbars=True,
                        type="auto"
                    ),
                    
                    dmc.Button(
                        "Excluir Selecionado", 
                        id="btn-delete-file-init", 
                        color="red", 
                        variant="outline",
                        fullWidth=True,
                        mt="md",
                        disabled=True,
                        leftSection=DashIconify(icon="fluent:delete-24-regular")
                    )
                ], withBorder=True, shadow="sm", radius="md", style={"height": "100%"})
            ], span={"base": 12, "md": 7}),
        ]
    ),

    dmc.Modal(
        id="modal-confirm-delete",
        centered=True,
        children=[
            dmc.Text("Confirmar Exclusão", fw=700, size="lg", mb="md"),
            dmc.Text(id="modal-body-delete", mb="md"),
            dmc.Group(
                [
                    dmc.Button("Cancelar", id="btn-cancel-delete", variant="outline", color="gray", n_clicks=0),
                    dmc.Button("Sim, Excluir", id="btn-confirm-delete", color="red", n_clicks=0),
                ],
                justify="flex-end"
            )
        ]
    ),

    dmc.Card([
        dmc.Group([
            dmc.Text("Histórico de Importações", size="lg", fw=500),
            dmc.Text("Últimas 20 execuções", c="dimmed", size="sm")
        ], justify="space-between", mb="sm"),

        dash_table.DataTable(
            id='tabela-import-auditoria',
            columns=[
                {'name': 'ID', 'id': 'id'},
                {'name': 'Início', 'id': 'started_at'},
                {'name': 'Fim', 'id': 'finished_at'},
                {'name': 'Status', 'id': 'status'},
                {'name': 'Arquivos', 'id': 'files_count'},
                {'name': 'Lidas', 'id': 'rows_read'},
                {'name': 'Válidas', 'id': 'rows_valid'},
                {'name': 'Novas', 'id': 'rows_new'},
                {'name': 'Atualizadas', 'id': 'rows_updated'},
                {'name': 'Erro', 'id': 'error_message'},
            ],
            data=[],
            style_table={'overflowX': 'auto'},
            style_header={
                "backgroundColor": "#f8f9fa",
                "color": "#000",
                "fontWeight": "bold",
                "fontFamily": "sans-serif"
            },
            style_data={
                "backgroundColor": "#fff",
                "color": "#000",
                "fontFamily": "sans-serif"
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'status'},
                    'fontWeight': 'bold',
                    'textTransform': 'uppercase'
                },
                {
                    'if': {'filter_query': '{status} = "success"', 'column_id': 'status'},
                    'backgroundColor': '#d3f9d8',
                    'color': '#2b8a3e'
                },
                {
                    'if': {'filter_query': '{status} = "error"', 'column_id': 'status'},
                    'backgroundColor': '#ffe3e3',
                    'color': '#c92a2a'
                },
                {
                    'if': {'filter_query': '{status} = "running"', 'column_id': 'status'},
                    'backgroundColor': '#dbe4ff',
                    'color': '#364fc7'
                },
            ],
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'border': '1px solid #dee2e6',
                'minWidth': '120px',
                'maxWidth': '350px',
                'whiteSpace': 'normal'
            },
            page_size=10,
        )
    ], withBorder=True, shadow="sm", radius="md", mt="md"),
    
    dcc.Store(id='store-file-to-delete'),
    html.Div(id='dummy-delete-output')
])


@callback(
    Output('tabela-arquivos', 'data'),
    [Input('url', 'pathname'),
     Input('btn-refresh-files', 'n_clicks'),
     Input('output-upload-status', 'children'),
     Input('dummy-delete-output', 'children')]
)
def update_file_list(pathname, n_refresh, upload_trigger, delete_trigger):
    return file_management.list_files()


@callback(
    Output('tabela-import-auditoria', 'data'),
    [Input('url', 'pathname'),
     Input('btn-refresh-files', 'n_clicks'),
     Input('interval-etl-status', 'n_intervals')]
)
def update_import_audit_table(pathname, n_refresh, n_intervals):
    return file_management.list_import_audit()

@callback(
    Output('btn-delete-file-init', 'disabled'),
    Input('tabela-arquivos', 'selected_rows')
)
def toggle_delete_btn(selected_rows):
    return not selected_rows

@callback(
    Output('output-upload-status', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def upload_file(contents, filename):
    if contents is None:
        return None

    success, message = file_management.save_uploaded_file(contents, filename)
    if success:
        return dmc.Alert(message, color="green", variant="filled")

    if 'ja existe' in message.lower() or 'já existe' in message.lower():
        return dmc.Alert(
            message,
            title="Arquivo Duplicado",
            color="red", 
            variant="filled",
            icon=DashIconify(icon="akar-icons:triangle-alert")
        )

    return dmc.Alert(message, color="red", variant="filled")

@callback(
    [Output('modal-confirm-delete', 'opened'),
     Output('modal-body-delete', 'children'),
     Output('store-file-to-delete', 'data')],
    [Input('btn-delete-file-init', 'n_clicks'),
     Input('btn-cancel-delete', 'n_clicks'),
     Input('btn-confirm-delete', 'n_clicks')],
    [State('modal-confirm-delete', 'opened'),
     State('tabela-arquivos', 'selected_rows'),
     State('tabela-arquivos', 'data')]
)
def toggle_modal(n_init, n_cancel, n_confirm, is_open, selected_rows, rows):
    triggers = list(callback_context.triggered_prop_ids.keys())
    
    if not triggers:
        return False, no_update, no_update

    ctx = triggers[0]
    
    if 'btn-delete-file-init' in ctx and selected_rows:
        filename = rows[selected_rows[0]]['filename']
        msg = f"Tem certeza que deseja excluir permanentemente o arquivo '{filename}' do servidor?"
        return True, msg, filename
    
    if 'btn-cancel-delete' in ctx or 'btn-confirm-delete' in ctx:
        return False, no_update, no_update
    
    return False, no_update, no_update

@callback(
    Output('dummy-delete-output', 'children'),
    Input('btn-confirm-delete', 'n_clicks'),
    State('store-file-to-delete', 'data'),
    prevent_initial_call=True
)
def delete_file_action(n_clicks, filename):
    if file_management.delete_file(filename):
        return "deleted"
    return no_update



@callback(
    [Output('interval-etl-status', 'disabled'),
     Output('btn-run-etl', 'disabled'),
     Output('dummy-loading-output', 'children')],
    Input('btn-run-etl', 'n_clicks'),
    prevent_initial_call=True
)
def start_etl(n_clicks):
    started = file_management.start_etl_async()
    if not started:
        return no_update, True, "" 

    return False, True, "rodando"

# Monitora o progresso (a cada 2 segundos)
@callback(
    [Output('alert-etl-status', 'children'),
     Output('alert-etl-status', 'color'),
     Output('interval-etl-status', 'disabled', allow_duplicate=True),
     Output('btn-run-etl', 'disabled', allow_duplicate=True)],
    Input('interval-etl-status', 'n_intervals'),
    prevent_initial_call=True
)
def check_etl_status(n):
    status, message, color = file_management.get_etl_status()
    
    if status:
        # Ainda rodando: mantém intervalo ligado, botão desligado
        return message, color, False, True
    else:
        # Terminou: desliga intervalo, liga botão
        return message, color, True, False
