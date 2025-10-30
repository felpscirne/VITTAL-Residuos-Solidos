from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

from database import engine, get_anos_options


def get_setores_options():
    """Busca setores únicos para o filtro dropdown."""
    try:
        query = "SELECT DISTINCT setor FROM registro WHERE setor IS NOT NULL AND setor != 'ACERTO DE PESO' ORDER BY setor"
        df = pd.read_sql(query, engine)
        options = [{'label': setor, 'value': setor} for setor in df['setor']]
        valor_inicial = options[0]['value'] if options else None
        return options, valor_inicial
    except Exception as e:
        print(f"Erro ao buscar setores: {e}")
        return [], None

# Carrega as opções de filtro quando o app inicia
anos_options, ano_inicial = get_anos_options()
setores_options, setor_inicial = get_setores_options()

# --- Layout da Página ---
layout = html.Div([
    html.H1('Análise de Média de Peso por Setor'),
    html.P('Selecione um setor e um ano para ver a variação da média de peso ao longo dos meses.'),
    
    # --- Filtros da Página ---
    html.Div(className='filtros-pagina', children=[
        html.Div([
            html.Label('Selecione o Setor:'),
            dcc.Dropdown(
                id='filtro-setor-media',
                options=setores_options,
                value=setor_inicial, # Define o primeiro setor como inicial
                clearable=False
            )
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            html.Label('Selecione o Ano:'),
            dcc.Dropdown(
                id='filtro-ano-media',
                options=anos_options,
                value=ano_inicial, # Define o ano mais recente como inicial
                clearable=False
            )
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
    ]),
    
    # O Gráfico de Linha
    dcc.Graph(id='grafico-media-setor-temporal')
])


@callback(
    Output('grafico-media-setor-temporal', 'figure'),
    [Input('filtro-setor-media', 'value'),
     Input('filtro-ano-media', 'value')]
)
def update_graph(setor_selecionado, ano_selecionado):
    
    if not setor_selecionado or not ano_selecionado:
        return px.line(title="Por favor, selecione um setor e um ano.")

    
    query = """
    SELECT 
        EXTRACT(MONTH FROM data_hora) as mes,
        AVG(peso_embalagem_liquido_corrigido) as media_peso
    FROM registro
    WHERE 
        setor = %(setor)s AND 
        EXTRACT(YEAR FROM data_hora) = %(ano)s
    GROUP BY mes
    ORDER BY mes
    """
    
    params = {'setor': setor_selecionado, 'ano': ano_selecionado}
    
    df = pd.read_sql(query, engine, params=params)
    
    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df['mes_nome'] = df['mes'].map(meses_map)
    
    df = df.sort_values(by='mes')

    fig = px.line(
        df, 
        x='mes_nome', 
        y='media_peso', 
        markers=True, 
        title=f"Média Mensal de Peso para: {setor_selecionado} ({ano_selecionado})"
    )
    
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Média de Peso (kg)"
    )
    
    return fig