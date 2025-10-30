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
    html.H1('Análise Mensal (Volume e Peso)'),
    
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
    

    dcc.Graph(id='grafico-qtde-por-mes'),
    html.Hr(),
    dcc.Graph(id='grafico-media-peso-por-mes')
])

@callback(
    [Output('grafico-qtde-por-mes', 'figure'),
     Output('grafico-media-peso-por-mes', 'figure')],
    [Input('filtro-ano-qtde', 'value'),
     Input('filtro-empresa-qtde', 'value')]
)
def update_graph(ano_selecionado, empresa_selecionada):
    
    base_query = " FROM registro WHERE EXTRACT(YEAR FROM data_hora) = %(ano)s"
    params = {'ano': ano_selecionado}
    
    if empresa_selecionada != 'todas':
        base_query += " AND fornecedor_cliente = %(empresa)s"
        params['empresa'] = empresa_selecionada
        
    # --- Query 1: Quantidade por Mês ---
    query1 = 'SELECT EXTRACT(MONTH FROM data_hora) AS mes, COUNT(*) AS "Registros"' + base_query + " GROUP BY mes ORDER BY mes"
    df1 = pd.read_sql(query1, engine, params=params)
    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df1['Mês'] = df1['mes'].map(meses_map)
    fig1 = px.bar(df1, x='Mês', y='Registros', 
                 title=f'Registros em {ano_selecionado} (Empresa: {empresa_selecionada})')

    # --- Query 2: Média de Peso por Mês (Sua rota /media_peso_por_mes) ---
    query2 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, AVG(peso_entrada) AS media" + base_query + " GROUP BY mes ORDER BY mes"
    df2 = pd.read_sql(query2, engine, params=params)
    df2['Mês'] = df2['mes'].map(meses_map)
    fig2 = px.line(df2, x='Mês', y='media', 
                 title=f'Média de Peso de Entrada em {ano_selecionado} (Empresa: {empresa_selecionada})', markers=True)
    fig2.update_layout(yaxis_title="Média de Peso Entrada (kg)")
    
    return fig1, fig2 # <--- RETORNA AS DUAS FIGURAS