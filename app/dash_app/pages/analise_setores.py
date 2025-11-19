from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

from app.database import engine, get_anos_options 

from app.services.ai_service import generate_analysis_component

template_theme_light = "cosmo" 
template_theme_dark = "plotly_dark"

def load_sector_data():
    query = """
    SELECT 
        setor, 
        AVG(peso_embalagem_liquido_corrigido) as "Média de Peso (kg)",
        COUNT(*) as quantidade
    FROM registro 
    WHERE 
        setor IS NOT NULL AND
        setor != 'ACERTO DE PESO' AND
        setor != 'CANDIOTA'
    GROUP BY setor
    """
    df = pd.read_sql(query, engine)
    return df

df_setores = load_sector_data()

def fig_relacao_peso_volume(df, template):
    fig = px.scatter(
        df, x='quantidade', y='Média de Peso (kg)',
        title="Relação: Média de Peso x Volume de Registros por Setor",
        labels={'quantidade': 'Volume (Contagem)', 'Média de Peso (kg)': 'Média de Peso (kg)'},
        hover_name='setor', template=template
    )
    fig.update_layout(height=600, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def fig_media_por_setor(df, template):
    df_sorted = df.sort_values(by='Média de Peso (kg)', ascending=False)
    fig = px.bar(df_sorted, x='setor', y='Média de Peso (kg)', 
                 title="Média do Peso por Setor", template=template)
    fig.update_xaxes(tickangle=45) 
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def fig_contagem_por_setor(df, template):
    df_sorted = df.sort_values(by='quantidade', ascending=False)
    num_setores = len(df_sorted.index)
    dynamic_height = max(400, num_setores * 20)
    fig = px.bar(df_sorted, x='quantidade', y='setor', orientation='h', 
                 title="Volume de Registros por Setor", template=template)
    fig.update_layout(yaxis={'autorange': 'reversed'}, height=dynamic_height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


setores_options_temporal = sorted([
    {'label': s, 'value': s} for s in df_setores['setor'].unique()
], key=lambda x: x['label'])

anos_options_temporal, ano_inicial_temporal = get_anos_options()
setor_inicial_temporal = setores_options_temporal[0]['value'] if setores_options_temporal else None


layout = html.Div([
    html.H1('Análise de Setores (Visão Geral e Temporal)'),
    html.P('Compare todos os setores entre si ou analise a tendência de um setor específico ao longo do tempo.'),
    html.Hr(),

    html.H2("Visão Geral: Comparativo entre Setores"),
    
    dcc.RadioItems(
        id='filtro-tipo-visualizacao-setores', 
        options=[
            {'label': 'Relação (Peso x Volume)', 'value': 'relacao'},
            {'label': 'Rankings Individuais', 'value': 'individual'}
        ],
        value='relacao',
        inline=True,
        className="mb-3 dbc", 
        labelStyle={'margin-right': '25px'} 
    ),
    
   
    
    html.Div(
        id='div-visualizacao-relacao-setores', 
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
        id='div-visualizacao-individual-setores', 
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
    ),
    dbc.Button("🤖 Explicar esta visão geral", id="btn-ia-setores-overview", n_clicks=0, color="primary", outline=True, size="sm", className="mb-3"),
    dcc.Loading(html.Div(id='ia-output-setores-overview')),  
   
    html.Hr(className="mt-5"),
    html.H2("Drill-Down: Análise Temporal por Setor"),
    
    dbc.Alert(
        [   html.H5("O que esta análise responde?", className="alert-heading"),
            html.P("Esta seção permite um 'zoom' em um setor específico. Ela compara um setor consigo mesmo ao longo do tempo para ver como sua média de peso (eficiência) varia mês a mês."),
            html.P("Existem tendências sazonais ou mudanças repentinas que devemos observar?")
        ],
        color="info", className="mb-3"
    ),

    dbc.Row(
        [
            dbc.Col(
                [
                    html.Label('Selecione o Setor:'),
                    dcc.Dropdown(
                        id='filtro-setor-temporal', 
                        options=setores_options_temporal,
                        value=setor_inicial_temporal,
                        clearable=False
                    )
                ],
                md=6
            ),
            dbc.Col(
                [
                    html.Label('Selecione o Ano:'),
                    dcc.Dropdown(
                        id='filtro-ano-temporal', 
                        options=anos_options_temporal,
                        value=ano_inicial_temporal,
                        clearable=False
                    )
                ],
                md=6
            ),
        ],
        className="dbc mb-3" 
    ),
    


    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-media-setor-temporal') 
        ])
    ),
    dbc.Button("🤖 Explicar este setor", id="btn-ia-setores-temporal", n_clicks=0, color="primary", outline=True, size="sm", className="mb-3"),
    dcc.Loading(html.Div(id='ia-output-setores-temporal')), 
])



@callback(
    [Output('div-visualizacao-relacao-setores', 'style'),
     Output('div-visualizacao-individual-setores', 'style')],
    [Input('filtro-tipo-visualizacao-setores', 'value')]
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
    [Input("theme-switch", "value")] 
)
def update_overview_graphs_theme(switch_is_light): 
    template = template_theme_light if switch_is_light else template_theme_dark
    
    fig1 = fig_relacao_peso_volume(df_setores, template)
    fig2 = fig_media_por_setor(df_setores, template)
    fig3 = fig_contagem_por_setor(df_setores, template)
    
    return fig1, fig2, fig3

@callback(
    Output('grafico-media-setor-temporal', 'figure'),
    [Input('filtro-setor-temporal', 'value'),
     Input('filtro-ano-temporal', 'value'),
     Input("theme-switch", "value")]
)
def update_temporal_graph(setor_selecionado, ano_selecionado, switch_is_light):
    
    template = template_theme_light if switch_is_light else template_theme_dark
    
    if not setor_selecionado or not ano_selecionado:
        fig_vazia = px.line(title="Por favor, selecione um setor e um ano.", template=template)
        fig_vazia.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig_vazia

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
        title=f"Média Mensal de Peso Corrigido para: {setor_selecionado} ({ano_selecionado})",
        template=template
    )
    
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Média de Peso Corrigido (kg)",
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig


@callback(
    Output('ia-output-setores-overview', 'children'),
    Input('btn-ia-setores-overview', 'n_clicks'),
    prevent_initial_call=True
)
def get_ia_setores_overview(n_clicks):
            
    # Prepara os dados (Top 5 e Piores 5)
    df_media = df_setores.sort_values(by='Média de Peso (kg)', ascending=False)
    df_volume = df_setores.sort_values(by='quantidade', ascending=False)
    
    dados_em_texto = f"""
    Dados de Análise de Setores (excluindo Candiota e Acerto de Peso):

    TOP 5 - MAIOR MÉDIA DE PESO (kg) POR COLETA:
    {df_media.head(5).to_markdown(index=False)}

    TOP 5 - MAIOR VOLUME (Nº DE COLETAS):
    {df_volume.head(5).to_markdown(index=False)}
    """

    # Prompt Visão Geral
    prompt = f"""
    Você é um analista de dados da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar os dados de Visão Geral dos setores de coleta de resíduos.
    
    Aqui estão os dados:
    {dados_em_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  O que os setores no "Top 5 de Média de Peso" nos dizem? (Estes são os mais eficientes?)
    2.  O que os setores no "Top 5 de Volume" nos dizem? (Estes são os que dão mais trabalho?)
    3.  Existe alguma sobreposição óbvia (ex: um setor está em ambas as listas)?
    4.  Qual a relação entre volume de coletas e eficiência em peso observada nestes dados?
    4.  Qual o principal insight para quem vê esses rankings?
    
    Responda em um texto organizado e de linguagem clara. Sem falar as perguntas. Não se apresente.
    """
    
    return generate_analysis_component(prompt)

@callback(
    Output('ia-output-setores-temporal', 'children'),
    Input('btn-ia-setores-temporal', 'n_clicks'),
    [State('filtro-setor-temporal', 'value'),
     State('filtro-ano-temporal', 'value')],
    prevent_initial_call=True
)
def get_ia_setores_temporal(n_clicks, setor_selecionado, ano_selecionado):
            
    query = """
    SELECT EXTRACT(MONTH FROM data_hora) as mes, AVG(peso_embalagem_liquido_corrigido) as media_peso_kg
    FROM registro
    WHERE setor = %(setor)s AND EXTRACT(YEAR FROM data_hora) = %(ano)s
    GROUP BY mes ORDER BY mes
    """
    params = {'setor': setor_selecionado, 'ano': ano_selecionado}
    df = pd.read_sql(query, engine, params=params)
    
    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df['mes'] = df['mes'].map(meses_map)
    df['media_peso_kg'] = df['media_peso_kg'].round(2)
    
    dados_em_texto = df.to_markdown(index=False)

    # Prompt Temporal
    prompt = f"""
    Você é um analista de dados da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar a tendência temporal de um setor específico.

    Dados da Análise:
    - Setor em Foco: "{setor_selecionado}"
    - Ano: {ano_selecionado}
    
    Tabela de Média de Peso (kg) por Mês:
    {dados_em_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  Qual é a tendência geral deste setor ao longo do ano? (Está estável, melhorando, piorando?)
    2.  Existem meses com picos ou quedas repentinas que merecem investigação?
    3.  Qual ação um gestor de logística deveria tomar com base nessa tendência?
    
    Responda em um texto organizado e de linguagem clara. Sem falar as perguntas. Não se apresente.
    """
    
    return generate_analysis_component(prompt)