from datetime import datetime

from dash import callback, callback_context, dash_table, dcc, html, no_update
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from flask_login import current_user

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
                "Processando arquivos enviados. O status abaixo acompanha a execucao em tempo real.",
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


def _get_current_actor():
    if getattr(current_user, "is_authenticated", False):
        if getattr(current_user, "name", None) and getattr(current_user, "email", None):
            return f"{current_user.name} <{current_user.email}>"
        return current_user.name or current_user.email or "Usuario autenticado"
    return "Sistema"


def _get_current_role():
    return getattr(current_user, "role", None)


def _user_can_import_files():
    return _get_current_role() in {"operator", "management"}


def _user_can_delete_data():
    return _get_current_role() == "management"


layout = html.Div([
    dmc.Title('Gerenciamento de Arquivos e Dados', order=2),
    dmc.Text('Selecione arquivos, confira os pendentes e confirme a importacao. Todo o historico de carga e exclusao pode ser acompanhado por esta tela.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Group(
        [
            dmc.Button(
                "Reiniciar Base",
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
                        "Excluir Dados do Arquivo",
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
        dmc.SimpleGrid(
            cols={"base": 1, "md": 2, "xl": 4},
            spacing="sm",
            mb="sm",
            children=[
                dmc.TextInput(
                    id="filtro-import-arquivo",
                    label="Nome do arquivo",
                    placeholder="Filtrar por arquivo",
                ),
                dmc.TextInput(
                    id="filtro-import-incluido-por",
                    label="Incluido por",
                    placeholder="Filtrar por usuario",
                ),
                dmc.TextInput(
                    id="filtro-import-excluido-por",
                    label="Excluido por",
                    placeholder="Filtrar por usuario",
                ),
                dmc.Select(
                    id="filtro-import-ordem",
                    label="Ordenacao",
                    value="adicionadas_mais_recentes",
                    data=[
                        {"value": "adicionadas_mais_recentes", "label": "Adicionadas mais recentes"},
                        {"value": "adicionadas_mais_antigas", "label": "Adicionadas mais antigas"},
                        {"value": "excluidas_mais_recentes", "label": "Excluidas mais recentes"},
                        {"value": "excluidas_mais_antigas", "label": "Excluidas mais antigas"},
                    ],
                    allowDeselect=False,
                ),
            ],
        ),
        dash_table.DataTable(
            id='tabela-import-auditoria',
            columns=[
                {'name': 'ID', 'id': 'id'},
                {'name': 'Arquivo', 'id': 'source_file'},
                {'name': 'Incluido por', 'id': 'initiated_by'},
                {'name': 'Inicio', 'id': 'started_at'},
                {'name': 'Fim', 'id': 'finished_at'},
                {'name': 'Status', 'id': 'status_label'},
                {'name': 'Lidas', 'id': 'rows_read'},
                {'name': 'Validas', 'id': 'rows_valid'},
                {'name': 'Novas', 'id': 'rows_new'},
                {'name': 'Atualizadas', 'id': 'rows_updated'},
                {'name': 'Excluido por', 'id': 'deleted_by'},
                {'name': 'Data da exclusao', 'id': 'deleted_at'},
                {'name': 'Linhas excluidas', 'id': 'deleted_rows'},
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
                {'if': {'column_id': 'status_label'}, 'fontWeight': 'bold', 'textTransform': 'uppercase'},
                {'if': {'filter_query': '{status_label} = "Concluida"', 'column_id': 'status_label'}, 'backgroundColor': '#d3f9d8', 'color': '#2b8a3e'},
                {'if': {'filter_query': '{status_label} = "Falhou"', 'column_id': 'status_label'}, 'backgroundColor': '#ffe3e3', 'color': '#c92a2a'},
                {'if': {'filter_query': '{status_label} = "Em andamento"', 'column_id': 'status_label'}, 'backgroundColor': '#dbe4ff', 'color': '#364fc7'},
                {'if': {'filter_query': '{status_label} = "Excluida"', 'column_id': 'status_label'}, 'backgroundColor': '#fff3bf', 'color': '#e67700'},
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
            dmc.Text("Reiniciar base", fw=700, size="lg", mb="md"),
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
    dcc.Store(id='store-import-audit-raw', data=[]),
    html.Div(
        id='import-notification-area',
        style={
            'position': 'fixed',
            'top': '1rem',
            'right': '1rem',
            'zIndex': 2000,
            'maxWidth': '380px',
        },
    ),
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
     Output('alert-import-status', 'color', allow_duplicate=True),
     Output('import-notification-area', 'children', allow_duplicate=True)],
    Input('btn-confirm-upload', 'n_clicks'),
    State('store-pending-uploads', 'data'),
    prevent_initial_call=True,
)
def confirm_pending_uploads(n_clicks, pending_uploads):
    if not _user_can_import_files():
        return (
            dmc.Alert("Voce nao possui permissao para iniciar importacoes.", color="red", variant="filled"),
            pending_uploads or [],
            True,
            no_update,
            "Voce nao possui permissao para iniciar importacoes.",
            "red",
            dmc.Notification(
                title="Importacao nao iniciada",
                message="Voce nao possui permissao para iniciar importacoes.",
                color="red",
                action="show",
                autoClose=5000,
            ),
        )

    if not pending_uploads:
        return (
            dmc.Alert("Nao ha arquivos pendentes para importar.", color="yellow", variant="filled"),
            [],
            True,
            no_update,
            "Nao ha arquivos pendentes para importar.",
            "yellow",
            dmc.Notification(
                title="Nenhum arquivo pendente",
                message="Nao ha arquivos pendentes para importar.",
                color="yellow",
                action="show",
                autoClose=4000,
            ),
        )

    contents = [item['contents'] for item in pending_uploads]
    filenames = [item['filename'] for item in pending_uploads]
    result = file_management.save_uploaded_files(contents, filenames)
    saved = result.get('saved', [])
    errors = result.get('errors', [])

    processing_started = False
    if saved:
        processing_started = file_management.start_etl_async(initiated_by=_get_current_actor())

    status_message = (
        "Processando arquivos enviados..."
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
        dmc.Notification(
            title="Processamento iniciado" if processing_started else "Importacao nao iniciada",
            message=(
                "Os arquivos enviados estao sendo processados agora."
                if processing_started
                else "Nenhum arquivo valido estava disponivel para iniciar a importacao."
            ),
            color="blue" if processing_started else "gray",
            action="show",
            loading=processing_started,
            autoClose=False if processing_started else 4000,
        ),
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
    Output('store-import-audit-raw', 'data'),
    [Input('url', 'pathname'),
     Input('interval-import-status', 'n_intervals'),
     Input('dummy-import-output', 'children')]
)
def update_import_audit_table(pathname, n_intervals, import_trigger):
    return file_management.list_import_audit()


@callback(
    [Output('btn-reset-import-data', 'style'),
     Output('btn-delete-import-data', 'style')],
    Input('url', 'pathname'),
)
def update_file_management_action_visibility(pathname):
    hidden_style = {'display': 'none'}
    if _user_can_delete_data():
        return {}, {}
    return hidden_style, hidden_style


@callback(
    Output('tabela-import-auditoria', 'data'),
    [
        Input('store-import-audit-raw', 'data'),
        Input('filtro-import-arquivo', 'value'),
        Input('filtro-import-incluido-por', 'value'),
        Input('filtro-import-excluido-por', 'value'),
        Input('filtro-import-ordem', 'value'),
    ],
)
def filter_import_audit_table(records, file_filter, added_by_filter, deleted_by_filter, order_filter):
    data = list(records or [])

    def _matches(value, pattern):
        if not pattern:
            return True
        return pattern.strip().lower() in str(value or "").lower()

    filtered = [
        row for row in data
        if _matches(row.get('source_file'), file_filter)
        and _matches(row.get('initiated_by'), added_by_filter)
        and _matches(row.get('deleted_by'), deleted_by_filter)
    ]

    def _date_key(row, field):
        raw = row.get(field) or ""
        if not raw:
            return datetime.min
        try:
            return datetime.strptime(raw, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            return datetime.min

    if order_filter == "adicionadas_mais_antigas":
        filtered.sort(key=lambda row: _date_key(row, 'started_at'))
    elif order_filter == "excluidas_mais_recentes":
        filtered.sort(key=lambda row: _date_key(row, 'deleted_at'), reverse=True)
    elif order_filter == "excluidas_mais_antigas":
        filtered.sort(key=lambda row: _date_key(row, 'deleted_at'))
    else:
        filtered.sort(key=lambda row: _date_key(row, 'started_at'), reverse=True)

    return filtered


@callback(
    [Output('btn-open-import-details', 'disabled'),
     Output('btn-delete-import-data', 'disabled')],
    [Input('tabela-import-auditoria', 'selected_rows'),
     State('tabela-import-auditoria', 'data')]
)
def toggle_audit_action_buttons(selected_rows, table_data):
    if not selected_rows or not table_data:
        return True, True

    record = table_data[selected_rows[0]]
    delete_disabled = (not _user_can_delete_data()) or record.get('status') in {'deleted', 'running'}
    return False, delete_disabled


@callback(
    [Output('alert-import-status', 'children'),
     Output('alert-import-status', 'color'),
     Output('interval-import-status', 'disabled', allow_duplicate=True),
     Output('import-notification-area', 'children', allow_duplicate=True)],
    Input('interval-import-status', 'n_intervals'),
    prevent_initial_call=True
)
def check_import_status(n):
    status, message, color = file_management.get_etl_status()
    if status:
        return (
            message,
            color,
            False,
            dmc.Notification(
                title="Processamento em andamento",
                message=message,
                color="blue",
                action="show",
                loading=True,
                autoClose=False,
            ),
        )
    if color == "green":
        cache.clear()
    title = "Processamento concluido" if color == "green" else "Processamento finalizado com alertas"
    return (
        message,
        color,
        True,
        dmc.Notification(
            title=title,
            message=message,
            color=color,
            action="show",
            autoClose=6000,
        ),
    )


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
        f"- Arquivo: {record.get('source_file')}\n"
        f"- Incluido por: {record.get('initiated_by') or 'Nao informado'}\n"
        f"- Status: {record.get('status_label') or record.get('status')}\n"
        f"- Inicio: {record.get('started_at')}\n"
        f"- Fim: {record.get('finished_at')}\n"
        f"- Linhas lidas: {record.get('rows_read')}\n"
        f"- Linhas validas: {record.get('rows_valid')}\n"
        f"- Novas: {record.get('rows_new')}\n"
        f"- Atualizadas: {record.get('rows_updated')}\n"
        f"- Excluido por: {record.get('deleted_by') or 'Nao aplicavel'}\n"
        f"- Data da exclusao: {record.get('deleted_at') or 'Nao aplicavel'}\n"
        f"- Linhas excluidas: {record.get('deleted_rows')}\n"
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
        if not _user_can_delete_data():
            return False, no_update, no_update
        record = table_data[selected_rows[0]]
        message = (
            f"Confirma a exclusao do banco dos dados importados a partir do arquivo '{record.get('source_file')}'? "
            "A remocao afetara somente os registros vinculados a este arquivo."
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
    if not audit_id or not _user_can_delete_data():
        return no_update

    deleted_count = file_management.delete_imported_data(audit_id, deleted_by=_get_current_actor())
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
        if not _user_can_delete_data():
            return False, no_update
        return True, no_update
    if trigger == 'btn-cancel-reset-import-data':
        return False, no_update
    if trigger == 'btn-confirm-reset-import-data':
        if not _user_can_delete_data():
            return False, no_update
        success = file_management.reset_import_data()
        return False, "import-reset-success" if success else "import-reset-failed"
    return False, no_update
