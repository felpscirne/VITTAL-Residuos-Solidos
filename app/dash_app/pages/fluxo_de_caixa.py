from dash import dcc, html, callback, dash_table, no_update
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

# df_fluxo_macro = load_fluxo_macro_data()
# df_fluxo_micro = load_fluxo_micro_data() 

# Prepara a lista de setores para o dropdown (excluindo Candiota)
# setores_para_filtro = df_fluxo_micro[
#     df_fluxo_micro['setor'] != 'CANDIOTA'
# ]['setor'].unique()
# setores_options = sorted([{'label': s, 'value': s} for s in setores_para_filtro], key=lambda x: x['label'])

def get_setores_options_dynamic():
    df = load_fluxo_micro_data()
    if df.empty: return []
    setores = df[df['setor'] != 'CANDIOTA']['setor'].unique()
    return sorted([{'label': s, 'value': s} for s in setores], key=lambda x: x['label'])



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
        color="ifsc-green", 
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
                    data=[], 
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
                label="Selecione um Setor para comparar",
                placeholder="Carregando opções...",
                id='select-setor-micro',
                # data=setores_options,
                # value=setores_options[0]['value'] if setores_options else None,
                data=[],
                value=None,
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
    Output('tabela-fluxo-candiota', 'data'),
    Input('url', 'pathname')
)
def update_table_data(pathname):
    if pathname == '/fluxo-de-caixa':
        return load_fluxo_macro_data().to_dict('records')
    return no_update

@callback(
    [Output('select-setor-micro', 'data'),
     Output('select-setor-micro', 'value')],
    Input('url', 'pathname')
)
def update_setores_dropdown(pathname):
    if pathname == '/fluxo-de-caixa':
        options = get_setores_options_dynamic()
        value = options[0]['value'] if options else None
        return options, value
    return no_update, no_update

@callback(
    Output('grafico-fluxo-candiota', 'figure'),
    [Input('url', 'pathname'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_macro_graph(pathname, color_scheme):
    if pathname != '/fluxo-de-caixa': return no_update
    
    # Load fresh data
    df = load_fluxo_macro_data()
    
    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"
    
    if df.empty:
        # Return empty fig
        return px.bar(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        
    return create_macro_fluxo_graph(df, template)

@callback(
    Output('grafico-setor-vs-candiota', 'figure'),
    [Input('select-setor-micro', 'value'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_micro_graph(setor_selecionado, color_scheme):
    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"
    
    # Handle initial state or missing selection
    if not setor_selecionado:
         return px.line(template=template).update_layout(
             paper_bgcolor="rgba(0,0,0,0)", 
             plot_bgcolor="rgba(0,0,0,0)",
             title="Selecione um setor para visualizar"
         )

    df = load_fluxo_micro_data()
    if df.empty:
         return px.line(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    return create_micro_fluxo_graph(df, setor_selecionado, template)

@callback(
    Output('ia-output-balanco', 'children'),
    Input('btn-ia-balanco', 'n_clicks'),
    prevent_initial_call=True
)
def get_ia_balanco(n_clicks):
    
    df = load_fluxo_macro_data()
    if df.empty: return "Sem dados para análise."

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
    State('select-setor-micro', 'value'), # Corrected ID
    prevent_initial_call=True
)
def get_ia_setor(n_clicks, setor_selecionado):
            
    if not setor_selecionado: return "Selecione um setor."

    df_fluxo_micro = load_fluxo_micro_data()
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

@callback(
    Output('kpi-setor-participacao', 'children'),
    Input('select-setor-micro', 'value'),
)
def update_kpi_participacao(setor_selecionado):
    if not setor_selecionado:
        return dmc.Text("Selecione um setor.", c="dimmed")
    df = load_fluxo_micro_data()
    total_saida = df[df['setor'] == 'CANDIOTA']['peso_kg'].sum()
    total_setor = df[df['setor'] == setor_selecionado]['peso_kg'].sum()
    pct = (total_setor / total_saida * 100) if total_saida > 0 else 0
    return dmc.Stack([
        dmc.Text("Participação no Total de Saída", size="xs", c="dimmed", tt="uppercase"),
        dmc.Text(f"{pct:.1f}%", fw=700, size="xl"),
        dmc.Text(f"{total_setor:,.0f} kg de {total_saida:,.0f} kg", size="sm", c="dimmed"),
    ])