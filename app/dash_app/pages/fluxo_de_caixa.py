from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

from app.database import engine

from app.services.ai_service import client, gemini_configurado, MODEL_NAME

template_theme_light = "cosmo" 
template_theme_dark = "plotly_dark"

def load_fluxo_macro_data():
    query = """
    SELECT 
        EXTRACT(YEAR FROM data_hora) as year,
        EXTRACT(MONTH FROM data_hora) as month,
        SUM(CASE 
            WHEN setor = 'CANDIOTA' THEN peso_embalagem_liquido_corrigido 
            ELSE 0 
        END) as saidas,
        SUM(CASE 
            WHEN setor != 'CANDIOTA' AND setor != 'ACERTO DE PESO' THEN peso_embalagem_liquido_corrigido 
            ELSE 0 
        END) as entradas
    FROM registro
    GROUP BY year, month
    ORDER BY year, month
    """
    df = pd.read_sql(query, engine)
    df['balanco'] = (df['entradas'] - df['saidas']).round(2)
    df['entradas'] = df['entradas'].round(2)
    df['saidas'] = df['saidas'].round(2)
    df['periodo'] = pd.to_datetime(df.assign(day=1)[['year', 'month', 'day']]).dt.strftime('%Y-%m')
    return df

def load_fluxo_micro_data():
    query = """
    SELECT
        EXTRACT(YEAR FROM data_hora) as year,
        EXTRACT(MONTH FROM data_hora) as month,
        setor,
        SUM(peso_embalagem_liquido_corrigido) as peso_kg
    FROM registro
    WHERE 
        setor != 'ACERTO DE PESO'
    GROUP BY year, month, setor
    ORDER BY year, month, setor
    """
    df = pd.read_sql(query, engine)
    df['periodo'] = pd.to_datetime(df.assign(day=1)[['year', 'month', 'day']]).dt.strftime('%Y-%m')
    return df

df_fluxo_macro = load_fluxo_macro_data()
df_fluxo_micro = load_fluxo_micro_data() 

# Prepara a lista de setores para o dropdown (excluindo Candiota)
setores_para_filtro = df_fluxo_micro[
    df_fluxo_micro['setor'] != 'CANDIOTA'
]['setor'].unique()
setores_options = sorted([{'label': s, 'value': s} for s in setores_para_filtro], key=lambda x: x['label'])


 # Criação dos gráficos 
def create_macro_fluxo_graph(df, template):
    df_melted = df.melt(id_vars=['periodo'], value_vars=['entradas', 'saidas'],
                         var_name='tipo_fluxo', value_name='peso_kg')
    fig = px.bar(df_melted, x='periodo', y='peso_kg', color='tipo_fluxo',
                 barmode='group', title="Fluxo Mensal: Total Entradas vs. Total Saídas (Candiota)",
                 template=template)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def create_micro_fluxo_graph(df, setor_selecionado, template):
    df_candiota = df[df['setor'] == 'CANDIOTA']
    df_setor = df[df['setor'] == setor_selecionado]
    
    df_comparativo = pd.concat([df_candiota, df_setor])
    
    fig = px.line(df_comparativo, x='periodo', y='peso_kg', color='setor',
                  title=f"Comparativo Mensal: {setor_selecionado} vs. Candiota",
                  markers=True, template=template)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

layout = html.Div([
    html.H1('Análise de Fluxo (Entrada vs. Saída)'),
    html.P("Esta página compara o volume total de resíduos 'Entrada' (coletado de todos os setores) "
           "com o volume de 'Saída' (registrado no setor de destino 'CANDIOTA')."),
    html.Hr(),
    
    
    dbc.Alert(
        [
            html.H5("O que esta análise responde?", className="alert-heading"),
            html.P("Qual é a relação entre o que coletamos e o que enviamos para descarte? "
                   "Estamos coletando mais do que descartamos, ou o contrário? "
                   "Existem setores específicos que contribuem mais para essa dinâmica?")
        ],
        color="info", className="mb-3"
    ),

    html.H2("Visão Geral do Balanço Mensal (Gráfico)"),

    dbc.Card(
        dbc.CardBody(dcc.Graph(id='grafico-fluxo-candiota')),
        className="mb-3"
    ),

    html.Div([
        html.H2("Visão Geral do Balanço Mensal (Tabela)"),
        dbc.Button("🤖 Explicar esta tabela", id="btn-ia-balanco", n_clicks=0, color="primary", outline=True, size="sm", className="ms-3"),
    ], className="d-flex align-items-center mb-2"),
    
    dbc.Card(
        dbc.CardBody(
            dash_table.DataTable(
                id='tabela-fluxo-candiota',
                columns=[
                    {"name": "Período", "id": "periodo"},
                    {"name": "Entradas (kg)", "id": "entradas"},
                    {"name": "Saídas (kg)", "id": "saidas"},
                    {"name": "Balanço (kg)", "id": "balanco"},
                ],
                data=df_fluxo_macro.to_dict('records'),
                sort_action="native", page_size=12,
                style_header={"backgroundColor": "var(--bs-tertiary-bg)", "color": "var(--bs-body-color)", "fontWeight": "bold", "border": "1px solid var(--bs-border-color)"},
                style_data={"backgroundColor": "var(--bs-body-bg)", "color": "var(--bs-body-color)"},
                style_cell={'border': '1px solid var(--bs-border-color)'}
            ),
            className="dbc" 
        ),
        className="mb-3"
    ),
    
    dcc.Loading(html.Div(id='ia-output-balanco')),

    
    html.Hr(className="mt-5"),
    
    html.Div([
        html.H2("Análise Setorial Detalhada (vs. Candiota)"),
        dbc.Button("🤖 Explicar esta análise", id="btn-ia-setor", n_clicks=0, color="primary", outline=True, size="sm", className="ms-3"),
    ], className="d-flex align-items-center mb-2"),
    
    dbc.Card(
        dbc.CardBody([
            html.Label("Selecione um setor para análise detalhada:"),
            dcc.Dropdown(
                id='dropdown-setor-fluxo',
                options=setores_options,
                value=setores_options[0]['value'] 
            )
        ]),
        className="mb-3 dbc" 
    ),
    
    dbc.Row([
        dbc.Col(
            dbc.Card(dbc.CardBody(dcc.Loading(dcc.Graph(id='grafico-setor-vs-candiota')))),
            md=8, className="mb-3"
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody(dcc.Loading(html.Div(id='kpi-setor-participacao')))),
            md=4, className="mb-3"
        ),
    ]),
    
    dcc.Loading(html.Div(id='ia-output-setor'))
])



@callback(
    Output('grafico-fluxo-candiota', 'figure'),
    [Input("theme-switch", "value")]
)
def update_macro_graph_theme(switch_is_light):
    template = template_theme_light if switch_is_light else template_theme_dark
    fig = create_macro_fluxo_graph(df_fluxo_macro, template)
    return fig

@callback(
    [Output('grafico-setor-vs-candiota', 'figure'),
     Output('kpi-setor-participacao', 'children')],
    [Input('dropdown-setor-fluxo', 'value'),
     Input("theme-switch", "value")]
)
def update_micro_analysis(setor_selecionado, switch_is_light):
    
    template = template_theme_light if switch_is_light else template_theme_dark
    
    fig = create_micro_fluxo_graph(df_fluxo_micro, setor_selecionado, template)
    
    
    total_saida_candiota = df_fluxo_micro[
        df_fluxo_micro['setor'] == 'CANDIOTA'
    ]['peso_kg'].sum()
    
    total_setor_selecionado = df_fluxo_micro[
        df_fluxo_micro['setor'] == setor_selecionado
    ]['peso_kg'].sum()
    
    if total_saida_candiota > 0:
        percentual = (total_setor_selecionado / total_saida_candiota) * 100
    else:
        percentual = 0
        
    kpi_component = html.Div([
        html.H4("Participação vs. Saída Total"),
        html.P(f"Análise do setor: {setor_selecionado}"),
        html.Hr(),
        html.H5(f"Total {setor_selecionado}:", className="fw-bold"),
        html.P(f"{total_setor_selecionado:,.2f} kg"),
        html.H5(f"Total Saída (Candiota):", className="fw-bold"),
        html.P(f"{total_saida_candiota:,.2f} kg"),
        html.Hr(),
        html.H5("Participação Percentual:"),
        dbc.Progress(
            value=percentual, 
            label=f"{percentual:.2f}%", 
            style={"height": "30px", "font-size": "1.1rem"}
        ),
        html.P(
            f"O volume deste setor representa {percentual:.2f}% do volume total de saída.",
            className="mt-3"
        )
    ])
    
    return fig, kpi_component


@callback(
    Output('ia-output-balanco', 'children'),
    Input('btn-ia-balanco', 'n_clicks'),
    prevent_initial_call=True
)
def get_ia_balanco(n_clicks):
    if not gemini_configurado:
        return dbc.Alert("Erro de Configuração: API do Gemini não encontrada.", color="danger", className="mt-3")
            
    
    df = df_fluxo_macro
    media_balanco_mensal = df['balanco'].mean()
    total_balanco_acumulado = df['balanco'].sum()
    mes_maior_excesso = df.loc[df['balanco'].idxmax()]
    mes_maior_deficit = df.loc[df['balanco'].idxmin()]

    # Prompt Balanço
    prompt = f"""
    Você é um analista de dados sênior da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar os DADOS GERAIS de fluxo de resíduos e fornecer insights.

    Aqui estão os dados-chave que eu calculei:
    - Balanço Total Acumulado (Entradas - Saídas): {total_balanco_acumulado:,.2f} kg
    - Média de Balanço Mensal: {media_balanco_mensal:,.2f} kg/mês
    - Mês com Maior Excesso de Entrada (Balanço mais alto): {mes_maior_excesso['periodo']} (Balanço: {mes_maior_excesso['balanco']:,.2f} kg)
    - Mês com Maior Déficit de Entrada (Balanço mais baixo): {mes_maior_deficit['periodo']} (Balanço: {mes_maior_deficit['balanco']:,.2f} kg)

    Por favor, gere uma análise em markdown respondendo:
    1.  O que o balanço mensal acumulado e a média nos dizem? (Um balanço positivo alto significa que estamos estocando resíduo? A diferença é significativa? Pode ser agua, terra, etc.? Ou erro de medição?)
    2.  Quais são as implicações dos meses de discrepância (o mês com maior excesso e o mês com maior déficit)?
    3.  Qual sua principal recomendação com base nesses números?

    Responda em um texto organizado e de linguagem clara. Sem falar as perguntas. Não se apresente.
    """
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return dbc.Card(dbc.CardBody(dcc.Markdown(response.text)), className="mt-3")
    except Exception as e:
        return dbc.Alert(f"Erro na API: {str(e)}", color="danger", className="mt-3")

@callback(
    Output('ia-output-setor', 'children'),
    Input('btn-ia-setor', 'n_clicks'),
    State('dropdown-setor-fluxo', 'value'),
    prevent_initial_call=True
)
def get_ia_setor(n_clicks, setor_selecionado):
    if not gemini_configurado:
        return dbc.Alert("Erro de Configuração: API do Gemini não encontrada.", color="danger", className="mt-3")
            
    total_saida_candiota = df_fluxo_micro[df_fluxo_micro['setor'] == 'CANDIOTA']['peso_kg'].sum()
    total_setor_selecionado = df_fluxo_micro[df_fluxo_micro['setor'] == setor_selecionado]['peso_kg'].sum()
    percentual = (total_setor_selecionado / total_saida_candiota) * 100 if total_saida_candiota > 0 else 0

    # Prompt  Setor
    prompt = f"""
    Você é um analista de dados sênior da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar a *Participação do Setor* selecionado.

    Dados da Análise:
    - Setor em Foco: "{setor_selecionado}"
    - Participação deste setor no total de saída: {percentual:.2f}%
    - Total de Entrada do Setor: {total_setor_selecionado:,.2f} kg
    - Total de Saída (Candiota): {total_saida_candiota:,.2f} kg

    Por favor, explique o que esses números significam em 2-3 bullet points:
    1.  O que a participação de {percentual:.2f}% do setor "{setor_selecionado}" significa? É um volume alto ou baixo para um único setor?
    2.  Qual a principal conclusão que se pode tirar disso?
    3.  Quais ações você recomendaria?

    Responda em um texto organizado e de linguagem clara. Sem falar as perguntas. Não se apresente. O usuario pode conferir uma analise melhor do setor analisando o grafico acima. Outra opção é a pagina de analise geral de setores.
    """
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return dbc.Card(dbc.CardBody(dcc.Markdown(response.text)), className="mt-3")
    except Exception as e:
        return dbc.Alert(f"Erro na API: {str(e)}", color="danger", className="mt-3")