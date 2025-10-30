from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from database import engine, get_anos_options

template_theme = "cosmo" 

anos_options, ano_inicial = get_anos_options()
query_empresas = "SELECT DISTINCT fornecedor_cliente FROM registro WHERE fornecedor_cliente IS NOT NULL ORDER BY fornecedor_cliente"

empresas_df = pd.read_sql(query_empresas, engine)

empresas_options = [{'label': emp, 'value': emp} for emp in empresas_df['fornecedor_cliente']]
empresas_options.insert(0, {'label': 'Todas as Empresas', 'value': 'todas'})


layout = html.Div([
    html.H1('Análise Mensal (Volume e Peso)'),
    
   
    dbc.Row(
        [
            dbc.Col(
                [
                    html.Label('Selecione o Ano:'),
                    dcc.Dropdown(
                        id='filtro-ano-qtde',
                        options=anos_options,
                        value=ano_inicial,
                        clearable=False
                    )
                ],
                md=6 
            ),
            dbc.Col(
                [
                    html.Label('Selecione a Empresa:'),
                    dcc.Dropdown(
                        id='filtro-empresa-qtde',
                        options=empresas_options,
                        value='todas'
                    )
                ],
                md=6
            ),
        ],
        className="dbc mb-3"
    ),
    
    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-qtde-por-mes')
        ]),
        className="mb-3"
    ),
    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-media-peso-por-mes')
        ]),
        className="mb-3"
    )
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
    
    query1 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, COUNT(*) AS qtde" + base_query + " GROUP BY mes ORDER BY mes"
    df1 = pd.read_sql(query1, engine, params=params)
    
    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    
    df1['mes_nome'] = df1['mes'].map(meses_map)
    
    fig1 = px.bar(df1, x='mes_nome', y='qtde', 
                 title=f'Registros em {ano_selecionado} (Empresa: {empresa_selecionada})',
                 template=template_theme) 
    
    query2 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, AVG(peso_entrada) AS media" + base_query + " GROUP BY mes ORDER BY mes"
    df2 = pd.read_sql(query2, engine, params=params)
    
    df2['mes_nome'] = df2['mes'].map(meses_map)
    
    fig2 = px.line(df2, x='mes_nome', y='media', 
                 title=f'Média de Peso de Entrada em {ano_selecionado} (Empresa: {empresa_selecionada})', markers=True,
                 template=template_theme) 
    
    fig2.update_layout(yaxis_title="Média de Peso Entrada (kg)")
    
    return fig1, fig2