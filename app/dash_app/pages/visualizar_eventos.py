import dash
from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from app.models import Event

# --- Layout ---
layout = html.Div([
    html.H1('Visualizar Eventos'),
    html.P('Quadro geral de avisos, manutenções e paradas.'),
    html.Hr(),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Histórico de Eventos"),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='view-table-events',
                        columns=[
                            {'name': 'Data Início', 'id': 'start'},
                            {'name': 'Data Fim', 'id': 'end'},
                            {'name': 'Título', 'id': 'title'},
                            {'name': 'Tipo', 'id': 'type'},
                            {'name': 'Setores Afetados', 'id': 'sectors'},
                        ],
                        data=[],
                        row_selectable=False, # Não selecionável, apenas leitura
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
                        page_size=15 # Um pouco maior que a gestão
                    )
                ])
            ], className="dbc h-100")
        ], md=12)
    ])
])

# --- Callbacks ---

@callback(
    Output('view-table-events', 'data'),
    Input('url', 'pathname')
)
def list_view_events(pathname):
    if pathname == '/visualizar-eventos':
        events_data = []
        try:
            # Busca todos os eventos, ordenados por data de início (decrescente)
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
        except Exception as e:
            print(f"Erro ao buscar eventos: {e}")
            pass
        return events_data
    
    return dash.no_update
