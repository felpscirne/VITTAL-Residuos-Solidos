from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

# Importa a engine do banco
from app.database import engine

template_theme_light = "plotly"
template_theme_dark = "plotly_dark"

def carregar_kpis():
    query = "SELECT COUNT(*) AS total_registros, MIN(data_hora) AS data_inicio, MAX(data_hora) AS data_fim FROM registro"
    try:
        df = pd.read_sql(query, engine)
        kpis = df.iloc[0]
        return {
            'total': kpis['total_registros'],
            'inicio': kpis['data_inicio'].strftime('%d/%m/%Y'),
            'fim': kpis['data_fim'].strftime('%d/%m/%Y')
        }
    except Exception:
        return {'total': 'N/D', 'inicio': 'N/D', 'fim': 'N/D'}

def get_df_qtde_por_ano():
    query = "SELECT EXTRACT(YEAR FROM data_hora) AS ano, COUNT(*) AS qtde FROM registro GROUP BY ano ORDER BY ano"
    df = pd.read_sql(query, engine)
    df['ano'] = df['ano'].astype(str)
    return df

def get_df_top_produtos():
    query = "SELECT produto, COUNT(*) AS qtde FROM registro GROUP BY produto ORDER BY qtde DESC LIMIT 10"
    df = pd.read_sql(query, engine)
    return df

# --- Carregar dados UMA VEZ ---
# (Isso é rápido, então fazemos fora do callback)
kpi_data = carregar_kpis()
df_ano = get_df_qtde_por_ano()
df_produtos = get_df_top_produtos()

# --- Layout da Página (AGORA DINÂMICO) ---
# As figuras dos gráficos foram removidas do layout
layout = html.Div([
    html.H1('Visão Geral do Dashboard'),
    html.P('Resumo dos principais indicadores de pesagem.'),
    
dbc.Alert(
        [
            html.H5("O que são estes números?", className="alert-heading"),
            html.P("Estes são os números vitais que dão contexto a todo o resto. Eles nos dizem o 'tamanho' da amostra (quantos registros temos) e se os dados estão atualizados."),
            html.P("Os graficos a seguir possuem algumas missões: Queremos ver a tendência de longo prazo. Isso é crucial para o planejamento futuro. Queremos identificar o 'carro-chefe' da nossa coleta. É lixo domiciliar comum? É entulho de construção? É lixo hospitalar? A proporção entre eles é a que esperamos?")
        ],
        color="info", className="mb-3"
    ),

    # KPIs (estáticos, dentro de Cards)
    dbc.Row(
        [
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H3(kpi_data['total'], className='card-title'),
                html.P('Total de Registros', className='card-text')
            ]), className="mb-3"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H3(kpi_data['inicio'], className='card-title'),
                html.P('Data de Início', className='card-text')
            ]), className="mb-3"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H3(kpi_data['fim'], className='card-title'),
                html.P('Data de Fim', className='card-text')
            ]), className="mb-3"), md=4),
        ]
    ),
    html.Hr(),
    
    # Gráficos (vazios, 'figure=' removido, mas dentro de Cards)
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(dbc.CardBody(dcc.Graph(id='overview-grafico-ano'))), # 'figure=' removido
                md=6, className="mb-3"
            ),
            dbc.Col(
                dbc.Card(dbc.CardBody(dcc.Graph(id='overview-grafico-produtos'))), # 'figure=' removido
                md=6, className="mb-3"
            ),
        ]
    )
])

@callback(
    [Output('overview-grafico-ano', 'figure'),
     Output('overview-grafico-produtos', 'figure')],
    [Input("theme-switch", "value")]
)
def update_overview_graphs(switch_is_light):
    
    
    template_name = template_theme_light if switch_is_light else template_theme_dark
    
    fig_ano = px.bar(
        df_ano, 
        x='ano', y='qtde', 
        title="Total de Registros por Ano", 
        template=template_name 
    )
    fig_ano.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    
    fig_produtos = px.pie(
        df_produtos, 
        names='produto', values='qtde', 
        title="Top 10 Produtos (Volume de Registros)",
        template=template_name 
    )
    fig_produtos.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    
    return fig_ano, fig_produtos