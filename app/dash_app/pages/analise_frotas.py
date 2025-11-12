from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

from app.database import engine
from app.services.ai_service import client, gemini_configurado, MODEL_NAME

template_theme_light = "cosmo" 
template_theme_dark = "plotly_dark"

def load_frota_data():
    query = """
    SELECT 
        placa_veiculo,
        COALESCE(fornecedor_cliente, 'Não Especificada') as entidade_responsavel,
        COUNT(*) as total_viagens,
        AVG(peso_liquido) as peso_medio_por_viagem
    FROM registro
    WHERE 
        setor != 'CANDIOTA' AND setor != 'ACERTO DE PESO'
        AND peso_liquido > 0
    GROUP BY placa_veiculo, fornecedor_cliente
    ORDER BY total_viagens DESC;
    """
    df = pd.read_sql(query, engine)
    
    df['peso_medio_por_viagem'] = df['peso_medio_por_viagem'].round(2)
    return df

df_frota_raw = load_frota_data()

if df_frota_raw.empty:
    max_viagens_slider = 100
    min_viagens_default = 0
    entidades_options = [{'label': 'Todas as Entidades', 'value': 'todas'}]
else:
    max_viagens_slider = int(df_frota_raw['total_viagens'].max())
    min_viagens_default = 1
    entidades_options = [
        {'label': t, 'value': t} for t in df_frota_raw['entidade_responsavel'].unique()
    ]
    entidades_options.insert(0, {'label': 'Todas as Entidades', 'value': 'todas'})



def create_frota_scatter_graph(df, template):
    fig = px.scatter(
        df,
        x='total_viagens',
        y='peso_medio_por_viagem',
        title='Eficiência (Peso Médio) vs. Volume (Total de Viagens) por Veículo',
        labels={
            'total_viagens': 'Total de Viagens (Volume)',
            'peso_medio_por_viagem': 'Peso Médio por Viagem (Eficiência)'
        },
        hover_name='placa_veiculo', 
        color='entidade_responsavel',
        template=template
    )
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

def create_frota_ranking_graph(df, template):
    
    df_piores = df.nsmallest(15, 'peso_medio_por_viagem')
    df_piores['tipo'] = '15 Piores (Menor Peso Médio)'
    
    df_melhores = df.nlargest(15, 'peso_medio_por_viagem')
    df_melhores['tipo'] = '15 Melhores (Maior Peso Médio)'
    
    df_ranking = pd.concat([df_piores, df_melhores])
    
    fig = px.bar(
        df_ranking,
        x='peso_medio_por_viagem',
        y='placa_veiculo',
        orientation='h',
        color='tipo',
        title='Ranking de Eficiência de Veículos (Melhores vs Piores)',
        labels={'peso_medio_por_viagem': 'Peso Médio por Viagem (kg)', 'placa_veiculo': 'Placa do Veículo'},
        template=template,
        facet_col='tipo' 
    )
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title=None,
        yaxis={'categoryorder':'total ascending'}
    )
    fig.update_yaxes(matches=None, showticklabels=True) 
    
    return fig

layout = html.Div([
    html.H1('Análise de Eficiência da Frota (por Placa)'),
    html.P('Esta análise identifica os veículos mais e menos eficientes da operação de coleta.'),
    html.Hr(),
    
    dbc.Alert(
        [
            html.H5("O que esta análise responde?", className="alert-heading"),
            html.P("Temos caminhões (da frota própria ou de empresas) que estão rodando 'batendo lata' (com peso médio baixo)? "
                   "Quais veículos são nossos 'cavalos de batalha' (muitas viagens, peso alto) e quais são 'problemáticos' (muitas viagens, peso baixo)?")
        ], color="info", className="mb-3"
    ),

    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Filtrar por Empresa/Entidade:"),
                    dcc.Dropdown(
                        id='filtro-entidade-frota',
                        options=entidades_options,
                        value='todas'
                    )
                ], md=6),
                dbc.Col([
                    html.Label(id='label-slider-frota', children=f"Filtrar por Nº Mínimo de Viagens: {min_viagens_default}"),
                    dcc.Slider(
                        id='filtro-viagens-frota',
                        min=0,
                        max=max_viagens_slider,
                        step=1, 
                        value=min_viagens_default,
                        marks=None,
                        tooltip={"placement": "bottom", "always_visible": False}
                    )
                ], md=6)
            ])
        ]),
        className="dbc mb-3"
    ),

    dbc.Button("🤖 Analisar Eficiência da Frota", id="btn-ia-frota", n_clicks=0, color="primary", outline=True, size="sm", className="mb-3"),
    dcc.Loading(html.Div(id='ia-output-frota')), 

    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-frota-scatter') # Gráfico de Dispersão
        ]),
        className="mb-3"
    ),
    dbc.Card(
        dbc.CardBody([
            dcc.Graph(id='grafico-frota-ranking') # Gráfico de Ranking (Facetado)
        ]),
        className="mb-3"
    )
])


@callback(
    [Output('grafico-frota-scatter', 'figure'),
     Output('grafico-frota-ranking', 'figure'),
     Output('label-slider-frota', 'children')], 
    [Input('filtro-entidade-frota', 'value'),
     Input('filtro-viagens-frota', 'value'),
     Input("theme-switch", "value")]
)
def update_frota_graphs(selected_entidade, min_viagens, switch_is_light):
    template = template_theme_light if switch_is_light else template_theme_dark
    
    df_filtered = df_frota_raw.copy()
    if selected_entidade != 'todas':
        df_filtered = df_filtered[df_filtered['entidade_responsavel'] == selected_entidade]
    
    df_filtered = df_filtered[df_filtered['total_viagens'] >= min_viagens]
    
    if df_filtered.empty or len(df_filtered) < 2: 
        fig_scatter = px.scatter(title=f"Nenhum veículo encontrado com {min_viagens}+ viagens", template=template)
        fig_ranking = px.bar(title=f"Nenhum veículo encontrado com {min_viagens}+ viagens", template=template)
        fig_scatter.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig_ranking.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    else:
        fig_scatter = create_frota_scatter_graph(df_filtered, template)
        fig_ranking = create_frota_ranking_graph(df_filtered, template)
    
    label_slider = f"Filtrar por Nº Mínimo de Viagens: {min_viagens}"
    
    return fig_scatter, fig_ranking, label_slider

@callback(
    Output('ia-output-frota', 'children'),
    [Input('btn-ia-frota', 'n_clicks')],
    [State('filtro-entidade-frota', 'value'), 
     State('filtro-viagens-frota', 'value')],
    prevent_initial_call=True
)
def get_ia_frota_analysis(n_clicks, selected_entidade, min_viagens):
    if not gemini_configurado:
        return dbc.Alert("Erro de Configuração: API do Gemini não encontrada.", color="danger", className="mt-3")
            
    df_filtered = df_frota_raw.copy()
    if selected_entidade != 'todas':
        df_filtered = df_filtered[df_filtered['entidade_responsavel'] == selected_entidade]
    df_filtered = df_filtered[df_filtered['total_viagens'] >= min_viagens]

    if df_filtered.empty:
        return dbc.Alert("Nenhum dado encontrado para análise. Ajuste os filtros.", color="warning", className="mt-3")

    df_piores = df_filtered.nsmallest(5, 'peso_medio_por_viagem')
    df_melhores = df_filtered.nlargest(5, 'peso_medio_por_viagem')
    dados_piores_texto = df_piores.to_markdown(index=False)
    dados_melhores_texto = df_melhores.to_markdown(index=False)
    contexto_filtro = f"da entidade '{selected_entidade}'" if selected_entidade != 'todas' else "de todas as entidades"
    contexto_filtro += f" com no mínimo {min_viagens} viagens"

    prompt = f"""
    Você é um gerente de logística da prefeitura de Rio Grande - RS.
    Sua tarefa é analisar a eficiência da frota de veículos {contexto_filtro}.

    Aqui estão os dados:
    
    TOP 5 VEÍCULOS MAIS EFICIENTES (Maior Peso Médio):
    {dados_melhores_texto}

    TOP 5 VEÍCULOS MENOS EFICIENTES (Pior Peso Médio):
    {dados_piores_texto}

    Por favor, gere uma análise em markdown respondendo:
    1.  O que a lista de "Piores Veículos" nos diz? Por que um veículo com muitas viagens teria um peso médio tão baixo?
    2.  O que podemos aprender com os "Melhores Veículos"?
    3.  Qual a sua principal recomendação para o gestor de frota com base nesses dados? (Ex: otimizar rotas, verificar caminhões específicos, etc.)
    
    Responda em um texto organizado e de linguagem clara. Não fale as perguntas. Não se apresente.
    """
    
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return dbc.Card(dbc.CardBody(dcc.Markdown(response.text)), className="mt-3")
    except Exception as e:
        return dbc.Alert(f"Erro na API: {str(e)}", color="danger", className="mt-3")