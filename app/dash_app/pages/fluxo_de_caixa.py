from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.database import engine

from app.services.ai_service import generate_analysis_component

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
    dmc.Title('Análise de Fluxo (Entrada vs. Saída)', order=2),
    dmc.Text(
        "Esta página compara o volume total de resíduos 'Entrada' (coletado de todos os setores) "
        "com o volume de 'Saída' (registrado no setor de destino 'CANDIOTA').",
        c="dimmed",
        size="sm"
    ),
    dmc.Divider(variant="solid", my="md"),
    
    
    dmc.Alert(
        [
            "Qual é a relação entre o que coletamos e o que enviamos para descarte? "
            "Estamos coletando mais do que descartamos, ou o contrário? "
            "Existem setores específicos que contribuem mais para essa dinâmica?"
        ],
        title="O que esta análise responde?",
        color="blue", 
        variant="light",
        icon=DashIconify(icon="akar-icons:info"),
        mb="md"
    ),

    dmc.Text("Visão Geral do Balanço Mensal (Gráfico)", size="lg", fw=500, mb="sm"),

    dmc.Card(
        children=[dcc.Graph(id='grafico-fluxo-candiota')],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),

    dmc.Group([
        dmc.Text("Visão Geral do Balanço Mensal (Tabela)", size="lg", fw=500),
        dmc.Button(
            "🤖 Explicar esta tabela", 
            id="btn-ia-balanco", 
            n_clicks=0, 
            variant="outline", 
            size="compact-sm",
            leftSection=DashIconify(icon="fluent:bot-24-regular")
        ),
    ], justify="space-between", mb="sm"),
    
    dmc.Card(
        children=[
            dmc.ScrollArea(
                dash_table.DataTable(
                    id='tabela-fluxo-candiota',
                    columns=[
                        {"name": "Período", "id": "periodo"},
                        {"name": "Entradas (kg)", "id": "entradas"},
                        {"name": "Saídas (kg)", "id": "saidas"},
                        {"name": "Balanço (kg)", "id": "balanco"},
                    ],
                    data=df_fluxo_macro.to_dict('records'),
                    sort_action="native", 
                    page_size=12,
                    style_header={
                        "backgroundColor": "#f8f9fa", 
                        "color": "#000", 
                        "fontWeight": "bold", 
                        "fontFamily": "sans-serif"
                    },
                    style_data={
                        "backgroundColor": "#fff", 
                        "color": "#000",
                        "fontFamily": "sans-serif"
                    },
                    style_cell={'border': '1px solid #dee2e6', 'padding': '10px'}
                ),
                offsetScrollbars=True,
                type="auto"
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),
    
    dcc.Loading(html.Div(id='ia-output-balanco')),

    dmc.Divider(variant="dotted", my="xl"),
    
    dmc.Group([
        dmc.Text("Análise Setorial Detalhada (vs. Candiota)", size="lg", fw=500),
        dmc.Button(
            "🤖 Explicar esta análise", 
            id="btn-ia-setor", 
            n_clicks=0, 
            variant="outline", 
            size="compact-sm",
            leftSection=DashIconify(icon="fluent:bot-24-regular")
        ),
    ], justify="space-between", mb="sm"),
    
    dmc.Card(
        children=[
            dmc.Select(
                label="Selecione um setor para análise detalhada:",
                placeholder="Selecione um setor",
                id='dropdown-setor-fluxo',
                data=setores_options,
                value=setores_options[0]['value'],
                leftSection=DashIconify(icon="fa6-solid:building"),
                mb="md"
            ),
             dmc.Grid(
                gutter="md",
                children=[
                    dmc.GridCol(
                        dcc.Loading(dcc.Graph(id='grafico-setor-vs-candiota')),
                        span={"base": 12, "md": 8}
                    ),
                    dmc.GridCol(
                        dcc.Loading(html.Div(id='kpi-setor-participacao')),
                        span={"base": 12, "md": 4}
                    )
                ]
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),
    
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
        
    kpi_component = dmc.Stack([
        dmc.Text("Participação vs. Saída Total", fw=500, size="lg"),
        dmc.Text(f"Análise do setor: {setor_selecionado}", c="dimmed", size="sm"),
        dmc.Divider(variant="solid"),
        dmc.Group([
            dmc.Text(f"Total {setor_selecionado}:", fw=700),
            dmc.Text(f"{total_setor_selecionado:,.2f} kg"),
        ], justify="space-between"),
        dmc.Group([
            dmc.Text(f"Total Saída (Candiota):", fw=700),
            dmc.Text(f"{total_saida_candiota:,.2f} kg"),
        ], justify="space-between"),
        dmc.Divider(variant="solid"),
        dmc.Text("Participação Percentual:", fw=500),
        dmc.Progress(
            value=percentual, 
            label=f"{percentual:.2f}%", 
            size="xl",
            radius="md",
            color="indigo"
        ),
        dmc.Text(
            f"O volume deste setor representa {percentual:.2f}% do volume total de saída.",
            size="sm",
            mt="sm"
        )
    ])
    
    return fig, kpi_component


@callback(
    Output('ia-output-balanco', 'children'),
    Input('btn-ia-balanco', 'n_clicks'),
    prevent_initial_call=True
)
def get_ia_balanco(n_clicks):
    
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
    
    return generate_analysis_component(prompt)

@callback(
    Output('ia-output-setor', 'children'),
    Input('btn-ia-setor', 'n_clicks'),
    State('dropdown-setor-fluxo', 'value'),
    prevent_initial_call=True
)
def get_ia_setor(n_clicks, setor_selecionado):
            
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
    
    return generate_analysis_component(prompt)
