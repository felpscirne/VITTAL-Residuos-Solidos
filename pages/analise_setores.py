from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

from database import engine

def load_sector_data():
    
    query = """
    SELECT 
        setor, 
        AVG(peso_embalagem_liquido_corrigido) as "Média de Peso (kg)",
        COUNT(*) as quantidade
    FROM registro 
    WHERE 
        setor IS NOT NULL AND
        setor != 'ACERTO DE PESO'
    GROUP BY setor
    """
    df = pd.read_sql(query, engine)
    return df

df_setores = load_sector_data()


# --- GRÁFICO 1: Relação Peso x Volume ---
def fig_relacao_peso_volume(df):
    fig = px.scatter(
        df,
        x='quantidade',
        y='Média de Peso (kg)',  
        text='setor',
        title="Relação: Média de Peso x Volume de Registros por Setor",
        labels={
            'quantidade': 'Volume de Registros (Contagem)', 
            'Média de Peso (kg)': 'Média de Peso Corrigido (kg)' 
        },
        hover_name='setor'
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(height=600)
    return fig


# --- GRÁFICO 2: Média por Setor ---
def fig_media_por_setor(df):
    df_sorted = df.sort_values(by='Média de Peso (kg)', ascending=False) # Corrigido
    
    fig = px.bar(df_sorted, 
                 x='setor', 
                 y='Média de Peso (kg)', 
                 title="Média do Peso por Setor")
    
    fig.update_xaxes(tickangle=45) 
    
    return fig


# --- GRÁFICO 3: Contagem por Setor  ---
def fig_contagem_por_setor(df):
    df_sorted = df.sort_values(by='quantidade', ascending=False)
    
    num_setores = len(df_sorted.index)
    dynamic_height = max(400, num_setores * 20)
    
    fig = px.bar(df_sorted, 
                 x='quantidade', 
                 y='setor', 
                 orientation='h', 
                 title="Volume de Registros por Setor")
    
    fig.update_layout(yaxis={'autorange': 'reversed'}, height=dynamic_height)
    
    return fig


layout = html.Div([
    html.H1('Análise de Setores'),
    html.P('Análises estáticas focadas nos setores, ou seja, nos locais onde houve recolhimento dos resíduos.'),
    
    dcc.RadioItems(
        id='filtro-tipo-visualizacao',
        options=[
            {'label': 'Relação (Peso x Volume)', 'value': 'relacao'},
            {'label': 'Rankings Individuais', 'value': 'individual'}
        ],
        value='relacao',  
        inline=True,      
        style={'margin-top': '20px', 'margin-bottom': '20px'}
    ),
    html.Hr(),
    
    html.Div(
        id='div-visualizacao-relacao',
        children=[
            html.H2('Análise de Relação (Peso x Volume)'),
            html.P("Este gráfico ajuda a identificar setores atípicos. "
                   "Por exemplo, setores no canto inferior direito têm "
                   "baixa média de peso, mas muitos registros."),
            dcc.Graph(
                id='grafico-relacao-setor',
                figure=fig_relacao_peso_volume(df_setores)
            )
        ]
    ),
    

    html.Div(
        id='div-visualizacao-individual',
        children=[
            html.H2('Rankings Individuais'),
            html.Div(className='row', children=[
                dcc.Graph(
                    id='grafico-media-setor',
                    figure=fig_media_por_setor(df_setores)
                ),
                html.Hr(),
                dcc.Graph(
                    id='grafico-contagem-setor',
                    figure=fig_contagem_por_setor(df_setores)
                )
            ])
        ]

    )
])


@callback(
    [Output('div-visualizacao-relacao', 'style'),
     Output('div-visualizacao-individual', 'style')],
    [Input('filtro-tipo-visualizacao', 'value')]
)
def toggle_visualizacao(view_selected):
    
    if view_selected == 'relacao':
        return {'display': 'block'}, {'display': 'none'}
    else: # view_selected == 'individual'
        return {'display': 'none'}, {'display': 'block'}