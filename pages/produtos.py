from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

from database import engine, get_anos_options

anos_options, ano_inicial = get_anos_options()

query_produtos = "SELECT produto, count(*) from registro group by produto order by produto;"
produtos_df = pd.read_sql(query_produtos, engine)
produtos_options = [{'label': emp, 'value': emp} for emp in produtos_df['produto']]

produtos_options.insert(0, {'label': 'Todos os Produtos', 'value': 'todos'})


layout = html.Div([
    html.H1('Quantidade de Registros por Tipo de Produto'),
    html.H2('Registros de produtos divididos por tipo.'),

    
    html.Div(className='filtros-pagina', children=[
        html.Div([
            html.Label('Selecione o Ano:'),
            dcc.Dropdown(
                id='filtro-ano-qtde', 
                options=anos_options,
                value=ano_inicial,
                clearable=False
            )
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            html.Label('Selecione o Produto:'),
            dcc.Dropdown(
                id='filtro-produto-qtde', 
                options=produtos_options,
                value='todos' 
            )
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
    ]),
    dcc.Graph(id='grafico-produtos')
])

@callback(
    Output('grafico-produtos', 'figure'),
    [Input('filtro-ano-qtde', 'value'),
     Input('filtro-produto-qtde', 'value')]
)
def update_graph(ano_selecionado, produto_selecionado):

    query = """
    """
    params = {'ano': ano_selecionado}
    
    if produto_selecionado != 'todos':
        query += " AND produto = %(produto)s"
        params['produto'] = produto_selecionado

    query += " GROUP BY mes ORDER BY mes"
    
    df = pd.read_sql(query, engine, params=params)
    
    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df['mes_nome'] = df['mes'].map(meses_map)
    
    fig = px.bar(df, x='mes_nome', y='qtde', 
                 title=f'Registros em {ano_selecionado} (Produto: {produto_selecionado})')
    
    return fig