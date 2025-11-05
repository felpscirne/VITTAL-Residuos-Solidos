from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

from database import engine

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
    
    # --- Seção MACRO (Gráfico e Tabela Originais) ---
    dbc.Card(
        dbc.CardBody(dcc.Graph(id='grafico-fluxo-candiota')),
        className="mb-3"
    ),
    html.H2("Tabela de Balanço Mensal (Total)"),
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
    
    # --- NOVA SEÇÃO: Análise Setorial Detalhada ---
    html.Hr(className="mt-5"),
    html.H2("Análise Setorial Detalhada (vs. Candiota)"),
    
    # Filtro de Setor
    dbc.Card(
        dbc.CardBody([
            html.Label("Selecione um setor para análise detalhada:"),
            dcc.Dropdown(
                id='dropdown-setor-fluxo',
                options=setores_options,
                value=setores_options[0]['value'] # Seleciona o primeiro setor por padrão
            )
        ]),
        className="mb-3 dbc" # 'dbc' para o tema do dropdown
    ),
    
    # Cards de Análise
    dbc.Row([
        # Gráfico (Goal 1)
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dcc.Loading(dcc.Graph(id='grafico-setor-vs-candiota'))
                )
            ),
            md=8, className="mb-3"
        ),
        # KPI de Participação (Goal 2)
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dcc.Loading(html.Div(id='kpi-setor-participacao'))
                )
            ),
            md=4, className="mb-3"
        ),
    ])
])

# --- 4. CALLBACKS (ATUALIZADOS) ---

# Callback 1: Atualiza o gráfico MACRO com a troca de tema
@callback(
    Output('grafico-fluxo-candiota', 'figure'),
    [Input("theme-switch", "value")]
)
def update_macro_graph_theme(switch_is_light):
    template = template_theme_light if switch_is_light else template_theme_dark
    fig = create_macro_fluxo_graph(df_fluxo_macro, template)
    return fig

# Callback 2 (NOVO): Atualiza o gráfico MICRO e o KPI com a troca de dropdown E tema
@callback(
    [Output('grafico-setor-vs-candiota', 'figure'),
     Output('kpi-setor-participacao', 'children')],
    [Input('dropdown-setor-fluxo', 'value'),
     Input("theme-switch", "value")]
)
def update_micro_analysis(setor_selecionado, switch_is_light):
    
    # Define o template do gráfico
    template = template_theme_light if switch_is_light else template_theme_dark
    
    # --- Lógica para o Gráfico (Goal 1) ---
    fig = create_micro_fluxo_graph(df_fluxo_micro, setor_selecionado, template)
    
    # --- Lógica para o KPI de Participação (Goal 2) ---
    
    # Calcula totais
    total_saida_candiota = df_fluxo_micro[
        df_fluxo_micro['setor'] == 'CANDIOTA'
    ]['peso_kg'].sum()
    
    total_setor_selecionado = df_fluxo_micro[
        df_fluxo_micro['setor'] == setor_selecionado
    ]['peso_kg'].sum()
    
    # Calcula a porcentagem
    if total_saida_candiota > 0:
        percentual = (total_setor_selecionado / total_saida_candiota) * 100
    else:
        percentual = 0
        
    # Cria o componente de KPI/Progresso
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