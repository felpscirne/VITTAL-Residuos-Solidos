from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

from app.database import engine
from services.ai_service import client, gemini_configurado, MODEL_NAME 

template_theme_light = "cosmo" 
template_theme_dark = "plotly_dark"

def load_product_data():
    query = """
    SELECT 
        produto, 
        COUNT(*) as quantidade,
        SUM(peso_embalagem_liquido_corrigido) as peso_total
    FROM registro 
    WHERE produto IS NOT NULL
    GROUP BY produto 
    ORDER BY quantidade DESC
    """
    df = pd.read_sql(query, engine)
    return df

df_produtos = load_product_data() 

def fig_contagem_produtos(df, template):
    num_itens = len(df.index)
    dynamic_height = max(400, num_itens * 20)
    fig = px.bar(df, x='quantidade', y='produto', orientation='h',
                 title="Volume (Nº de Registros) por Produto",
                 template=template) 
    fig.update_layout(yaxis={'autorange': 'reversed'}, height=dynamic_height,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def get_produtos_options():
    try:
        df = pd.read_sql("SELECT DISTINCT produto FROM registro WHERE produto IS NOT NULL ORDER BY produto", engine)
        return [{'label': p, 'value': p} for p in df['produto']]
    except:
        return []

def get_setores_options():
    try:
        query = "SELECT DISTINCT setor FROM registro WHERE setor IS NOT NULL AND setor != 'ACERTO DE PESO' AND setor != 'CANDIOTA' ORDER BY setor"
        df = pd.read_sql(query, engine)
        return [{'label': s, 'value': s} for s in df['setor']]
    except:
        return []

produtos_options = get_produtos_options()
setores_options = get_setores_options()

layout = html.Div([
    html.H1('Análise de Produtos'),
    html.P('Ranking geral dos tipos de resíduos e análises cruzadas (drill-down) por fornecedor e setor.'),
    html.Hr(),

    html.H2("Visão Geral: Ranking de Produtos"),
    dbc.Alert(
        [
            html.H5("O que este gráfico responde?", className="alert-heading"),
            html.P("Quais são nossos resíduos mais comuns e quais são os mais raros, em ordem? "
                   "Isso ajuda a identificar o que realmente domina nossas coletas.")
        ], color="info", className="mb-3"
    ),


    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-contagem-produtos') 
        ]),
        className="mb-3"
    ),

    dbc.Button("🤖 Explicar este ranking", id="btn-ia-produtos", n_clicks=0, color="primary", outline=True, size="sm", className="mb-3"),
    dcc.Loading(html.Div(id='ia-output-produtos')),

    html.Hr(className="mt-5"),
    html.H2("Drill-Down: Fornecedores por Produto"),
    dbc.Alert("O que mostra? Ao selecionar um produto (ex: 'RESÍDUO DOMICILIAR'), este gráfico mostra quais fornecedores/empresas mais movimentaram esse item.", color="info"),
    
    dbc.Row([
        dbc.Col(
            [
                html.Label("Selecione um Produto:"),
                dcc.Dropdown(id='filtro-produto-para-fornecedor', options=produtos_options, value=produtos_options[0]['value'])
            ], md=6
        )
    ], className="dbc mb-3"),
    
    
    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-produto-fornecedores') 
        ]),
        className="mb-3"
    ),

    dbc.Button("🤖 Explicar Fornecedores deste Produto", id="btn-ia-prod-forn", n_clicks=0, color="primary", outline=True, size="sm", className="mb-3"),
    dcc.Loading(html.Div(id='ia-output-prod-forn')),

    html.Hr(className="mt-5"),
    html.H2("Drill-Down: Produtos por Setor"),
    dbc.Alert("O que mostra? Ao selecionar um setor (ex: 'CENTRO'), este gráfico mostra quais produtos são mais comuns *naquele* local.", color="info"),
    
    dbc.Row([
        dbc.Col(
            [
                html.Label("Selecione um Setor:"),
                dcc.Dropdown(id='filtro-setor-para-produto', options=setores_options, value=setores_options[0]['value'])
            ], md=6
        )
    ], className="dbc mb-3"),
    
    
    
    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-setor-produtos') 
        ]),
        className="mb-3"
    ),

    dbc.Button("🤖 Explicar Produtos deste Setor", id="btn-ia-setor-prod", n_clicks=0, color="primary", outline=True, size="sm", className="mb-3"),
    dcc.Loading(html.Div(id='ia-output-setor-prod'))

])


@callback(
    Output('grafico-contagem-produtos', 'figure'),
    [Input("theme-switch", "value")]
)
def update_product_graph_theme(switch_is_light):
    template = template_theme_light if switch_is_light else template_theme_dark
    fig = fig_contagem_produtos(df_produtos, template)
    return fig

@callback(
    Output('grafico-produto-fornecedores', 'figure'),
    [Input('filtro-produto-para-fornecedor', 'value'),
     Input("theme-switch", "value")]
)
def update_prod_forn_graph(selected_product, switch_is_light):
    template = template_theme_light if switch_is_light else template_theme_dark
    
    query = """
    SELECT 
        fornecedor_cliente, 
        COUNT(*) as quantidade
    FROM registro
    WHERE 
        produto = %(produto)s AND 
        fornecedor_cliente IS NOT NULL
    GROUP BY fornecedor_cliente
    ORDER BY quantidade DESC
    """
    params = {'produto': selected_product}
    df_drilldown = pd.read_sql(query, engine, params=params)
    
    fig = px.bar(df_drilldown, x='quantidade', y='fornecedor_cliente', orientation='h',
                 title=f"Fornecedores que movimentaram: {selected_product}",
                 template=template)
    fig.update_layout(yaxis={'autorange': 'reversed'},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

@callback(
    Output('grafico-setor-produtos', 'figure'),
    [Input('filtro-setor-para-produto', 'value'),
     Input("theme-switch", "value")]
)
def update_setor_prod_graph(selected_setor, switch_is_light):
    template = template_theme_light if switch_is_light else template_theme_dark
    
    query = """
    SELECT 
        produto, 
        COUNT(*) as quantidade
    FROM registro
    WHERE 
        setor = %(setor)s AND 
        produto IS NOT NULL
    GROUP BY produto
    ORDER BY quantidade DESC
    """
    params = {'setor': selected_setor}
    df_drilldown = pd.read_sql(query, engine, params=params)
    
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
    if not gemini_configurado:
        return dbc.Alert("Erro de Configuração: API do Gemini não encontrada.", color="danger", className="mt-3")
            
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
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return dbc.Card(dbc.CardBody(dcc.Markdown(response.text)), className="mt-3")
    except Exception as e:
        return dbc.Alert(f"Erro na API: {str(e)}", color="danger", className="mt-3")

@callback(
    Output('ia-output-prod-forn', 'children'),
    Input('btn-ia-prod-forn', 'n_clicks'),
    State('filtro-produto-para-fornecedor', 'value'),
    prevent_initial_call=True
)
def get_ia_prod_forn(n_clicks, selected_product):
    if not gemini_configurado:
        return dbc.Alert("Erro de Configuração: API do Gemini não encontrada.", color="danger", className="mt-3")
            
    query = "SELECT fornecedor_cliente, COUNT(*) as quantidade FROM registro WHERE produto = %(produto)s AND fornecedor_cliente IS NOT NULL GROUP BY fornecedor_cliente ORDER BY quantidade DESC"
    params = {'produto': selected_product}
    df_drilldown = pd.read_sql(query, engine, params=params)
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
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return dbc.Card(dbc.CardBody(dcc.Markdown(response.text)), className="mt-3")
    except Exception as e:
        return dbc.Alert(f"Erro na API: {str(e)}", color="danger", className="mt-3")

@callback(
    Output('ia-output-setor-prod', 'children'),
    Input('btn-ia-setor-prod', 'n_clicks'),
    State('filtro-setor-para-produto', 'value'),
    prevent_initial_call=True
)
def get_ia_setor_prod(n_clicks, selected_setor):
    if not gemini_configurado:
        return dbc.Alert("Erro de Configuração: API do Gemini não encontrada.", color="danger", className="mt-3")
            
    query = "SELECT produto, COUNT(*) as quantidade FROM registro WHERE setor = %(setor)s AND produto IS NOT NULL GROUP BY produto ORDER BY quantidade DESC"
    params = {'setor': selected_setor}
    df_drilldown = pd.read_sql(query, engine, params=params)
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
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return dbc.Card(dbc.CardBody(dcc.Markdown(response.text)), className="mt-3")
    except Exception as e:
        return dbc.Alert(f"Erro na API: {str(e)}", color="danger", className="mt-3")