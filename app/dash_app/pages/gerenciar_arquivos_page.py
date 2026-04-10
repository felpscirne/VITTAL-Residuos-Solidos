from dash import callback, callback_context, dash_table, dcc, html, no_update
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.file_management import build_default_file_management_service
from app.extensions import cache

file_management = build_default_file_management_service()


def _build_upload_feedback(saved, errors, processing_started):
    alerts = []
    if saved:
        alerts.append(
            dmc.Alert(
                f"Arquivos recebidos para importacao: {', '.join(saved)}",
                color="green",
                variant="filled",
                mb="sm",
            )
        )
    if processing_started:
        alerts.append(
            dmc.Alert(
                "Importacao iniciada. O status abaixo ja esta acompanhando a execucao em tempo real.",
                color="blue",
                variant="filled",
                mb="sm",
            )
        )
    if errors:
        alerts.append(
            dmc.Alert(
                html.Ul([html.Li(error) for error in errors]),
                title="Arquivos recusados",
                color="red",
                variant="filled",
                icon=DashIconify(icon="akar-icons:triangle-alert"),
            )
        )
    return alerts or None


layout = html.Div([
    dmc.Title('Gerenciamento de Arquivos e Dados', order=2),
    dmc.Text('Selecione arquivos, confira os pendentes e confirme a importacao. A base de testes pode ser reiniciada por esta tela.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Group(
        [
            dmc.Button(
                "Reiniciar Base de Testes",
                id="btn-reset-import-data",
                color="red",
                variant="outline",
                leftSection=DashIconify(icon="fluent:database-plug-connected-24-regular"),
            ),
        ],
        justify="flex-end",
        mb="md",
    ),

    dmc.Grid(
        gutter="md",
        children=[
            dmc.GridCol([
                dmc.Card([
                    dmc.Text("Selecao de Arquivos", size="lg", fw=500, mb="sm"),
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            DashIconify(icon="bi:cloud-upload", width=40, height=40),
                            html.Br(),
                            dmc.Text('Arraste ou Clique para Selecionar', fw=700),
                            dmc.Text('Os arquivos ficam aguardando ate voce confirmar a importacao', c="dimmed", size="xs"),
                        ]),
                        style={
                            'width': '100%',
                            'height': '150px',
                            'lineHeight': '30px',
                            'borderWidth': '2px',
                            'borderStyle': 'dashed',
                            'borderRadius': '10px',
                            'textAlign': 'center',
                            'borderColor': '#e9ecef',
                            'cursor': 'pointer',
                            'display': 'flex',
                            'flexDirection': 'column',
                            'justifyContent': 'center',
                            'alignItems': 'center',
                        },
                        multiple=True,
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Importar Pendentes",
                                id="btn-confirm-upload",
                                color="green",
                                mt="md",
                                leftSection=DashIconify(icon="akar-icons:cloud-upload"),
                            ),
                            dmc.Button(
                                "Limpar Pendentes",
                                id="btn-clear-pending",
                                color="gray",
                                variant="outline",
                                mt="md",
                            ),
                        ],
                        gap="sm",
                    ),
                    html.Div(id='output-upload-status', className="mt-3"),
                    dmc.Alert(
                        id="alert-import-status",
                        children="Aguardando novas importacoes...",
                        color="gray",
                        variant="filled",
                        mt="md",
                        style={'whiteSpace': 'pre-wrap'},
                    ),
                    dcc.Interval(id='interval-import-status', interval=1500, n_intervals=0, disabled=True),
                ], withBorder=True, shadow="sm", radius="md", style={"height": "100%"}),
            ], span={"base": 12, "md": 5}),

            dmc.GridCol([
                dmc.Card([
                    dmc.Text("Arquivos Pendentes", size="lg", fw=500, mb="sm"),
                    dmc.Text("Estes arquivos foram apenas selecionados na interface e ainda nao foram importados.", c="dimmed", size="sm", mb="sm"),
                    dash_table.DataTable(
                        id='tabela-pendentes',
                        columns=[{'name': 'Nome do Arquivo', 'id': 'filename'}],
                        data=[],
                        style_table={'overflowX': 'auto'},
                        style_header={
                            "backgroundColor": "#fff4e6",
                            "color": "#000",
                            "fontWeight": "bold",
                            "fontFamily": "sans-serif",
                        },
                        style_data={
                            "backgroundColor": "#fff",
                            "color": "#000",
                            "fontFamily": "sans-serif",
                        },
                        style_cell={'textAlign': 'left', 'padding': '10px', 'border': '1px solid #dee2e6'},
                        page_size=6,
                    ),
                ], withBorder=True, shadow="sm", radius="md", style={"height": "100%"}),
            ], span={"base": 12, "md": 7}),
        ],
    ),

    dmc.Card([
        dmc.Text("Arquivos Temporarios no Servidor", size="lg", fw=500, mb="sm"),
        dmc.Text("Esta lista deve ficar vazia apos uma importacao finalizada. Se houver itens aqui, a importacao ainda nao concluiu ou falhou antes da limpeza.", c="dimmed", size="sm", mb="sm"),
        dash_table.DataTable(
            id='tabela-arquivos-temporarios',
            columns=[
                {'name': 'Nome do Arquivo', 'id': 'filename'},
                {'name': 'Tamanho', 'id': 'size'},
            ],
            data=[],
            style_table={'overflowX': 'auto'},
            style_header={
                "backgroundColor": "#f8f9fa",
                "color": "#000",
                "fontWeight": "bold",
                "fontFamily": "sans-serif",
            },
            style_data={
                "backgroundColor": "#fff",
                "color": "#000",
                "fontFamily": "sans-serif",
            },
            style_cell={'textAlign': 'left', 'padding': '10px', 'border': '1px solid #dee2e6'},
            page_size=6,
        ),
    ], withBorder=True, shadow="sm", radius="md", mt="md"),

    dmc.Card([
        dmc.Group([
            dmc.Text("Historico de Importacoes", size="lg", fw=500),
            dmc.Group(
                [
                    dmc.Button(
                        "Ver Detalhes",
                        id="btn-open-import-details",
                        variant="outline",
                        color="blue",
                        size="sm",
                        disabled=True,
                    ),
                    dmc.Button(
                        "Excluir Dados da Importacao",
                        id="btn-delete-import-data",
                        variant="outline",
                        color="red",
                        size="sm",
                        disabled=True,
                    ),
                ],
                gap="sm",
            ),
        ], justify="space-between", mb="sm"),
        dash_table.DataTable(
            id='tabela-import-auditoria',
            columns=[
                {'name': 'ID', 'id': 'id'},
                {'name': 'Inicio', 'id': 'started_at'},
                {'name': 'Fim', 'id': 'finished_at'},
                {'name': 'Status', 'id': 'status'},
                {'name': 'Arquivos', 'id': 'files_count'},
                {'name': 'Lidas', 'id': 'rows_read'},
                {'name': 'Validas', 'id': 'rows_valid'},
                {'name': 'Novas', 'id': 'rows_new'},
                {'name': 'Atualizadas', 'id': 'rows_updated'},
                {'name': 'Erro', 'id': 'error_message'},
            ],
            data=[],
            row_selectable='single',
            style_table={'overflowX': 'auto'},
            style_header={
                "backgroundColor": "#f8f9fa",
                "color": "#000",
                "fontWeight": "bold",
                "fontFamily": "sans-serif",
            },
            style_data={
                "backgroundColor": "#fff",
                "color": "#000",
                "fontFamily": "sans-serif",
            },
            style_data_conditional=[
                {'if': {'column_id': 'status'}, 'fontWeight': 'bold', 'textTransform': 'uppercase'},
                {'if': {'filter_query': '{status} = "success"', 'column_id': 'status'}, 'backgroundColor': '#d3f9d8', 'color': '#2b8a3e'},
                {'if': {'filter_query': '{status} = "error"', 'column_id': 'status'}, 'backgroundColor': '#ffe3e3', 'color': '#c92a2a'},
                {'if': {'filter_query': '{status} = "running"', 'column_id': 'status'}, 'backgroundColor': '#dbe4ff', 'color': '#364fc7'},
            ],
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'border': '1px solid #dee2e6',
                'minWidth': '120px',
                'maxWidth': '350px',
                'whiteSpace': 'normal',
            },
            page_size=10,
        ),
    ], withBorder=True, shadow="sm", radius="md", mt="md"),

    dmc.Modal(
        id="modal-import-details",
        centered=True,
        size="lg",
        title="Detalhes da Importacao",
        children=dcc.Markdown(id="modal-import-details-body"),
    ),

    dmc.Modal(
        id="modal-delete-import",
        centered=True,
        children=[
            dmc.Text("Excluir dados importados", fw=700, size="lg", mb="md"),
            dmc.Text(id="modal-delete-import-body", mb="md"),
            dmc.Group(
                [
                    dmc.Button("Cancelar", id="btn-cancel-delete-import", variant="outline", color="gray", n_clicks=0),
                    dmc.Button("Excluir do banco", id="btn-confirm-delete-import", color="red", n_clicks=0),
                ],
                justify="flex-end",
            ),
        ],
    ),

    dmc.Modal(
        id="modal-reset-import-data",
        centered=True,
        children=[
            dmc.Text("Reiniciar base de testes", fw=700, size="lg", mb="md"),
            dmc.Text(
                "Esta acao remove todos os dados importados e o historico de importacoes, preservando usuarios e permissoes.",
                mb="md",
            ),
            dmc.Group(
                [
                    dmc.Button("Cancelar", id="btn-cancel-reset-import-data", variant="outline", color="gray", n_clicks=0),
                    dmc.Button("Reiniciar base", id="btn-confirm-reset-import-data", color="red", n_clicks=0),
                ],
                justify="flex-end",
            ),
        ],
    ),

    dcc.Store(id='store-pending-uploads', data=[]),
    dcc.Store(id='store-import-to-delete'),
    html.Div(id='dummy-import-output'),
])


@callback(
    Output('store-pending-uploads', 'data'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('store-pending-uploads', 'data'),
    prevent_initial_call=True,
)
def queue_pending_uploads(contents, filenames, current_pending):
    if contents is None:
        return no_update

    contents_list = contents if isinstance(contents, list) else [contents]
    filenames_list = filenames if isinstance(filenames, list) else [filenames]
    pending = list(current_pending or [])
    existing_names = {item['filename'] for item in pending}

    for content, filename in zip(contents_list, filenames_list):
        if filename and filename not in existing_names:
            pending.append({'filename': filename, 'contents': content})
            existing_names.add(filename)

    return pending


@callback(
    Output('tabela-pendentes', 'data'),
    Input('store-pending-uploads', 'data'),
)
def update_pending_table(pending_uploads):
    return [{'filename': item['filename']} for item in (pending_uploads or [])]


@callback(
    [Output('output-upload-status', 'children'),
     Output('store-pending-uploads', 'data', allow_duplicate=True),
     Output('interval-import-status', 'disabled'),
     Output('dummy-import-output', 'children'),
     Output('alert-import-status', 'children', allow_duplicate=True),
     Output('alert-import-status', 'color', allow_duplicate=True)],
    Input('btn-confirm-upload', 'n_clicks'),
    State('store-pending-uploads', 'data'),
    prevent_initial_call=True,
)
def confirm_pending_uploads(n_clicks, pending_uploads):
    if not pending_uploads:
        return (
            dmc.Alert("Nao ha arquivos pendentes para importar.", color="yellow", variant="filled"),
            [],
            True,
            no_update,
            "Nao ha arquivos pendentes para importar.",
            "yellow",
        )

    contents = [item['contents'] for item in pending_uploads]
    filenames = [item['filename'] for item in pending_uploads]
    result = file_management.save_uploaded_files(contents, filenames)
    saved = result.get('saved', [])
    errors = result.get('errors', [])

    processing_started = False
    if saved:
        processing_started = file_management.start_etl_async()

    status_message = (
        "Importacao em andamento..."
        if processing_started
        else "Nenhuma importacao foi iniciada."
    )
    status_color = "blue" if processing_started else "gray"

    return (
        _build_upload_feedback(saved, errors, processing_started),
        [],
        not processing_started,
        "import-started" if processing_started else no_update,
        status_message,
        status_color,
    )


@callback(
    [Output('store-pending-uploads', 'data', allow_duplicate=True),
     Output('output-upload-status', 'children', allow_duplicate=True)],
    Input('btn-clear-pending', 'n_clicks'),
    prevent_initial_call=True,
)
def clear_pending_uploads(n_clicks):
    return [], dmc.Alert("Fila de arquivos pendentes limpa.", color="gray", variant="filled")


@callback(
    Output('tabela-arquivos-temporarios', 'data'),
    [Input('url', 'pathname'),
     Input('interval-import-status', 'n_intervals'),
     Input('dummy-import-output', 'children'),
     Input('output-upload-status', 'children')]
)
def update_temp_file_list(pathname, n_intervals, import_trigger, upload_trigger):
    return file_management.list_files()


@callback(
    Output('tabela-import-auditoria', 'data'),
    [Input('url', 'pathname'),
     Input('interval-import-status', 'n_intervals'),
     Input('dummy-import-output', 'children')]
)
def update_import_audit_table(pathname, n_intervals, import_trigger):
    return file_management.list_import_audit()


@callback(
    [Output('btn-open-import-details', 'disabled'),
     Output('btn-delete-import-data', 'disabled')],
    Input('tabela-import-auditoria', 'selected_rows')
)
def toggle_audit_action_buttons(selected_rows):
    disabled = not selected_rows
    return disabled, disabled


@callback(
    [Output('alert-import-status', 'children'),
     Output('alert-import-status', 'color'),
     Output('interval-import-status', 'disabled', allow_duplicate=True)],
    Input('interval-import-status', 'n_intervals'),
    prevent_initial_call=True
)
def check_import_status(n):
    status, message, color = file_management.get_etl_status()
    if status:
        return message, color, False
    if color == "green":
        cache.clear()
    return message, color, True


@callback(
    [Output('modal-import-details', 'opened'),
     Output('modal-import-details-body', 'children')],
    Input('btn-open-import-details', 'n_clicks'),
    [State('tabela-import-auditoria', 'selected_rows'),
     State('tabela-import-auditoria', 'data')],
    prevent_initial_call=True,
)
def open_import_details(n_clicks, selected_rows, table_data):
    if not selected_rows or not table_data:
        return False, no_update

    record = table_data[selected_rows[0]]
    details = record.get('details') or 'Sem detalhes adicionais.'
    error_message = record.get('error_message') or 'Sem erro registrado.'
    content = (
        f"### Importacao #{record.get('id')}\n"
        f"- Status: {record.get('status')}\n"
        f"- Inicio: {record.get('started_at')}\n"
        f"- Fim: {record.get('finished_at')}\n"
        f"- Arquivos processados: {record.get('files_count')}\n"
        f"- Linhas lidas: {record.get('rows_read')}\n"
        f"- Linhas validas: {record.get('rows_valid')}\n"
        f"- Novas: {record.get('rows_new')}\n"
        f"- Atualizadas: {record.get('rows_updated')}\n"
        f"- Erro: {error_message}\n\n"
        f"### Detalhes\n{details}"
    )
    return True, content


@callback(
    [Output('modal-delete-import', 'opened'),
     Output('modal-delete-import-body', 'children'),
     Output('store-import-to-delete', 'data')],
    [Input('btn-delete-import-data', 'n_clicks'),
     Input('btn-cancel-delete-import', 'n_clicks'),
     Input('btn-confirm-delete-import', 'n_clicks')],
    [State('tabela-import-auditoria', 'selected_rows'),
     State('tabela-import-auditoria', 'data')],
    prevent_initial_call=True,
)
def toggle_delete_import_modal(n_open, n_cancel, n_confirm, selected_rows, table_data):
    trigger = callback_context.triggered_id
    if trigger == 'btn-delete-import-data' and selected_rows and table_data:
        record = table_data[selected_rows[0]]
        message = (
            f"Confirma a exclusao do banco dos dados vinculados a importacao #{record.get('id')}? "
            "Esta acao afeta os registros carregados por esse lote."
        )
        return True, message, record.get('id')

    if trigger in {'btn-cancel-delete-import', 'btn-confirm-delete-import'}:
        return False, no_update, no_update

    return False, no_update, no_update


@callback(
    Output('dummy-import-output', 'children', allow_duplicate=True),
    Input('btn-confirm-delete-import', 'n_clicks'),
    State('store-import-to-delete', 'data'),
    prevent_initial_call=True,
)
def delete_imported_data(n_clicks, audit_id):
    if not audit_id:
        return no_update

    deleted_count = file_management.delete_imported_data(audit_id)
    return f"import-deleted-{audit_id}-{deleted_count}"


@callback(
    [Output('modal-reset-import-data', 'opened'),
     Output('dummy-import-output', 'children', allow_duplicate=True)],
    [Input('btn-reset-import-data', 'n_clicks'),
     Input('btn-cancel-reset-import-data', 'n_clicks'),
     Input('btn-confirm-reset-import-data', 'n_clicks')],
    prevent_initial_call=True,
)
def reset_import_data(n_open, n_cancel, n_confirm):
    trigger = callback_context.triggered_id
    if trigger == 'btn-reset-import-data':
        return True, no_update
    if trigger == 'btn-cancel-reset-import-data':
        return False, no_update
    if trigger == 'btn-confirm-reset-import-data':
        success = file_management.reset_import_data()
        return False, "import-reset-success" if success else "import-reset-failed"
    return False, no_update
