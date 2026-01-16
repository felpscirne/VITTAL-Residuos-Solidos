from dash import dcc, html, callback, no_update
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.database import engine
from app.services.ai_service import generate_analysis_component

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

# df_frota_raw = load_frota_data()

# if df_frota_raw.empty:
#     max_viagens_slider = 100
#     min_viagens_default = 0
#     entidades_options = [{'label': 'Todas as Entidades', 'value': 'todas'}]
# else:
#     max_viagens_slider = int(df_frota_raw['total_viagens'].max())
#     min_viagens_default = 1
#     entidades_options = [
#         {'label': t, 'value': t} for t in df_frota_raw['entidade_responsavel'].unique()
#     ]
#     entidades_options.insert(0, {'label': 'Todas as Entidades', 'value': 'todas'})

max_viagens_slider = 500 # Default fallback
min_viagens_default = 0
entidades_options = [{'label': 'Todas as Entidades', 'value': 'todas'}] # Initial placeholder




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
    dmc.Title('Análise de Eficiência da Frota', order=2),
    dmc.Text('Esta análise identifica os veículos mais e menos eficientes da operação de coleta.', c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),

    dmc.Alert(
        children=[
            dmc.Title("Eficiência Operacional", order=5),
            dmc.Text("Analise o desempenho individual dos veículos. Placas com muitas viagens mas pouco peso podem indicar ineficiência."),
        ],
        title="Dica de Análise",
        color="ifsc-green",
        variant="light",
        icon=DashIconify(icon="akar-icons:light-bulb"),
        mb="md"
    ),

    dmc.Card(
        children=[
            dmc.Grid( # Usando Grid para o Slider ficar alinhado melhor
                gutter="md",
                children=[
                    dmc.GridCol(
                        [
                            dmc.Select(
                                label="Filtrar por Empresa/Entidade",
                                placeholder="Selecione uma entidade",
                                id='filtro-entidade-frota',
                                data=entidades_options,
                                value='todas',
                                leftSection=DashIconify(icon="domain")
                            )
                        ], span={"base": 12, "md": 6}
                    ),
                    dmc.GridCol(
                        [
                            dmc.Text(id='label-slider-frota', children=f"Filtrar por Nº Mínimo de Viagens: {min_viagens_default}", size="sm", fw=500, mb=5),
                            dmc.Slider(
                                id='filtro-viagens-frota',
                                min=0,
                                max=max_viagens_slider,
                                step=1, 
                                value=min_viagens_default,
                                updatemode='drag',
                                color="teal",
                                marks=[
                                    {'value': 0, 'label': '0'},
                                    {'value': int(max_viagens_slider/2), 'label': str(int(max_viagens_slider/2))},
                                    {'value': max_viagens_slider, 'label': str(max_viagens_slider)},
                                ]
                            )
                        ], span={"base": 12, "md": 6}
                    )
                ]
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),

    dmc.Button(
        "🤖 Analisar Eficiência", 
        id="btn-ia-frotas", 
        n_clicks=0, 
        variant="outline", 
        color="indigo", 
        leftSection=DashIconify(icon="fluent:bot-24-regular"),
        size="compact-sm",
        mb="md"
    ),
    dcc.Loading(html.Div(id='ia-output-frota')), 

    dmc.Card(
        children=[
            dcc.Graph(id='grafico-frota-scatter') # Gráfico de Dispersão
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    ),
    dmc.Card(
        children=[
            dcc.Graph(id='grafico-frota-ranking') # Gráfico de Ranking (Facetado)
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="md"
    )
])


@callback(
    [Output('filtro-entidade-frota', 'data'),
     Output('filtro-viagens-frota', 'max'),
     Output('filtro-viagens-frota', 'marks')],
    Input('url', 'pathname')
)
def update_frota_filters(pathname):
    if pathname == '/analise-frotas':
        df = load_frota_data()
        
        if df.empty:
            return [{'label': 'Todas as Entidades', 'value': 'todas'}], 100, {'value': 0, 'label': '0'}
            
        # Entidades
        ents = sorted([
           {'label': t, 'value': t} for t in df['entidade_responsavel'].unique()
        ], key=lambda x: x['label'])
        ents.insert(0, {'label': 'Todas as Entidades', 'value': 'todas'})
        
        # Slider
        max_v = int(df['total_viagens'].max()) if not df.empty else 100
        marks = {
            0: '0',
            int(max_v/2): str(int(max_v/2)),
            max_v: str(max_v)
        }
        
        return ents, max_v, marks
        
    return no_update, no_update, no_update

# @callback(
#    [Output('grafico-frota-scatter', 'figure'),
#     Output('grafico-frota-ranking', 'figure'),
#     Output('label-slider-frota', 'children')], 
#    [Input('filtro-entidade-frota', 'value'),
#     Input('filtro-viagens-frota', 'value'),
#     Input("theme-switch", "value")]
# )
# def update_frota_graphs_legacy(selected_entidade, min_viagens, switch_is_light):
#    ...

@callback(
    [Output('grafico-frota-scatter', 'figure'),
     Output('grafico-frota-ranking', 'figure'),
     Output('label-slider-frota', 'children')],
    [Input('url', 'pathname'),
     Input('filtro-entidade-frota', 'value'),
     Input('filtro-viagens-frota', 'value'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_frota_graphs(pathname, entidade, min_viagens, color_scheme):
    if pathname != '/analise-frotas': return no_update, no_update, no_update
    
    df = load_frota_data()
    is_dark = color_scheme == 'dark'
    template = "plotly_dark" if is_dark else "plotly_white"
    
    if df.empty:
         empty_fig = px.scatter(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
         return empty_fig, empty_fig, "Sem dados"

    # Filters
    if entidade and entidade != 'todas':
        df = df[df['entidade_responsavel'] == entidade]
    
    if min_viagens is not None:
        df = df[df['total_viagens'] >= min_viagens]
        
    fig_scatter = create_frota_scatter_graph(df, template)
    fig_ranking = create_frota_ranking_graph(df, template)
    
    label = f"Filtrar por Nº Mínimo de Viagens: {min_viagens}"
    
    return fig_scatter, fig_ranking, label

@callback(
    Output('ia-output-frota', 'children'),
    [Input('btn-ia-frota', 'n_clicks')],
    [State('filtro-entidade-frota', 'value'), 
     State('filtro-viagens-frota', 'value')],
    prevent_initial_call=True
)
def get_ia_frota_analysis(n_clicks, selected_entidade, min_viagens):
            
    df_filtered = df_frota_raw.copy()
    if selected_entidade != 'todas':
        df_filtered = df_filtered[df_filtered['entidade_responsavel'] == selected_entidade]
    df_filtered = df_filtered[df_filtered['total_viagens'] >= min_viagens]

    if df_filtered.empty:
        return dmc.Alert("Nenhum dado encontrado para análise. Ajuste os filtros.", color="yellow", variant="filled", className="mt-3")

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
    
    return generate_analysis_component(prompt)
