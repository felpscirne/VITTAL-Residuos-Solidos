from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# Service imports
from app.services.data_repository import (
    get_produtos_resumo, 
    get_produtos_options, 
    get_setores_options, 
    get_fornecedores_por_produto,
    get_produtos_por_setor
)
from app.services.ai_service import generate_analysis_component

# Load initial data
df_produtos = get_produtos_resumo() 

def fig_contagem_produtos(df, template):
    num_itens = len(df.index)
    dynamic_height = max(400, num_itens * 20)
    fig = px.bar(df, x='quantidade', y='produto', orientation='h',
                 title="Volume (Nº de Registros) por Produto",
                 template=template) 
    fig.update_layout(yaxis={'autorange': 'reversed'}, height=dynamic_height,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

# Load options
produtos_options = get_produtos_options()
setores_options = get_setores_options()

layout = dmc.Container([
    dmc.Title('Análise de Produtos', order=2),
    dmc.Text('Ranking geral dos tipos de resíduos e análises cruzadas (drill-down) por fornecedor e setor.', c="dimmed", mb="lg"),
    
    dmc.Divider(mb="lg"),

    dmc.Title("Visão Geral: Ranking de Produtos", order=3, mb="md"),
    
    dmc.Alert(
        children=[
            dmc.Title("Contexto", order=5),
            dmc.Text("Identifique os resíduos mais comuns e os mais raros para priorizar a gestão.")
        ],
        title="O que este gráfico responde?",
        color="blue",
        variant="light",
        mb="md",
        icon=DashIconify(icon="radix-icons:question-mark-circled")
    ),

    dmc.Card(
        dcc.Graph(id='grafico-contagem-produtos'),
        withBorder=True, shadow="sm", radius="md", p="md", mb="md"
    ),

    dmc.Button(
        "Explicar este ranking com IA", 
        id="btn-ia-produtos", 
        n_clicks=0, 
        variant="light", 
        color="violet", 
        leftSection=DashIconify(icon="radix-icons:magic-wand"),
        mb="md"
    ),
    dcc.Loading(html.Div(id='ia-output-produtos', style={"marginTop": "10px"})),

    dmc.Divider(my="xl"),
    
    dmc.Title("Drill-Down: Fornecedores por Produto", order=3, mb="md"),
    dmc.Alert("Ao selecionar um produto, veja quem movimenta ele.", color="gray", variant="light", mb="md"),
    
    dmc.Grid(
        children=[
            dmc.GridCol(
                dmc.Select(
                    label="Selecione um Produto",
                    placeholder="Escolha um produto...",
                    id='filtro-produto-para-fornecedor',
                    data=produtos_options,
                    value=produtos_options[0]['value'] if produtos_options else None
                ), span=6
            )
        ],
        mb="md"
    ),
    
    dmc.Card(
        dcc.Graph(id='grafico-produto-fornecedores'),
        withBorder=True, shadow="sm", radius="md", p="md", mb="md"
    ),

    dmc.Button(
        "Explicar Fornecedores com IA", 
        id="btn-ia-prod-forn", 
        n_clicks=0, 
        variant="light", 
        color="violet", 
        leftSection=DashIconify(icon="radix-icons:magic-wand"),
        mb="md"
    ),
    dcc.Loading(html.Div(id='ia-output-prod-forn', style={"marginTop": "10px"})),

    dmc.Divider(my="xl"),
    
    dmc.Title("Drill-Down: Produtos por Setor", order=3, mb="md"),
    dmc.Alert("Selecione um setor para ver o que é gerado lá.", color="gray", variant="light", mb="md"),
    
    dmc.Grid(
        children=[
            dmc.GridCol(
                dmc.Select(
                    label="Selecione um Setor",
                    placeholder="Escolha um setor...",
                    id='filtro-setor-para-produto',
                    data=setores_options,
                    value=setores_options[0]['value'] if setores_options else None
                ), span=6
            )
        ],
        mb="md"
    ),
    
    dmc.Card(
        dcc.Graph(id='grafico-setor-produtos'),
        withBorder=True, shadow="sm", radius="md", p="md", mb="md"
    ),

    dmc.Button(
        "Explicar Produtos deste Setor com IA", 
        id="btn-ia-setor-prod", 
        n_clicks=0, 
        variant="light", 
        color="violet", 
        leftSection=DashIconify(icon="radix-icons:magic-wand"),
        mb="md"
    ),
    dcc.Loading(html.Div(id='ia-output-setor-prod', style={"marginTop": "10px"}))

], fluid=True, p=0)


@callback(
    Output('grafico-contagem-produtos', 'figure'),
    [Input("mantine-provider", "forceColorScheme")]
)
def update_product_graph_theme(color_scheme):
    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"
    fig = fig_contagem_produtos(df_produtos, template)
    return fig

@callback(
    Output('grafico-produto-fornecedores', 'figure'),
    [Input('filtro-produto-para-fornecedor', 'value'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_prod_forn_graph(selected_product, color_scheme):
    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"
    
    df_drilldown = get_fornecedores_por_produto(selected_product, limit=None)
    
    fig = px.bar(df_drilldown, x='quantidade', y='fornecedor_cliente', orientation='h',
                 title=f"Fornecedores que movimentaram: {selected_product}",
                 template=template)
    fig.update_layout(yaxis={'autorange': 'reversed'},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

@callback(
    Output('grafico-setor-produtos', 'figure'),
    [Input('filtro-setor-para-produto', 'value'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_setor_prod_graph(selected_setor, color_scheme):
    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"
    
    df_drilldown = get_produtos_por_setor(selected_setor, limit=None)
    
    fig = px.bar(df_drilldown, x='quantidade', y='produto', orientation='h',
                 title=f"Produtos encontrados no Setor: {selected_setor}",
                 template=template)
    fig.update_layout(yaxis={'autorange': 'reversed'},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


@callback(
    Output('ia-output-produtos', 'children'),
    Input('btn-ia-produtos', 'n_clicks'),
    prevent_initial_call=True
)
def get_ia_produtos(n_clicks):
            
    dados_em_texto = df_produtos.head(10).to_markdown(index=False)

    prompt = f"""
    Você é um analista de dados da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar o ranking dos 10 principais produtos (resíduos) coletados.

    Aqui estão os dados:
    {dados_em_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  Qual é o resíduo mais dominante e o que isso significa para a coleta?
    2.  Existem resíduos nesta lista (ex: Hospitalar, Reciclável) que deveriam ter uma coleta separada?
    3.  Qual a principal recomendação para um gestor de resíduos ao ver este ranking?
    
    Responda em um texto organizado e de linguagem clara. Não diga as perguntas. Não se apresente.
    """
    
    return generate_analysis_component(prompt)

@callback(
    Output('ia-output-prod-forn', 'children'),
    Input('btn-ia-prod-forn', 'n_clicks'),
    State('filtro-produto-para-fornecedor', 'value'),
    prevent_initial_call=True
)
def get_ia_prod_forn(n_clicks, selected_product):
            
    df_drilldown = get_fornecedores_por_produto(selected_product, limit=None)
    dados_em_texto = df_drilldown.to_markdown(index=False)

    # Prompt
    prompt = f"""
    Você é um analista de dados. Sua tarefa é analisar quais fornecedores
    movimentam um produto específico.
    
    - Produto em Foco: "{selected_product}"
    
    Ranking de Fornecedores/Empresas que movimentaram este produto:
    {dados_em_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  Quem é o principal movimentador deste produto?
    2.  Isso é esperado? (Ex: É esperado que 'Empresa de Coleta X' domine 'RESÍDUO DOMICILIAR').
    3.  Qual insight um gestor pode tirar desta relação?
    
    Responda em um texto organizado e de linguagem clara. Não se apresente.
    """
    
    return generate_analysis_component(prompt)

@callback(
    Output('ia-output-setor-prod', 'children'),
    Input('btn-ia-setor-prod', 'n_clicks'),
    State('filtro-setor-para-produto', 'value'),
    prevent_initial_call=True
)
def get_ia_setor_prod(n_clicks, selected_setor):
            
    df_drilldown = get_produtos_por_setor(selected_setor, limit=None)
    dados_em_texto = df_drilldown.to_markdown(index=False)

    # Prompt 
    prompt = f"""
    Você é um analista de dados. Sua tarefa é analisar quais produtos (resíduos)
    são mais comuns em um setor específico.
    
    - Setor em Foco: "{selected_setor}"
    
    Ranking de Produtos encontrados neste setor:
    {dados_em_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  Qual é o resíduo predominante neste setor?
    2.  A composição de resíduos deste setor é a esperada? (Ex: É normal o setor 'HOSPITAL' ter 'RESÍDUO HOSPITALAR'?).
    3.  Qual insight um gestor de coleta pode tirar desta informação? (Ex: necessidade de coleta especial, etc.)
    
    Responda em um texto organizado e de linguagem clara. Não diga as perguntas. Não se apresente.
    """
    
    return generate_analysis_component(prompt)