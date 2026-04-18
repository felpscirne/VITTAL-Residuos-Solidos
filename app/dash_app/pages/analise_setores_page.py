from dash import Input, Output, callback, dcc, html
import pandas as pd
import plotly.express as px
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import get_anos_options, get_dados_setores_macro, get_dados_setor_temporal
from app.services.ai_analytics import get_setor_clustering_analysis
from app.services.dashboard_summaries import summarize_setores_overview, summarize_setor_temporal
from app.services.event_markers import apply_event_markers, get_events_for_period
from app.services.management_insights import render_management_insight


APP_TIMEZONE = "America/Sao_Paulo"

df_setores = get_dados_setores_macro()
setores_options_temporal = sorted(
    [{"label": setor, "value": setor} for setor in df_setores["setor"].unique()],
    key=lambda item: item["label"],
) if not df_setores.empty else []
anos_options_temporal, ano_inicial_temporal = get_anos_options()
setor_inicial_temporal = setores_options_temporal[0]["value"] if setores_options_temporal else None


def fig_relacao_peso_volume(df, template):
    fig = px.scatter(
        df,
        x="quantidade",
        y="Média de Peso (kg)",
        title="Relação: média de peso x volume de registros por setor",
        labels={"quantidade": "Volume (contagem)", "Média de Peso (kg)": "Média de peso (kg)"},
        hover_name="setor",
        template=template,
    )
    fig.update_layout(height=500, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def fig_media_por_setor(df, template):
    df_sorted = df.sort_values(by="Média de Peso (kg)", ascending=False)
    fig = px.bar(
        df_sorted,
        x="setor",
        y="Média de Peso (kg)",
        title="Ranking: média de peso por setor",
        template=template,
    )
    fig.update_xaxes(tickangle=45)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def fig_contagem_por_setor(df, template):
    df_sorted = df.sort_values(by="quantidade", ascending=False)
    dynamic_height = max(400, len(df_sorted.index) * 20)
    fig = px.bar(
        df_sorted,
        x="quantidade",
        y="setor",
        orientation="h",
        title="Ranking: volume de registros por setor",
        template=template,
    )
    fig.update_layout(
        yaxis={"autorange": "reversed"},
        height=dynamic_height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _local_date_label(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(APP_TIMEZONE).tz_localize(None)
    return ts.strftime("%d/%m/%Y")


layout = dmc.Container(
    [
        dmc.Title("Análise de setores", order=2),
        dmc.Text(
            "Compare todos os setores entre si ou acompanhe a tendência de um setor específico ao longo do tempo.",
            c="dimmed",
            mb="lg",
        ),
        dmc.Divider(mb="lg"),
        dmc.Title("Visão geral: comparativo entre setores", order=3, mb="md"),
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.TabsTab("Matriz de relação", value="relacao", leftSection=DashIconify(icon="radix-icons:mix")),
                        dmc.TabsTab("Rankings individuais", value="individual", leftSection=DashIconify(icon="radix-icons:bar-chart")),
                    ]
                ),
                dmc.TabsPanel(
                    [
                        dmc.Alert(
                            "Este gráfico cruza número de registros com peso médio para identificar setores fora do padrão mais comum.",
                            title="Ajuda analítica",
                            color="blue",
                            variant="light",
                            mt="md",
                            mb="md",
                        ),
                        dmc.Card(dcc.Graph(id="grafico-relacao-setor"), withBorder=True, shadow="sm", radius="md", p="md"),
                    ],
                    value="relacao",
                ),
                dmc.TabsPanel(
                    [
                        dmc.Alert(
                            "Observe separadamente os setores com maior peso médio e os setores com maior demanda operacional.",
                            title="Ajuda analítica",
                            color="blue",
                            variant="light",
                            mt="md",
                            mb="md",
                        ),
                        dmc.SimpleGrid(
                            cols={"base": 1, "lg": 2},
                            spacing="md",
                            children=[
                                dmc.Card(dcc.Graph(id="grafico-media-setor"), withBorder=True, shadow="sm", radius="md", p="md"),
                                dmc.Card(dcc.Graph(id="grafico-contagem-setor"), withBorder=True, shadow="sm", radius="md", p="md"),
                            ],
                        ),
                    ],
                    value="individual",
                ),
            ],
            value="relacao",
            color="blue",
            mb="md",
        ),
        dmc.Card(dcc.Markdown(id="resumo-setores-overview"), withBorder=True, shadow="sm", radius="md", p="md", mb="md"),
        html.Div(id="insight-setores-overview-gerencial"),
        dmc.Card(
            [
                dmc.Title("Clustering de setores", order=4, mb="sm"),
                dmc.Text(
                    "A IA agrupa setores com comportamento parecido de volume, peso e discrepância operacional.",
                    c="dimmed",
                    size="sm",
                    mb="md",
                ),
                dcc.Loading(dcc.Graph(id="grafico-cluster-setores"), type="circle"),
                dcc.Markdown(id="resumo-cluster-setores"),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            p="md",
            mb="xl",
        ),
        dmc.Title("Drill-down: análise temporal por setor", order=3, mb="md"),
        dmc.Alert(
            "Acompanhe o comportamento mensal de um setor e observe a possível influência de eventos ocorridos no período.",
            color="gray",
            variant="light",
            mb="md",
        ),
        dmc.Grid(
            gutter="md",
            mb="md",
            children=[
                dmc.GridCol(
                    dmc.Select(
                        label="Selecione o setor",
                        id="filtro-setor-temporal",
                        data=setores_options_temporal,
                        value=setor_inicial_temporal,
                        searchable=True,
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    dmc.Select(
                        label="Selecione o ano",
                        id="filtro-ano-temporal",
                        data=anos_options_temporal,
                        value=str(ano_inicial_temporal) if ano_inicial_temporal else None,
                        allowDeselect=False,
                    ),
                    span=6,
                ),
            ],
        ),
        dmc.Card(
            [
                dcc.Graph(id="grafico-media-setor-temporal"),
                html.Div(id="lista-eventos-setor", style={"paddingTop": "20px"}),
                dcc.Markdown(id="resumo-setor-temporal"),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            p="md",
            mb="md",
        ),
        html.Div(id="insight-setor-temporal-gerencial"),
    ],
    fluid=True,
)


@callback(
    [
        Output("grafico-relacao-setor", "figure"),
        Output("grafico-media-setor", "figure"),
        Output("grafico-contagem-setor", "figure"),
        Output("resumo-setores-overview", "children"),
        Output("insight-setores-overview-gerencial", "children"),
    ],
    [Input("mantine-provider", "forceColorScheme")],
)
def update_overview_graphs_theme(theme):
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    current_df_setores = get_dados_setores_macro()
    summary = summarize_setores_overview(current_df_setores)
    return (
        fig_relacao_peso_volume(current_df_setores, template),
        fig_media_por_setor(current_df_setores, template),
        fig_contagem_por_setor(current_df_setores, template),
        summary,
        render_management_insight(summary),
    )


@callback(
    [
        Output("grafico-cluster-setores", "figure"),
        Output("resumo-cluster-setores", "children"),
    ],
    [Input("mantine-provider", "forceColorScheme")],
)
def update_setor_cluster_graph(theme):
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    cluster_result = get_setor_clustering_analysis()
    cluster_df = cluster_result.get("data")

    if cluster_result.get("available") and cluster_df is not None and not cluster_df.empty:
        cluster_fig = px.scatter(
            cluster_df,
            x="quantidade",
            y="media_peso",
            size="peso_total",
            color="cluster",
            hover_name="setor",
            title="Grupos de setores por comportamento operacional",
            labels={
                "quantidade": "Volume de registros",
                "media_peso": "Média de peso (kg)",
                "cluster": "Grupo",
            },
            template=template,
        )
        cluster_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return cluster_fig, cluster_result.get("summary", "")

    cluster_fig = px.scatter(title="Grupos de setores por comportamento operacional", template=template)
    cluster_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    cluster_fig.add_annotation(
        text=cluster_result.get("message", "Ainda não há dados suficientes para agrupar setores."),
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
    )
    return cluster_fig, cluster_result.get("summary", cluster_result.get("message", ""))


@callback(
    [
        Output("grafico-media-setor-temporal", "figure"),
        Output("lista-eventos-setor", "children"),
        Output("resumo-setor-temporal", "children"),
        Output("insight-setor-temporal-gerencial", "children"),
    ],
    [Input("filtro-setor-temporal", "value"), Input("filtro-ano-temporal", "value"), Input("mantine-provider", "forceColorScheme")],
)
def update_temporal_graph_logic(setor_selecionado, ano_selecionado, theme):
    template = "plotly_dark" if theme == "dark" else "plotly_white"
    if not setor_selecionado or not ano_selecionado:
        fig_vazia = px.line(title="Selecione um setor e um ano.", template=template)
        fig_vazia.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        summary = "### Resumo analítico\n- Selecione um setor e um ano para visualizar a série."
        return fig_vazia, "", summary, render_management_insight(summary)

    df = get_dados_setor_temporal(setor_selecionado, ano_selecionado)
    if not df.empty:
        df = df.sort_values(by="mes")
        df["periodo_data"] = pd.to_datetime(
            {
                "year": int(ano_selecionado),
                "month": df["mes"].astype(int),
                "day": 1,
            }
        )

    fig = px.line(
        df,
        x="periodo_data" if not df.empty else [],
        y="media_peso" if not df.empty else [],
        markers=True,
        title=f"Média mensal de peso corrigido: {setor_selecionado} ({ano_selecionado})",
        template=template,
    )
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Peso médio (kg)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(tickformat="%b", dtick="M1")

    events_html = []
    try:
        found_events = get_events_for_period(
            pd.Timestamp(f"{int(ano_selecionado)}-01-01"),
            pd.Timestamp(f"{int(ano_selecionado)}-12-31"),
            setor=setor_selecionado,
        )
        fig = apply_event_markers(fig, found_events)
        if found_events:
            items = []
            for event in found_events:
                dt_str = f"{_local_date_label(event.start_date)} a {_local_date_label(event.end_date)}"
                items.append(
                    dmc.Paper(
                        [
                            dmc.Text(event.title, fw=700),
                            dmc.Text(f"Período: {dt_str}", size="sm", c="dimmed"),
                            dmc.Text(event.description or "", size="sm"),
                        ],
                        withBorder=True,
                        p="sm",
                        mb="xs",
                    )
                )
            events_html = [
                dmc.Title("Eventos neste período:", order=5, mt="md", mb="sm"),
                dmc.ScrollArea(h=200, children=items),
            ]
    except Exception:
        events_html = []

    summary = summarize_setor_temporal(df, setor_selecionado, ano_selecionado)
    return fig, events_html, summary, render_management_insight(summary)
