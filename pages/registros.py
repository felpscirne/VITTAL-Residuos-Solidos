from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd

# Importa a engine do banco e helpers
from database import engine, get_anos_options

# Carrega filtros
anos_options, ano_inicial = get_anos_options()

# --- Layout da Página ---
layout = html.Div([
    html.H1('Visualizador de Registros'),
    html.P('Use os filtros para buscar nos registros brutos.'),
    
    # --- Filtros ---
    html.Div(className='filtros-pagina', children=[
        html.Div([
            html.Label('Selecione o Ano:'),
            dcc.Dropdown(
                id='filtro-ano-tabela',
                options=anos_options,
                value=ano_inicial
            )
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '5px'}),
        
        html.Div([
            html.Label('Selecione o Mês: (1-12)'),
            dcc.Input(
                id='filtro-mes-tabela',
                type='number',
                placeholder='Ex: 5',
                min=1, max=12
            )
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '5px'}),
        
        html.Div([
            html.Label('Filtrar por Ticket:'),
            dcc.Input(
                id='filtro-ticket-tabela',
                type='text',
                placeholder='Ex: 12345'
            )
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '5px'}),
    ]),
    
    html.Button('Buscar Registros', id='btn-buscar-tabela', n_clicks=0),
    html.Hr(),
    
    # A Tabela de Dados
    dash_table.DataTable(
        id='tabela-registros-brutos',
        page_size=20,             
        style_table={'overflowX': 'auto'}, 
        sort_action='native',     
        filter_action='native',   
    )
])

# --- Callback da Tabela ---
@callback(
    [Output('tabela-registros-brutos', 'data'),
     Output('tabela-registros-brutos', 'columns')],
    [Input('btn-buscar-tabela', 'n_clicks')], 
    [State('filtro-ano-tabela', 'value'),     
     State('filtro-mes-tabela', 'value'),
     State('filtro-ticket-tabela', 'value')]
)
def update_table(n_clicks, ano, mes, ticket):
    # Não faz nada até o botão ser clicado
    if n_clicks == 0:
        return [], []

    # Constrói a query dinamicamente
    query = "SELECT * FROM registro WHERE 1=1"
    params = {}
    
    if ano:
        query += " AND EXTRACT(YEAR FROM data_hora) = %(ano)s"
        params['ano'] = ano
    if mes:
        query += " AND EXTRACT(MONTH FROM data_hora) = %(mes)s"
        params['mes'] = mes
    if ticket:
        query += " AND ticket = %(ticket)s"
        params['ticket'] = ticket
        
    query += " ORDER BY data_hora DESC"
    
    try:
        df = pd.read_sql(query, engine, params=params)
        
        # Formata colunas de data para a tabela
        if 'data_hora' in df.columns:
            df['data_hora'] = df['data_hora'].astype(str)
            
        data_tabela = df.to_dict('records')
        cols_tabela = [{"name": i, "id": i} for i in df.columns]
        
        return data_tabela, cols_tabela
    except Exception as e:
        print(f"Erro ao buscar na tabela: {e}")
        return [], []