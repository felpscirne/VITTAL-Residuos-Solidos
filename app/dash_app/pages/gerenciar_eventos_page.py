from datetime import datetime

import dash_mantine_components as dmc
from dash import callback, dash_table, html, no_update
from dash.dependencies import Input, Output, State
from dash_iconify import DashIconify
from flask_login import current_user

from app import db
from app.application.analytics import get_list_setores
from app.models import Event


ALL_SECTORS_LABEL = "Todos os Setores"


layout = html.Div(
    [
        dmc.Title("Gerenciar Eventos Operacionais", order=2),
        dmc.Text("Histórico de manutenções, paradas e mudanças de padrão.", c="dimmed", size="sm"),
        dmc.Divider(variant="solid", my="md"),
        dmc.Grid(
            gutter="md",
            children=[
                dmc.GridCol(
                    [
                        dmc.Card(
                            [
                                dmc.Text("Novo Evento", size="lg", fw=500, mb="sm"),
                                dmc.TextInput(
                                    label="Título do Evento",
                                    placeholder="Ex: Manutenção da Balança",
                                    id="evt-title",
                                    mb="sm",
                                ),
                                dmc.Select(
                                    label="Tipo",
                                    id="evt-type",
                                    data=[
                                        {"label": "Manutenção Técnica", "value": "Manutenção"},
                                        {"label": "Mudança de Escala", "value": "Escala"},
                                        {"label": "Feriado/Parada", "value": "Parada"},
                                        {"label": "Outro", "value": "Outro"},
                                    ],
                                    value="Manutenção",
                                    mb="sm",
                                ),
                                dmc.DatePickerInput(
                                    type="range",
                                    label="Período (Início e Fim)",
                                    placeholder="Selecione as datas",
                                    id="evt-date-range",
                                    firstDayOfWeek=1,
                                    valueFormat="DD/MM/YYYY",
                                    mb="sm",
                                    clearable=True,
                                ),
                                dmc.MultiSelect(
                                    label="Setores Afetados",
                                    id="evt-sectors",
                                    placeholder="Selecione um ou mais setores...",
                                    data=[],
                                    searchable=True,
                                    nothingFoundMessage="Nenhum setor encontrado",
                                    mb="sm",
                                ),
                                dmc.Textarea(
                                    label="Descrição/Observações",
                                    placeholder="Detalhes adicionais...",
                                    id="evt-desc",
                                    minRows=3,
                                    mb="md",
                                ),
                                dmc.Button(
                                    "Salvar Evento",
                                    id="btn-save-event",
                                    color="green",
                                    fullWidth=True,
                                    leftSection=DashIconify(icon="fluent:save-24-regular"),
                                ),
                            ],
                            withBorder=True,
                            shadow="sm",
                            radius="md",
                        )
                    ],
                    span={"base": 12, "md": 4},
                    id="col-form-event",
                ),
                dmc.GridCol(
                    [
                        dmc.Card(
                            [
                                dmc.Text("Histórico de Eventos", size="lg", fw=500, mb="sm"),
                                dmc.ScrollArea(
                                    dash_table.DataTable(
                                        id="table-events",
                                        columns=[
                                            {"name": "Data Início", "id": "start"},
                                            {"name": "Data Fim", "id": "end"},
                                            {"name": "Título", "id": "title"},
                                            {"name": "Tipo", "id": "type"},
                                            {"name": "Setores Afetados", "id": "sectors"},
                                        ],
                                        data=[],
                                        row_selectable="single",
                                        style_table={"minWidth": "100%"},
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
                                            "whiteSpace": "normal",
                                            "height": "auto",
                                        },
                                        style_cell={"border": "1px solid #dee2e6", "padding": "10px", "textAlign": "left"},
                                        page_size=10,
                                    ),
                                    offsetScrollbars=True,
                                    type="auto",
                                ),
                                dmc.Group(
                                    [
                                        dmc.Button(
                                            "Excluir Selecionado",
                                            id="btn-delete-event",
                                            color="red",
                                            variant="outline",
                                            size="sm",
                                            disabled=True,
                                            leftSection=DashIconify(icon="fluent:delete-24-regular"),
                                        ),
                                    ],
                                    id="div-btn-delete",
                                    mt="md",
                                ),
                                html.Div(id="evt-msg-output", className="mt-2"),
                            ],
                            withBorder=True,
                            shadow="sm",
                            radius="md",
                            style={"height": "100%"},
                        )
                    ],
                    span={"base": 12, "md": 8},
                    id="col-list-event",
                ),
            ],
        ),
    ]
)


@callback(
    [Output("col-form-event", "style"), Output("col-list-event", "span"), Output("div-btn-delete", "style")],
    Input("url", "pathname"),
)
def update_layout_by_role(pathname):
    if not current_user.is_authenticated:
        return {"display": "none"}, {"base": 12, "md": 12}, {"display": "none"}

    role = current_user.role
    if role in ["management", "superadmin"]:
        return {"display": "block"}, {"base": 12, "md": 8}, {"display": "block"}
    return {"display": "none"}, {"base": 12, "md": 12}, {"display": "none"}


@callback(
    Output("evt-sectors", "data"),
    Input("url", "pathname"),
)
def load_sectors(pathname):
    if pathname != "/gerenciar-eventos":
        return no_update

    try:
        sectors = [sector for sector in get_list_setores() if sector and sector != ALL_SECTORS_LABEL]
        options = [{"label": ALL_SECTORS_LABEL, "value": ALL_SECTORS_LABEL}]
        options.extend({"label": sector, "value": sector} for sector in sectors)
        return options
    except Exception as exc:
        print(f"DEBUG: Erro ao buscar setores: {exc}")
        return []


@callback(
    Output("evt-sectors", "value"),
    Input("evt-sectors", "value"),
    prevent_initial_call=True,
)
def normalize_sector_selection(selected_values):
    if not selected_values:
        return selected_values
    if ALL_SECTORS_LABEL in selected_values:
        return [ALL_SECTORS_LABEL]
    return selected_values


@callback(
    Output("table-events", "data"),
    Input("url", "pathname"),
    Input("btn-save-event", "n_clicks"),
    Input("btn-delete-event", "n_clicks"),
)
def load_events_table(pathname, _save_clicks, _delete_clicks):
    if pathname != "/gerenciar-eventos":
        return no_update

    events_data = []
    try:
        events = Event.query.order_by(Event.start_date.desc()).all()
        for event in events:
            events_data.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "type": event.event_type,
                    "start": event.start_date.strftime("%d/%m/%Y"),
                    "end": event.end_date.strftime("%d/%m/%Y"),
                    "sectors": event.affected_sectors or ALL_SECTORS_LABEL,
                }
            )
    except Exception:
        return []

    return events_data


@callback(
    [
        Output("evt-msg-output", "children"),
        Output("btn-delete-event", "disabled"),
        Output("evt-title", "value"),
        Output("evt-desc", "value"),
        Output("evt-type", "value"),
        Output("evt-date-range", "value"),
        Output("evt-sectors", "value", allow_duplicate=True),
    ],
    [Input("url", "pathname"), Input("btn-save-event", "n_clicks"), Input("btn-delete-event", "n_clicks")],
    [
        State("evt-title", "value"),
        State("evt-type", "value"),
        State("evt-date-range", "value"),
        State("evt-sectors", "value"),
        State("evt-desc", "value"),
        State("table-events", "selected_rows"),
        State("table-events", "data"),
    ],
    prevent_initial_call=True,
)
def manage_events(pathname, n_save, n_delete, title, etype, date_range, sectors, desc, selected_rows, rows):
    if pathname != "/gerenciar-eventos":
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    msg = ""
    user_can_edit = current_user.is_authenticated and current_user.role in ["management", "superadmin"]

    import dash

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else "init"

    ret_title = no_update
    ret_desc = no_update
    ret_type = no_update
    ret_daterange = no_update
    ret_sectors = no_update
    btn_disabled = True

    if trigger_id == "btn-save-event" and user_can_edit:
        if not title or not date_range or len(date_range) != 2:
            msg = dmc.Alert("Preencha Título e Datas.", color="yellow", variant="filled")
        else:
            try:
                start_date_str = date_range[0]
                end_date_str = date_range[1]
                sectors_str = ALL_SECTORS_LABEL if not sectors or ALL_SECTORS_LABEL in sectors else ", ".join(sectors)

                new_event = Event(
                    title=title,
                    event_type=etype,
                    start_date=datetime.strptime(start_date_str.split("T")[0], "%Y-%m-%d"),
                    end_date=datetime.strptime(end_date_str.split("T")[0], "%Y-%m-%d"),
                    affected_sectors=sectors_str,
                    description=desc,
                )
                db.session.add(new_event)
                db.session.commit()
                msg = dmc.Alert("Evento criado com sucesso!", color="green", variant="filled")
                ret_title = ""
                ret_desc = ""
                ret_type = "Manutenção"
                ret_daterange = None
                ret_sectors = []
            except Exception as exc:
                db.session.rollback()
                msg = dmc.Alert(f"Erro ao salvar: {exc}", color="red", variant="filled")

    if trigger_id == "btn-delete-event" and selected_rows and user_can_edit:
        try:
            row_data = rows[selected_rows[0]]
            evt_id = row_data.get("id")
            if evt_id:
                event_to_del = Event.query.get(evt_id)
                if event_to_del:
                    db.session.delete(event_to_del)
                    db.session.commit()
                    msg = dmc.Alert("Evento excluído.", color="green", variant="filled")
        except Exception as exc:
            db.session.rollback()
            msg = dmc.Alert(f"Erro ao excluir: {exc}", color="red", variant="filled")

    return msg, btn_disabled, ret_title, ret_desc, ret_type, ret_daterange, ret_sectors


@callback(
    Output("btn-delete-event", "disabled", allow_duplicate=True),
    Input("table-events", "selected_rows"),
    prevent_initial_call=True,
)
def toggle_delete(selected_rows):
    return not selected_rows
