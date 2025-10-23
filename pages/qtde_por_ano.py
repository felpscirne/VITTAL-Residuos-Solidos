from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

from database import engine, get_anos_options

anos_options, ano_inicial = get_anos_options()

query_empresas = "SELECT DISTINCT fornecedor_cliente FROM registro WHERE fornecedor_cliente IS NOT NULL ORDER BY fornecedor_cliente"
empresas_df = pd.read_sql(query_empresas, engine)
empresas_options = [{'label': emp, 'value': emp} for emp in empresas_df['fornecedor_cliente']]

empresas_options.insert(0, {'label': 'Todas as Empresas', 'value': 'todas'})


layout = html.Div([
    html.H1('Quantidade de Registros por Mês/Ano'),

    
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
            html.Label('Selecione a Empresa:'),
            dcc.Dropdown(
                id='filtro-empresa-qtde', 
                options=empresas_options,
                value='todas' 
            )
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
    ]),
    
    dcc.Graph(id='grafico-qtde-por-ano')
])

@callback(
    Output('grafico-qtde-por-ano', 'figure'),
    [Input('filtro-ano-qtde', 'value'),
     Input('filtro-empresa-qtde', 'value')]
)
def update_graph(ano_selecionado, empresa_selecionada):
    
    query = """
        SELECT EXTRACT(MONTH FROM data_hora) AS mes, 
               COUNT(*) AS qtde 
        FROM registro 
        WHERE EXTRACT(YEAR FROM data_hora) = %(ano)s
    """
    params = {'ano': ano_selecionado}
    
    if empresa_selecionada != 'todas':
        query += " AND fornecedor_cliente = %(empresa)s"
        params['empresa'] = empresa_selecionada
        
    query += " GROUP BY mes ORDER BY mes"
    
    df = pd.read_sql(query, engine, params=params)
    
    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df['mes_nome'] = df['mes'].map(meses_map)
    
    fig = px.bar(df, x='mes_nome', y='qtde', 
                 title=f'Registros em {ano_selecionado} (Empresa: {empresa_selecionada})')
    
    return fig