from dash import dcc, html
import plotly.express as px
import pandas as pd


from database import engine


def carregar_kpis():
    
    query = """
    SELECT
        COUNT(*) AS total_registros,
        MIN(data_hora) AS data_inicio,
        MAX(data_hora) AS data_fim
    FROM registro
    """
    try:
        df = pd.read_sql(query, engine)
        kpis = df.iloc[0]
        return {
            'total': kpis['total_registros'],
            'inicio': kpis['data_inicio'].strftime('%d/%m/%Y'),
            'fim': kpis['data_fim'].strftime('%d/%m/%Y')
        }
    except Exception as e:
        print(f"Erro ao carregar KPIs: {e}")
        return {'total': 'N/D', 'inicio': 'N/D', 'fim': 'N/D'}

def fig_qtde_por_ano():
    query = "SELECT EXTRACT(YEAR FROM data_hora) AS ano, COUNT(*) AS qtde FROM registro GROUP BY ano ORDER BY ano"
    df = pd.read_sql(query, engine)
    df['ano'] = df['ano'].astype(str) 
    fig = px.bar(df, x='ano', y='qtde', title="Total de Registros por Ano")
    return fig

def fig_top_produtos():
    
    query = """
    SELECT produto, COUNT(*) AS qtde 
    FROM registro 
    GROUP BY produto 
    ORDER BY qtde DESC 
    LIMIT 10
    """
    df = pd.read_sql(query, engine)
    fig = px.pie(df, names='produto', values='qtde', title="Top 10 Produtos (Volume de Registros)")
    return fig

kpi_data = carregar_kpis()
fig_ano = fig_qtde_por_ano()
fig_produtos = fig_top_produtos()

# Layout da Página de Overview

layout = html.Div([
    html.H1('Visão Geral do Dashboard'),
    html.P('Resumo dos principais indicadores de pesagem.'),
    
    
    html.Div(className='kpi-container', children=[
        html.Div(className='kpi-card', children=[
            html.H3(kpi_data['total']),
            html.P('Total de Registros')
        ]),
        html.Div(className='kpi-card', children=[
            html.H3(kpi_data['inicio']),
            html.P('Data de Início')
        ]),
        html.Div(className='kpi-card', children=[
            html.H3(kpi_data['fim']),
            html.P('Data de Fim')
        ]),
    ]),
    
    html.Hr(),
    
    # --- Seção de Gráficos ---
    html.Div(className='row', children=[
        dcc.Graph(
            id='overview-grafico-ano',
            figure=fig_ano,
            style={'display': 'inline-block', 'width': '50%'}
        ),
        dcc.Graph(
            id='overview-grafico-produtos',
            figure=fig_produtos,
            style={'display': 'inline-block', 'width': '50%'}
        )
    ])
])