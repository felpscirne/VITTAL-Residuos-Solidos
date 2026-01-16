from dash import dcc, html, callback, no_update
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.database import engine, get_anos_options
from app.services.ai_service import generate_analysis_component

template_theme_light = "cosmo" # Ou seu tema
template_theme_dark = "plotly_dark"

def load_company_data():
    query = """
    SELECT 
        fornecedor_cliente, 
        COUNT(*) as quantidade,
        SUM(peso_embalagem_liquido_corrigido) as peso_total
    FROM registro 
    WHERE fornecedor_cliente IS NOT NULL
    GROUP BY fornecedor_cliente 
    ORDER BY quantidade DESC
    """
    df = pd.read_sql(query, engine)
    return df

# df_empresas = load_company_data() 


anos_options, ano_inicial = get_anos_options()
# empresas_options = sorted([
#     {'label': s, 'value': s} for s in df_empresas['fornecedor_cliente'].unique()
# ], key=lambda x: x['label'])
# empresas_options.insert(0, {'label': 'Todas as Empresas', 'value': 'todas'})

def get_empresas_options_dynamic():
    df = load_company_data()
    if df.empty: return [{'label': 'Todas as Empresas', 'value': 'todas'}]
    
    opts = sorted([{'label': s, 'value': s} for s in df['fornecedor_cliente'].unique()], key=lambda x: x['label'])
    opts.insert(0, {'label': 'Todas as Empresas', 'value': 'todas'})
    return opts


def fig_contagem_empresas(df, template):
    num_itens = len(df.index)
    dynamic_height = max(400, num_itens * 20)
    fig = px.bar(df, x='quantidade', y='fornecedor_cliente', orientation='h',
                 title="Volume (Nº de Registros) por Empresa/Entidade",
                 template=template)
    fig.update_layout(yaxis={'autorange': 'reversed'}, height=dynamic_height,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

layout = html.Div([
    dmc.Title('Análise de Empresas e Entidades', order=2),
    dmc.Text('Compare todas as empresas/entidades ou analise a tendência de uma específica ao longo do tempo.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Title("Visão Geral: Ranking de Empresas", order=3, my="sm"),
    dmc.Alert(
        "Quais empresas, entidades ou secretarias mais usam o nosso sistema de pesagem? Quem são os maiores players no nosso ecossistema de resíduos?",
        title="O que este gráfico responde?",
        color="ifsc-green",
        variant="light",
        icon=DashIconify(icon="radix-icons:info-circled"),
        mb="md"
    ),
    
    dmc.Card(
        children=[
            dcc.Graph(id='grafico-contagem-empresas')
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),

    dmc.Button(
        "🤖 Explicar este ranking", 
        id="btn-ia-empresas-ranking", 
        n_clicks=0, 
        variant="outline", 
        color="indigo", 
        leftSection=DashIconify(icon="fluent:bot-24-regular"),
        size="compact-sm",
        mb="md"
    ),
    dcc.Loading(html.Div(id='ia-output-empresas-ranking')), 

    dmc.Divider(label="Análise Temporal", labelPosition="center", my="xl"),
    
    dmc.Title("Drill-Down: Análise Mensal por Empresa", order=3, my="sm"),
    dmc.Alert(
        "Como o volume e a eficiência (peso médio) de uma empresa ou entidade específica mudam ao longo do ano? Existem tendências sazonais ou padrões notáveis?",
        title="O que esta análise responde?",
        color="ifsc-green",
        variant="light",
        icon=DashIconify(icon="akar-icons:statistic-up"),
        mb="md"
    ),
    
    dmc.SimpleGrid(
        cols={"base": 1, "sm": 2},
        spacing="md",
        children=[
            dmc.Select(
                label="Selecione o Ano",
                description="Filtrar dados por ano fiscal",
                id='filtro-ano-empresa',
                data=[], # Dynamic load
                value=None, 
                clearable=False,
                leftSection=DashIconify(icon="clarity:calendar-line")
            ),
            dmc.Select(
                label="Selecione a Empresa",
                description="Escolha uma entidade ou 'Todas'",
                id='filtro-empresa-temporal',
                # data=empresas_options, # Dynamic load needed
                data=[],
                value='todas',
                searchable=True,
                nothingFoundMessage="Nenhuma empresa encontrada",
                leftSection=DashIconify(icon="domain")
            ),
        ],
        mb="md"
    ),

    dmc.SimpleGrid(
        cols={"base": 1, "md": 2},
        spacing="md",
        children=[
            dmc.Card(
                children=[
                    dcc.Graph(id='grafico-qtde-por-mes-empresa')
                ],
                withBorder=True,
                shadow="sm",
                radius="md"
            ),
            dmc.Card(
                children=[
                    dcc.Graph(id='grafico-media-peso-por-mes-empresa')
                ],
                withBorder=True,
                shadow="sm",
                radius="md"
            ),
        ],
        mb="md"
    ),

    dmc.Button(
        "🤖 Explicar Tendência", 
        id="btn-ia-empresas-temporal", 
        n_clicks=0, 
        variant="outline", 
        color="indigo", 
        leftSection=DashIconify(icon="fluent:bot-24-regular")
    ),
    dcc.Loading(html.Div(id='ia-output-empresas-temporal')), 

])


@callback(
    Output('filtro-empresa-temporal', 'data'),
    Input('url', 'pathname')
)
def update_empresas_dropdown(pathname):
    if pathname == '/analise-empresas':
        return get_empresas_options_dynamic()
    return no_update

@callback(
    [Output('filtro-ano-empresa', 'data'),
     Output('filtro-ano-empresa', 'value')],
    Input('url', 'pathname')
)
def update_anos_dropdown_empresas(pathname):
    if pathname == '/analise-empresas':
        options, initial_val = get_anos_options()
        # Ensure we return valid format (options list, value)
        if not options:
            return [], None
        
        # If no initial_val returned but options exist, pick first
        if not initial_val and options:
             initial_val = options[0]['value']
             
        return options, initial_val
        
    return no_update, no_update

@callback(
    Output('grafico-contagem-empresas', 'figure'),
    [Input('url', 'pathname'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_empresas_main_graph(pathname, color_scheme):
    if pathname != '/analise-empresas': return no_update

    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"

    df = load_company_data()
    if df.empty:
        return px.bar(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    return fig_contagem_empresas(df, template)

# @callback(
#     Output('grafico-contagem-empresas', 'figure'),
#     [Input("theme-switch", "value")]
# )
# def update_company_rank_graph_theme(switch_is_light):
#     template = template_theme_light if switch_is_light else template_theme_dark
#     fig = fig_contagem_empresas(df_empresas, template)
#     return fig

@callback(
    [Output('grafico-qtde-por-mes-empresa', 'figure'),
     Output('grafico-media-peso-por-mes-empresa', 'figure')],
    [Input('filtro-ano-empresa', 'value'),
     Input('filtro-empresa-temporal', 'value'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_temporal_graphs(ano_selecionado, empresa_selecionada, color_scheme):
    
    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"
    
    # Handle initial loading state where inputs might be None
    if not ano_selecionado:
        empty_fig = px.bar(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", title="Aguardando seleção de ano...")
        return empty_fig, empty_fig

    base_query = " FROM registro WHERE EXTRACT(YEAR FROM data_hora) = %(ano)s"
    params = {'ano': ano_selecionado}
    
    if empresa_selecionada and empresa_selecionada != 'todas':
        base_query += " AND fornecedor_cliente = %(empresa)s"
        params['empresa'] = empresa_selecionada
        
    # Query 1
    query1 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, COUNT(*) AS qtde" + base_query + " GROUP BY mes ORDER BY mes"
    df1 = pd.read_sql(query1, engine, params=params)
    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df1['mes_nome'] = df1['mes'].map(meses_map)
    fig1 = px.bar(df1, x='mes_nome', y='qtde', 
                 title=f'Volume de Registros ({empresa_selecionada}, {ano_selecionado})',
                 template=template)
    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    # Query 2
    query2 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, AVG(peso_entrada) AS media" + base_query + " GROUP BY mes ORDER BY mes"
    df2 = pd.read_sql(query2, engine, params=params)
    df2['mes_nome'] = df2['mes'].map(meses_map)
    fig2 = px.line(df2, x='mes_nome', y='media', 
                 title=f'Média de Peso de Entrada ({empresa_selecionada}, {ano_selecionado})', markers=True,
                 template=template) 
    fig2.update_layout(yaxis_title="Média de Peso Entrada (kg)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    
    return fig1, fig2


@callback(
    Output('ia-output-empresas-ranking', 'children'),
    Input('btn-ia-empresas-ranking', 'n_clicks'),
    prevent_initial_call=True
)
def get_ia_empresas_ranking(n_clicks):
    
    df = load_company_data()
    dados_em_texto = df.head(10).to_markdown(index=False) 


    # Prompt de empresas
    prompt = f"""
    Você é um analista de dados da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar o ranking das 10 principais empresas/entidades que usam o sistema de pesagem.
    
    Aqui estão os dados:
    {dados_em_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  Quais são as 3 principais entidades e o que isso significa? (São empresas de coleta, secretarias, etc.?)
    2.  Qual a principal recomendação para quem vê este ranking de volume?

    Responda em um texto organizado e de linguagem clara. Não fale as perguntas. Não se apresente.
    """
    
    return generate_analysis_component(prompt)

@callback(
    Output('ia-output-empresas-temporal', 'children'),
    Input('btn-ia-empresas-temporal', 'n_clicks'),
    [State('filtro-ano-empresa', 'value'),
     State('filtro-empresa-temporal', 'value')],
    prevent_initial_call=True
)
def get_ia_empresas_temporal(n_clicks, ano, empresa):
            
    base_query = " FROM registro WHERE EXTRACT(YEAR FROM data_hora) = %(ano)s"
    params = {'ano': ano}
    if empresa != 'todas':
        base_query += " AND fornecedor_cliente = %(empresa)s"
        params['empresa'] = empresa
    
    query1 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, COUNT(*) AS qtde_registros" + base_query + " GROUP BY mes ORDER BY mes"
    df_volume = pd.read_sql(query1, engine, params=params)
    
    query2 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, AVG(peso_entrada) AS media_peso_kg" + base_query + " GROUP BY mes ORDER BY mes"
    df_media_peso = pd.read_sql(query2, engine, params=params)

    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df_volume['mes'] = df_volume['mes'].map(meses_map)
    df_media_peso['mes'] = df_media_peso['mes'].map(meses_map)
    df_media_peso['media_peso_kg'] = df_media_peso['media_peso_kg'].round(2)

    dados_volume_texto = df_volume.to_markdown(index=False)
    dados_media_peso_texto = df_media_peso.to_markdown(index=False)

    prompt = f"""
    Você é um analista de dados da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar a tendência temporal de uma empresa ou entidade, com base nos dados que o usuário está vendo.

    Dados da Análise:
    - Entidade em Foco: "{empresa}"
    - Ano: {ano}

    Tabela 1: Volume de Registros (Nº de Viagens) por Mês:
    {dados_volume_texto}

    Tabela 2: Média de Peso (Eficiência) por Viagem (kg) por Mês:
    {dados_media_peso_texto}

    Por favor, gere uma análise em markdown que "explique os resultados" que o usuário vê nos gráficos:
    1.  Qual é a tendência de **Volume** (Tabela 1) para esta entidade ao longo do ano? (Existem picos ou quedas sazonais?)
    2.  Qual é a tendência da **Média de Peso** (Tabela 2)? (A eficiência está aumentando, diminuindo, é instável?)
    3.  **Análise Crítica:** Elas estão relacionadas? (Ex: o volume subiu em Junho, mas a eficiência caiu? Isso é bom ou ruim?)
    4.  Qual a principal recomendação para quem monitora esta entidade?
    
    Responda em um texto organizado e de linguagem clara. Sem falar as perguntas. Não se apresente.
    """
    
    return generate_analysis_component(prompt)
