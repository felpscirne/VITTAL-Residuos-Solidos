from dash import dcc, html, callback, Input, Output, State
import plotly.express as px
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from sqlalchemy import or_, extract
from datetime import datetime

from app.application.analytics import engine, get_anos_options 
from app.models import Event
from app.application.insights import generate_analysis_component
from app.application.analytics import get_dados_setores_macro, get_dados_setor_temporal
from app import db

# Load data
df_setores = get_dados_setores_macro()

# Dropdown options
setores_options_temporal = sorted([
    {'label': s, 'value': s} for s in df_setores['setor'].unique()
], key=lambda x: x['label'])

anos_options_temporal, ano_inicial_temporal = get_anos_options()
# DMC Select expects string value for labels usually, but let's check. 
# It handles value as string usually.
setor_inicial_temporal = setores_options_temporal[0]['value'] if setores_options_temporal else None


def fig_relacao_peso_volume(df, template):
    fig = px.scatter(
        df, x='quantidade', y='Média de Peso (kg)',
        title="Relação: Média de Peso x Volume de Registros por Setor",
        labels={'quantidade': 'Volume (Contagem)', 'Média de Peso (kg)': 'Média de Peso (kg)'},
        hover_name='setor', template=template
    )
    fig.update_layout(height=500, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def fig_media_por_setor(df, template):
    df_sorted = df.sort_values(by='Média de Peso (kg)', ascending=False)
    fig = px.bar(df_sorted, x='setor', y='Média de Peso (kg)', 
                 title="Ranking: Média do Peso por Setor", template=template)
    fig.update_xaxes(tickangle=45) 
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def fig_contagem_por_setor(df, template):
    df_sorted = df.sort_values(by='quantidade', ascending=False)
    num_setores = len(df_sorted.index)
    dynamic_height = max(400, num_setores * 20)
    fig = px.bar(df_sorted, x='quantidade', y='setor', orientation='h', 
                 title="Ranking: Volume de Registros por Setor", template=template)
    fig.update_layout(yaxis={'autorange': 'reversed'}, height=dynamic_height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


layout = dmc.Container([
    dmc.Title('Análise de Setores', order=2),
    dmc.Text('Compare todos os setores entre si ou analise a tendência de um setor específico ao longo do tempo.', c="dimmed", mb="lg"),
    
    dmc.Divider(mb="lg"),

    dmc.Title("Visão Geral: Comparativo entre Setores", order=3, mb="md"),

    dmc.Tabs(
        [
            dmc.TabsList(
                [
                    dmc.TabsTab("Matriz de Relação", value="relacao", leftSection=DashIconify(icon="radix-icons:mix")),
                    dmc.TabsTab("Rankings Individuais", value="individual", leftSection=DashIconify(icon="radix-icons:bar-chart")),
                ]
            ),
            dmc.TabsPanel(
                children=[
                    dmc.Alert(
                        children=[
                            dmc.Title("Matriz de Relação", order=5),
                            dmc.Text("Este gráfico cruza o número de viagens (horizontal) com o peso médio (vertical). Identifique setores 'fora da curva'."),
                        ],
                        title="Ajuda Analítica",
                        color="blue",
                        variant="light",
                        mt="md",
                        mb="md",
                        icon=DashIconify(icon="radix-icons:info-circled")
                    ),
                    dmc.Card(
                        dcc.Graph(id='grafico-relacao-setor'),
                        withBorder=True, shadow="sm", radius="md", p="md"
                    )
                ],
                value="relacao"
            ),
            dmc.TabsPanel(
                children=[
                    dmc.Alert(
                        children=[
                             dmc.Title("Rankings", order=5),
                             dmc.Text("Identifique os setores mais produtivos (peso médio) e os que geram mais demanda operacional (volume)."),
                        ],
                        title="Ajuda Analítica",
                        color="blue",
                        variant="light",
                         mt="md",
                        mb="md",
                        icon=DashIconify(icon="radix-icons:info-circled")
                    ),
                    dmc.SimpleGrid(
                        cols={"base": 1, "lg": 2},
                        spacing="md",
                        children=[
                            dmc.Card(dcc.Graph(id='grafico-media-setor'), withBorder=True, shadow="sm", radius="md", p="md"),
                            dmc.Card(dcc.Graph(id='grafico-contagem-setor'), withBorder=True, shadow="sm", radius="md", p="md"),
                        ]
                    )
                ],
                value="individual"
            ),
        ],
        value="relacao",
        color="blue",
        mb="xl"
    ),

    dmc.Button(
        "Analisar comparativo com IA", 
        id="btn-ia-setores-overview", 
        n_clicks=0, 
        variant="light", 
        color="violet", 
        leftSection=DashIconify(icon="radix-icons:magic-wand"),
        mb="md"
    ),
    dcc.Loading(html.Div(id='ia-output-setores-overview')),

    dmc.Divider(my="xl"),

    dmc.Title("Drill-Down: Análise Temporal por Setor", order=3, mb="md"),
    dmc.Alert(
        "Compare o desempenho mensal de um setor. Veja se há influência de eventos sazonais.", 
        color="gray", 
        variant="light", 
        mb="md"
    ),

    dmc.Grid(
        gutter="md",
        mb="md",
        children=[
            dmc.GridCol(
                dmc.Select(
                    label="Selecione o Setor",
                    placeholder="Escolha um setor",
                    id='filtro-setor-temporal',
                    data=setores_options_temporal,
                    value=setor_inicial_temporal,
                    searchable=True
                ), span=6
            ),
             dmc.GridCol(
                dmc.Select(
                    label="Selecione o Ano",
                    placeholder="Ano",
                    id='filtro-ano-temporal',
                    data=anos_options_temporal,
                    value=str(ano_inicial_temporal) if ano_inicial_temporal else None,
                     allowDeselect=False
                ), span=6
            )
        ]
    ),

    dmc.Card(
        children=[
             dcc.Graph(id='grafico-media-setor-temporal'),
             html.Div(id='lista-eventos-setor', style={"paddingTop": "20px"})
        ],
        withBorder=True, shadow="sm", radius="md", p="md", mb="md"
    ),
    
    dmc.Button(
        "Analisar tendência deste setor com IA", 
        id="btn-ia-setores-temporal", 
        n_clicks=0, 
        variant="light", 
        color="violet", 
        leftSection=DashIconify(icon="radix-icons:magic-wand"),
        mb="md"
    ),
    dcc.Loading(html.Div(id='ia-output-setores-temporal')), 

], fluid=True)

@callback(
    [Output('grafico-relacao-setor', 'figure'),
     Output('grafico-media-setor', 'figure'),
     Output('grafico-contagem-setor', 'figure')],
    [Input("mantine-provider", "forceColorScheme")] 
)
def update_overview_graphs_theme(theme): 
    # Determine template based on global Mantine theme
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    
    # Use standard Plotly templates that look good
    # 'plotly_white' is cleaner than 'cosmo' for DMC
    
    fig1 = fig_relacao_peso_volume(df_setores, template)
    fig2 = fig_media_por_setor(df_setores, template)
    fig3 = fig_contagem_por_setor(df_setores, template)
    
    return fig1, fig2, fig3

@callback(
    [Output('grafico-media-setor-temporal', 'figure'),
     Output('lista-eventos-setor', 'children')],
    [Input('filtro-setor-temporal', 'value'),
     Input('filtro-ano-temporal', 'value'),
     Input("mantine-provider", "forceColorScheme")]
)
def update_temporal_graph_logic(setor_selecionado, ano_selecionado, theme):
    
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    
    if not setor_selecionado or not ano_selecionado:
        fig_vazia = px.line(title="Por favor, selecione um setor e um ano.", template=template)
        fig_vazia.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig_vazia, ""

    # Call Service
    df = get_dados_setor_temporal(setor_selecionado, ano_selecionado)
    
    meses_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    
    if not df.empty:
        df['mes_nome'] = df['mes'].map(meses_map)
        df = df.sort_values(by='mes')

    fig = px.line(
        df, 
        x='mes_nome' if not df.empty else [],
        y='media_peso' if not df.empty else [],
        markers=True,
        title=f"Média Mensal de Peso Corrigido: {setor_selecionado} ({ano_selecionado})",
        template=template
    )
    
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Peso Médio (kg)",
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    events_html = []

    # --- Check for Events ---
    try:
        events = Event.query.filter(
            extract('year', Event.start_date) <= ano_selecionado,
            extract('year', Event.end_date) >= ano_selecionado
        ).all()
        
        meses_ordem = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        fig.update_xaxes(categoryorder='array', categoryarray=meses_ordem)
        
        found_events = []

        for e in events:
            # Filtering logic remains the same
            if not e.affected_sectors: continue 
            affected_list = [s.strip() for s in e.affected_sectors.split(',')]
            is_generic = "Geral (Todos)" in affected_list or "Geral" in affected_list
            is_specific = setor_selecionado in affected_list
            
            if is_generic or is_specific:
                found_events.append(e)
                # ... graph annotation logic ...
                start_dt = e.start_date
                end_dt = e.end_date
                # Simple int casting for year comparison
                s_year = int(start_dt.year)
                e_year = int(end_dt.year)
                sel_year = int(ano_selecionado)

                start_month_idx = start_dt.month if s_year == sel_year else 1
                end_month_idx = end_dt.month if e_year == sel_year else 12
                
                if start_month_idx > end_month_idx: continue

                x0_val = (start_month_idx - 1) - 0.5
                x1_val = (end_month_idx - 1) + 0.5

                color_map = {
                    'Manutenção': 'orange',
                    'Escala': 'blue',
                    'Parada': 'red',
                    'Outro': 'gray'
                }
                color = color_map.get(e.event_type, 'gray')
                
                fig.add_vrect(
                    x0=x0_val, x1=x1_val,
                    fillcolor=color, opacity=0.1,
                    layer="below", line_width=0,
                    annotation_text=e.title,
                    annotation_position="top left",
                )

        if found_events:
            list_items = []
            for e in found_events:
                dt_str = f"{e.start_date.strftime('%d/%m/%Y')} a {e.end_date.strftime('%d/%m/%Y')}"
                badge_color = {
                    'Manutenção': 'yellow',
                    'Escala': 'blue',
                    'Parada': 'red',
                    'Outro': 'gray'
                }.get(e.event_type, 'gray')
                
                list_items.append(
                    dmc.Paper(
                        children=[
                            dmc.Group([
                                dmc.Text(e.title, fw=700),
                                dmc.Badge(e.event_type, color=badge_color)
                            ], justify="space-between", mb="xs"),
                            dmc.Text(f"Período: {dt_str}", size="sm", c="dimmed"),
                            dmc.Text(e.description, size="sm")
                        ],
                        withBorder=True, p="sm", mb="xs"
                    )
                )
            
            events_html = [
                dmc.Title("Eventos neste período:", order=5, mt="md", mb="sm"),
                dmc.ScrollArea(h=200, children=list_items)
            ]

    except Exception as ex:
        print(f"Erro ao carregar eventos no gráfico: {str(ex)}") 
    
    return fig, events_html


@callback(
    Output('ia-output-setores-overview', 'children'),
    Input('btn-ia-setores-overview', 'n_clicks'),
    prevent_initial_call=True
)
def get_ia_setores_overview(n_clicks):
    # Same logic, just updated output format if needed
    df_media = df_setores.sort_values(by='Média de Peso (kg)', ascending=False)
    df_volume = df_setores.sort_values(by='quantidade', ascending=False)
    
    dados_em_texto = f"""
    Dados de Análise de Setores:
    TOP 5 MEDIA PESO:
    {df_media.head(5).to_markdown(index=False)}
    TOP 5 VOLUME:
    {df_volume.head(5).to_markdown(index=False)}
    """
    prompt = f"Analise estes dados da coleta municipal de Rio Grande (Setores):\n{dados_em_texto}\nQuais os insights de eficiência vs volume?"
    return generate_analysis_component(prompt)

@callback(
    Output('ia-output-setores-temporal', 'children'),
    Input('btn-ia-setores-temporal', 'n_clicks'),
    [State('filtro-setor-temporal', 'value'),
     State('filtro-ano-temporal', 'value')],
    prevent_initial_call=True
)
def get_ia_setores_temporal(n_clicks, setor_selecionado, ano_selecionado):
    if not setor_selecionado or not ano_selecionado: return ""
    
    df = get_dados_setor_temporal(setor_selecionado, ano_selecionado)
    dados_txt = df.to_markdown(index=False)
    prompt = f"Analise a tendência mensal de peso para o setor {setor_selecionado} em {ano_selecionado}:\n{dados_txt}"
    return generate_analysis_component(prompt)