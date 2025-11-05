from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from database import engine

template_theme = "cosmo" 

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

def fig_relacao_peso_volume(df, template):
    fig = px.scatter(
        df, x='quantidade', y='Média de Peso (kg)', text='setor',
        title="Relação: Média de Peso x Volume de Registros por Setor",
        labels={'quantidade': 'Volume (Contagem)', 'Média de Peso (kg)': 'Média de Peso (kg)'},
        hover_name='setor', template=template
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(height=600)

    return fig

def fig_media_por_setor(df, template):
    df_sorted = df.sort_values(by='Média de Peso (kg)', ascending=False)
    fig = px.bar(df_sorted, x='setor', y='Média de Peso (kg)', 
                 title="Média do Peso por Setor", template=template)
    fig.update_xaxes(tickangle=45) 

    return fig

def fig_contagem_por_setor(df, template):
    df_sorted = df.sort_values(by='quantidade', ascending=False)
    num_setores = len(df_sorted.index)
    dynamic_height = max(400, num_setores * 20)
    fig = px.bar(df_sorted, x='quantidade', y='setor', orientation='h', 
                 title="Volume de Registros por Setor", template=template)
    fig.update_layout(yaxis={'autorange': 'reversed'}, height=dynamic_height)
    return fig

layout = html.Div([
    html.H1('Análise de Setores'),
    html.P('Análises focadas nos locais onde houve recolhimento dos resíduos.'),
    
    

    dcc.RadioItems(
        id='filtro-tipo-visualizacao',
        options=[
            {'label': 'Relação (Peso x Volume)', 'value': 'relacao'},
            {'label': 'Rankings Individuais', 'value': 'individual'}
        ],
        value='relacao',
        inline=True,
        className="mb-3 dbc", 
        labelStyle={'margin-right': '25px'} 
    ),
    html.Hr(),
    
    html.Div(
        id='div-visualizacao-relacao',
        children=[
            dbc.Alert(
                [
                html.H5("O que este gráfico responde?", className="alert-heading"),
                html.P("Existem setores (bairros/locais) que se comportam de forma estranha ou 'fora da curva'?"),
                html.P("Este é um gráfico de detetive. Ele cruza duas informações: o número de viagens (horizontal) e o peso médio por viagem (vertical). Isso nos mostra padrões.")
                ],
            color="info", className="mb-3"
            ),

            dbc.Card(dbc.CardBody(dcc.Graph(id='grafico-relacao-setor')))
        ],
        className="mb-3"
    ),
    html.Div(
        id='div-visualizacao-individual',
        children=[
            dbc.Alert(
                [
                html.H5("O que este gráfico responde?", className="alert-heading"),
                html.P("Quais setores têm, em média, as coletas mais 'pesadas' (eficientes) e quais têm as mais 'leves'? Quais setores dão mais 'trabalho', ou seja, exigem o maior número de viagens e registros na balança?"),
                html.P("Queremos comparar a eficiência média entre os bairros.")
                ],
            color="info", className="mb-3"
            ),

            dbc.Card(dbc.CardBody(dcc.Graph(id='grafico-media-setor')), className="mb-3"),
            dbc.Card(dbc.CardBody(dcc.Graph(id='grafico-contagem-setor')), className="mb-3")
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
    else: 
        return {'display': 'none'}, {'display': 'block'}
    

@callback(
    [Output('grafico-relacao-setor', 'figure'),
     Output('grafico-media-setor', 'figure'),
     Output('grafico-contagem-setor', 'figure')],
    [Input('filtro-tipo-visualizacao', 'value')] 
)
def update_sector_graphs_theme(view_selected): 
    fig1 = fig_relacao_peso_volume(df_setores, template_theme)
    fig2 = fig_media_por_setor(df_setores, template_theme)
    fig3 = fig_contagem_por_setor(df_setores, template_theme)
    
    return fig1, fig2, fig3