import os
import base64
import threading
import subprocess
import sys
from dash import dcc, html, callback, dash_table, no_update, callback_context
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

SHEETS_FOLDER = 'sheets'
SCRIPT_NAME = 'import_sheet.py'

ETL_STATUS = {
    'is_running': False,
    'message': '',
    'color': 'light'
}

def run_import_script_thread():
    global ETL_STATUS
    ETL_STATUS['is_running'] = True
    ETL_STATUS['message'] = "O script de importação está rodando... Isso pode levar alguns minutos."
    ETL_STATUS['color'] = "info"
    
    try:
        
        result = subprocess.run(
            [sys.executable, SCRIPT_NAME], 
            capture_output=True, 
            text=True, 
            cwd=os.getcwd() 
        )
        
        if result.returncode == 0:
            ETL_STATUS['message'] = f"Sucesso! Importação concluída..." 
            ETL_STATUS['color'] = "success"
        else:
            ETL_STATUS['message'] = f"Erro na execução:\n{result.stderr}"
            ETL_STATUS['color'] = "danger"
            
    except Exception as e:
        ETL_STATUS['message'] = f"Erro crítico ao tentar rodar o script: {str(e)}"
        ETL_STATUS['color'] = "danger"
    
    finally:
        ETL_STATUS['is_running'] = False

def listar_arquivos():
    # Letura dos arquivos na pasta
    if not os.path.exists(SHEETS_FOLDER):
        try:
            os.makedirs(SHEETS_FOLDER)
        except OSError:
            return []
        
    arquivos = []
    try:
        for f in os.listdir(SHEETS_FOLDER):
            if f.endswith('.ods') and not f.startswith('~'): 
                caminho = os.path.join(SHEETS_FOLDER, f)
                try:
                    tamanho = os.path.getsize(caminho) / 1024 
                    arquivos.append({'filename': f, 'size': f"{tamanho:.2f} KB"})
                except OSError:
                    continue
    except Exception as e:
        print(f"Erro ao listar arquivos: {e}")
        return []
    
    return sorted(arquivos, key=lambda x: x['filename'])

layout = html.Div([
    html.H1('Gerenciamento de Arquivos e Dados'),
    html.P('Faça upload de planilhas e processe os dados para atualizar o dashboard.'),
    html.Hr(),
    
    dbc.Card([
        dbc.CardHeader("Processamento de Dados (ETL)"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.P("Após adicionar ou remover arquivos na lista abaixo, clique no botão para processar os dados e atualizar o banco de dados."),
                    dbc.Button(
                        [
                            html.I(className="bi bi-database-gear me-2"), 
                            "Rodar Script de Importação"
                        ], 
                        id="btn-run-etl", 
                        color="primary", 
                        className="mb-3",
                        disabled=False
                    ),
                ], md=8),
                dbc.Col([
                    # Spinner e Status
                    dcc.Loading(
                        id="loading-etl",
                        type="default",
                        children=html.Div(id="dummy-loading-output")
                    )
                ], md=4, className="d-flex align-items-center justify-content-center")
            ]),
            
            # Alerta de Status
            dbc.Alert(
                id="alert-etl-status",
                children="Aguardando comando...",
                color="light",
                is_open=True,
                style={'whiteSpace': 'pre-wrap'}
            ),
            
            # Intervalo para verificar o status a cada 2 segundos
            dcc.Interval(id='interval-etl-status', interval=2000, n_intervals=0, disabled=True)
        ])
    ], className="mb-4 dbc"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Upload de Novo Arquivo"),
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            html.I(className="bi bi-cloud-upload fs-1 text-primary"),
                            html.Br(),
                            html.Span('Arraste ou Clique para Selecionar', className="fw-bold"),
                            html.Br(),
                            html.Small('Apenas arquivos .ods', className="text-muted")
                        ]),
                        style={
                            'width': '100%', 'height': '150px', 'lineHeight': '30px',
                            'borderWidth': '2px', 'borderStyle': 'dashed',
                            'borderRadius': '10px', 'textAlign': 'center',
                            'borderColor': 'var(--bs-border-color)',
                            'cursor': 'pointer',
                            'display': 'flex', 'flexDirection': 'column', 
                            'justifyContent': 'center', 'alignItems': 'center'
                        },
                        multiple=False 
                    ),
                    html.Div(id='output-upload-status', className="mt-3")
                ])
            ], className="h-100 dbc") 
        ], md=5),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    "Arquivos no Servidor",
                    dbc.Button(html.I(className="bi bi-arrow-clockwise"), id="btn-refresh-files", color="light", size="sm", className="float-end")
                ]),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='tabela-arquivos',
                        columns=[
                            {'name': 'Nome do Arquivo', 'id': 'filename'},
                            {'name': 'Tamanho', 'id': 'size'},
                        ],
                        data=[],
                        row_selectable='single', 
                        style_table={'overflowX': 'auto'},
                        style_header={
                            "backgroundColor": "var(--bs-tertiary-bg)",
                            "color": "var(--bs-body-color)",
                            "fontWeight": "bold",
                            "border": "1px solid var(--bs-border-color)"
                        },
                        style_data={
                            "backgroundColor": "var(--bs-body-bg)",
                            "color": "var(--bs-body-color)",
                            "border": "1px solid var(--bs-border-color)"
                        },
                        style_cell={'textAlign': 'left', 'padding': '10px'},
                    ),
                    
                    dbc.Button(
                        [html.I(className="bi bi-trash me-2"), "Excluir Selecionado"], 
                        id="btn-delete-file-init", 
                        color="danger", 
                        className="mt-3 w-100", 
                        disabled=True
                    )
                ])
            ], className="h-100 dbc")
        ], md=7),
    ]),

    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Confirmar Exclusão")),
            dbc.ModalBody(id="modal-body-delete"),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancelar", id="btn-cancel-delete", className="ms-auto", n_clicks=0),
                    dbc.Button("Sim, Excluir", id="btn-confirm-delete", color="danger", n_clicks=0),
                ]
            ),
        ],
        id="modal-confirm-delete",
        is_open=False,
    ),
    
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
    return listar_arquivos()

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
    if not filename.lower().endswith('.ods'):
        return dbc.Alert("Erro: Apenas arquivos .ods permitidos.", color="danger", dismissable=True)
    caminho = os.path.join(SHEETS_FOLDER, filename)
    if os.path.exists(caminho):
        return dbc.Alert(
            [html.I(className="bi bi-exclamation-octagon-fill me-2"), f"O arquivo '{filename}' já existe. Exclua-o da lista ao lado antes de enviar novamente."], 
            color="danger", dismissable=True
        )
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        with open(caminho, 'wb') as f:
            f.write(decoded)
        return dbc.Alert(f"Sucesso: '{filename}' enviado.", color="success", dismissable=True)
    except Exception as e:
        return dbc.Alert(f"Erro ao salvar: {str(e)}", color="danger", dismissable=True)

@callback(
    [Output('modal-confirm-delete', 'is_open'),
     Output('modal-body-delete', 'children'),
     Output('store-file-to-delete', 'data')],
    [Input('btn-delete-file-init', 'n_clicks'),
     Input('btn-cancel-delete', 'n_clicks'),
     Input('btn-confirm-delete', 'n_clicks')],
    [State('modal-confirm-delete', 'is_open'),
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
    
    return False, no_update, no_update

@callback(
    Output('dummy-delete-output', 'children'),
    Input('btn-confirm-delete', 'n_clicks'),
    State('store-file-to-delete', 'data'),
    prevent_initial_call=True
)
def delete_file_action(n_clicks, filename):
    if not filename:
        return no_update
    caminho = os.path.join(SHEETS_FOLDER, filename)
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
            return "deleted"
    except Exception as e:
        print(f"Erro ao deletar: {e}")
        pass
    return no_update



@callback(
    [Output('interval-etl-status', 'disabled'),
     Output('btn-run-etl', 'disabled'),
     Output('dummy-loading-output', 'children')],
    Input('btn-run-etl', 'n_clicks'),
    prevent_initial_call=True
)
def start_etl(n_clicks):
    if ETL_STATUS['is_running']:
        return no_update, True, "" 
    
    # Inicia a thread
    thread = threading.Thread(target=run_import_script_thread)
    thread.start()
    
    # Ativa o intervalo (disabled=False), Desativa o botão
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
    # Lê o estado global
    status = ETL_STATUS['is_running']
    message = ETL_STATUS['message']
    color = ETL_STATUS['color']
    
    if status:
        # Ainda rodando: mantém intervalo ligado, botão desligado
        return message, color, False, True
    else:
        # Terminou: desliga intervalo, liga botão
        return message, color, True, False