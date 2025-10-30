from dash import dcc, html
import plotly.express as px
import pandas as pd

from database import engine


def fig_media_por_setor():
    query = """
    SELECT 
        setor, 
        AVG(peso_embalagem_liquido_corrigido) as media_corrigida
    FROM registro 
    WHERE 
        setor IS NOT NULL AND
        setor != 'ACERTO DE PESO'
    GROUP BY setor 
    ORDER BY media_corrigida DESC
    """
    df = pd.read_sql(query, engine)
    num_setores = len(df.index)
    dynamic_height = max(400, num_setores * 20)
    fig = px.bar(df, 
                 x='setor', 
                 y='media_corrigida', 
                 title="Média do Peso Corrigido por Setor")
    #fig.update_layout(height=dynamic_height)
    return fig


def fig_contagem_por_setor():
    query = """
    SELECT 
        setor, 
        COUNT(*) as quantidade
    FROM registro 
    WHERE 
        setor IS NOT NULL AND
        setor != 'ACERTO DE PESO'
    GROUP BY setor 
    ORDER BY quantidade DESC  
    """
    df = pd.read_sql(query, engine)
    num_setores = len(df.index)
    dynamic_height = max(400, num_setores * 20)
    
   
    fig = px.bar(df, 
                 x='quantidade', 
                 y='setor', 
                 orientation='h',  
                 title="Volume de Registros por Setor")
    
    fig.update_layout(yaxis={'autorange': 'reversed'}, height=dynamic_height)
    
    return fig


layout = html.Div([
    html.H1('Análise de Setores'),
    html.P('Análises estáticas focadas nos setores.'),
    html.Hr(),
    
    html.Div(className='row', children=[
        dcc.Graph(
            id='grafico-media-setor',
            figure=fig_media_por_setor(),
            # style={'display': 'inline-block', 'width': '50%'}
        ),
        dcc.Graph(
            id='grafico-contagem-setor',
            figure=fig_contagem_por_setor(),
            # style={'display': 'inline-block', 'width': '50%'}
        )
    ])
])