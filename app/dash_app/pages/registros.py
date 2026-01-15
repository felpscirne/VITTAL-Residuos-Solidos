from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import dash_bootstrap_components as dbc

# Service imports
from app.services.data_repository import get_anos_options, get_registros_filtrados

anos_options, ano_inicial = get_anos_options()

table_header_style = {
    "backgroundColor": "var(--bs-tertiary-bg)",
    "color": "var(--bs-body-color)",
    "fontWeight": "bold"
}

table_data_style = {
    "backgroundColor": "var(--bs-body-bg)",
    "color": "var(--bs-body-color)",
}

layout = html.Div([
    html.H1('Visualizador de Registros'),
    html.P('Use os filtros para buscar nos registros brutos.'),
    
    dbc.Row(
        [
            dbc.Col(
                [
                    html.Label('Selecione o Ano:'),
                    dcc.Dropdown(id='filtro-ano-tabela', options=anos_options, value=ano_inicial)
                ],
                md=3 
            ),
            dbc.Col(
                [
                    html.Label('Mês: (1-12)'),
                    dcc.Input(id='filtro-mes-tabela', type='number', min=1, max=12, style={'width': '100%'})
                ],
                md=3
            ),
            dbc.Col(
                [
                    html.Label('Ticket:'),
                    dcc.Input(id='filtro-ticket-tabela', type='text', style={'width': '100%'})
                ],
                md=3
            ),
            dbc.Col(
                [
                    html.Label(u'\u00A0', style={'display': 'block'}),
                    dbc.Button('Buscar Registros', id='btn-buscar-tabela', n_clicks=0, className="w-100")  
                ],
                md=3
            )
        ],
        className="dbc mb-3" 
    ),
    html.Hr(),

    dbc.Card(
        dbc.CardBody([
            dash_table.DataTable(
                id='tabela-registros-brutos',
                page_size=20,
                style_table={'overflowX': 'auto'},
                sort_action='native',
                filter_action='native',
                
                style_header=table_header_style,
                style_data=table_data_style,
                style_cell={'border': '1px solid var(--bs-border-color)'},
                style_filter={
                    "backgroundColor": "var(--bs-secondary-bg)",
                    "color": "var(--bs-body-color)"
                },
            )
        ])
    )
])

@callback(
    [Output('tabela-registros-brutos', 'data'),
     Output('tabela-registros-brutos', 'columns')],
    [Input('btn-buscar-tabela', 'n_clicks')],
    [State('filtro-ano-tabela', 'value'),
     State('filtro-mes-tabela', 'value'),
     State('filtro-ticket-tabela', 'value')]
)
def update_table(n_clicks, ano, mes, ticket):
    if n_clicks == 0:
        return [], []
    
    try:
        df = get_registros_filtrados(ano, mes, ticket)
        data_tabela = df.to_dict('records')
        cols_tabela = [{"name": i, "id": i} for i in df.columns]
        return data_tabela, cols_tabela
    except Exception as e:
        print(f"Erro ao buscar na tabela: {e}")
        return [], []