from dash import dcc, html, callback, no_update
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import engine, get_anos_options
from app.services.ai_analytics import get_empresa_clustering_analysis
from app.services.dashboard_summaries import summarize_empresas_ranking, summarize_empresas_temporal
from app.services.management_insights import render_management_insight


def load_company_data():
    query = """
    SELECT fornecedor_cliente, COUNT(*) as quantidade, SUM(peso_embalagem_liquido_corrigido) as peso_total
    FROM registro
    WHERE fornecedor_cliente IS NOT NULL
    GROUP BY fornecedor_cliente
    ORDER BY quantidade DESC
    """
    return pd.read_sql(query, engine)


def get_empresas_options_dynamic():
    df = load_company_data()
    if df.empty:
        return [{"label": "Todas as Empresas", "value": "todas"}]
    opts = sorted([{"label": s, "value": s} for s in df["fornecedor_cliente"].unique()], key=lambda x: x["label"])
    opts.insert(0, {"label": "Todas as Empresas", "value": "todas"})
    return opts


def fig_contagem_empresas(df, template):
    dynamic_height = max(400, len(df.index) * 20)
    fig = px.bar(df, x="quantidade", y="fornecedor_cliente", orientation="h", title="Volume (n de registros) por empresa/entidade", template=template)
    fig.update_layout(yaxis={"autorange": "reversed"}, height=dynamic_height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


layout = html.Div(
    [
        dmc.Title("Análise de empresas e entidades", order=2),
        dmc.Text("Compare empresas/entidades ou analise a tendência de uma específica ao longo do tempo.", c="dimmed", size="sm"),
        dmc.Divider(variant="solid", my="md"),
        dmc.Title("Visão geral: ranking de empresas", order=3, my="sm"),
        dmc.Alert(
            "Quais entidades mais usam o sistema de pesagem e concentram o fluxo registrado?",
            title="O que este gráfico responde?",
            color="ifsc-green",
            variant="light",
            icon=DashIconify(icon="radix-icons:info-circled"),
            mb="md",
        ),
        dmc.Card([dcc.Graph(id="grafico-contagem-empresas")], withBorder=True, shadow="sm", radius="md", mb="md"),
        dmc.Card(dcc.Markdown(id="resumo-empresas-ranking"), withBorder=True, shadow="sm", radius="md", p="md", mb="md"),
        html.Div(id="insight-empresas-ranking-gerencial"),
        dmc.Card(
            [
                dmc.Title("Clustering de empresas", order=4, mb="sm"),
                dmc.Text(
                    "A IA aproxima empresas com comportamento parecido de volume, peso e discrepância operacional.",
                    c="dimmed",
                    size="sm",
                    mb="md",
                ),
                dcc.Graph(id="grafico-cluster-empresas"),
                dcc.Markdown(id="resumo-cluster-empresas"),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            p="md",
            mb="xl",
        ),
        dmc.Divider(label="Análise temporal", labelPosition="center", my="xl"),
        dmc.Title("Drill-down: análise mensal por empresa", order=3, my="sm"),
        dmc.Alert(
            "Acompanhe volume mensal e média de peso para avaliar carga operacional e perfil de atendimento.",
            title="O que esta análise responde?",
            color="ifsc-green",
            variant="light",
            icon=DashIconify(icon="akar-icons:statistic-up"),
            mb="md",
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "sm": 2},
            spacing="md",
            children=[
                dmc.Select(label="Selecione o ano", id="filtro-ano-empresa", data=[], value=None, clearable=False, leftSection=DashIconify(icon="clarity:calendar-line")),
                dmc.Select(label="Selecione a empresa", id="filtro-empresa-temporal", data=[], value="todas", searchable=True, nothingFoundMessage="Nenhuma empresa encontrada", leftSection=DashIconify(icon="domain")),
            ],
            mb="md",
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "md": 2},
            spacing="md",
            children=[
                dmc.Card([dcc.Graph(id="grafico-qtde-por-mes-empresa")], withBorder=True, shadow="sm", radius="md"),
                dmc.Card([dcc.Graph(id="grafico-media-peso-por-mes-empresa")], withBorder=True, shadow="sm", radius="md"),
            ],
            mb="md",
        ),
        dmc.Card(dcc.Markdown(id="resumo-empresas-temporal"), withBorder=True, shadow="sm", radius="md", p="md"),
        html.Div(id="insight-empresas-temporal-gerencial"),
    ]
)


@callback(Output("filtro-empresa-temporal", "data"), Input("url", "pathname"))
def update_empresas_dropdown(pathname):
    if pathname == "/analise-empresas":
        return get_empresas_options_dynamic()
    return no_update


@callback([Output("filtro-ano-empresa", "data"), Output("filtro-ano-empresa", "value")], Input("url", "pathname"))
def update_anos_dropdown_empresas(pathname):
    if pathname == "/analise-empresas":
        options, initial_val = get_anos_options()
        if not options:
            return [], None
        if not initial_val and options:
            initial_val = options[0]["value"]
        return options, initial_val
    return no_update, no_update


@callback(
    [
        Output("grafico-contagem-empresas", "figure"),
        Output("resumo-empresas-ranking", "children"),
        Output("insight-empresas-ranking-gerencial", "children"),
        Output("grafico-cluster-empresas", "figure"),
        Output("resumo-cluster-empresas", "children"),
    ],
    [Input("url", "pathname"), Input("mantine-provider", "forceColorScheme")],
)
def update_empresas_main_graph(pathname, color_scheme):
    if pathname != "/analise-empresas":
        return no_update, no_update, no_update, no_update, no_update
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    df = load_company_data()
    if df.empty:
        fig = px.bar(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        summary = "### Resumo analítico\n- Não há dados de empresas disponíveis."
        cluster_fig = px.scatter(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig, summary, render_management_insight(summary), cluster_fig, "Ainda não há dados suficientes para clustering."

    cluster_result = get_empresa_clustering_analysis()
    cluster_df = cluster_result.get("data")
    if cluster_result.get("available") and cluster_df is not None and not cluster_df.empty:
        cluster_fig = px.scatter(
            cluster_df,
            x="quantidade",
            y="media_peso",
            size="peso_total",
            color="cluster",
            hover_name="empresa",
            title="Grupos de empresas por comportamento operacional",
            labels={
                "quantidade": "Volume de registros",
                "media_peso": "Média de peso (kg)",
                "cluster": "Grupo",
            },
            template=template,
        )
        cluster_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        cluster_summary = cluster_result.get("summary", "")
    else:
        cluster_fig = px.scatter(title="Grupos de empresas por comportamento operacional", template=template)
        cluster_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        cluster_fig.add_annotation(
            text=cluster_result.get("message", "Ainda não há dados suficientes para clustering."),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        cluster_summary = cluster_result.get("summary", cluster_result.get("message", ""))

    summary = summarize_empresas_ranking(df.head(10))
    return fig_contagem_empresas(df, template), summary, render_management_insight(summary), cluster_fig, cluster_summary


@callback(
    [
        Output("grafico-qtde-por-mes-empresa", "figure"),
        Output("grafico-media-peso-por-mes-empresa", "figure"),
        Output("resumo-empresas-temporal", "children"),
        Output("insight-empresas-temporal-gerencial", "children"),
    ],
    [Input("filtro-ano-empresa", "value"), Input("filtro-empresa-temporal", "value"), Input("mantine-provider", "forceColorScheme")],
)
def update_temporal_graphs(ano_selecionado, empresa_selecionada, color_scheme):
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    if not ano_selecionado:
        empty_fig = px.bar(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", title="Aguardando seleção de ano...")
        summary = "### Resumo analítico\n- Selecione um ano para visualizar a série."
        return empty_fig, empty_fig, summary, render_management_insight(summary)

    base_query = " FROM registro WHERE EXTRACT(YEAR FROM data_hora) = %(ano)s"
    params = {"ano": ano_selecionado}
    if empresa_selecionada and empresa_selecionada != "todas":
        base_query += " AND fornecedor_cliente = %(empresa)s"
        params["empresa"] = empresa_selecionada

    query1 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, COUNT(*) AS qtde" + base_query + " GROUP BY mes ORDER BY mes"
    query2 = "SELECT EXTRACT(MONTH FROM data_hora) AS mes, AVG(peso_entrada) AS media" + base_query + " GROUP BY mes ORDER BY mes"
    df1 = pd.read_sql(query1, engine, params=params)
    df2 = pd.read_sql(query2, engine, params=params)
    meses_map = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    df1["mes_nome"] = df1["mes"].map(meses_map)
    df2["mes_nome"] = df2["mes"].map(meses_map)
    fig1 = px.bar(df1, x="mes_nome", y="qtde", title=f"Volume de registros ({empresa_selecionada}, {ano_selecionado})", template=template)
    fig2 = px.line(df2, x="mes_nome", y="media", title=f"Média de peso de entrada ({empresa_selecionada}, {ano_selecionado})", markers=True, template=template)
    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig2.update_layout(yaxis_title="Média de peso de entrada (kg)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    summary = summarize_empresas_temporal(df1[["mes_nome", "qtde"]], df2[["mes_nome", "media"]], empresa_selecionada, ano_selecionado)
    return fig1, fig2, summary, render_management_insight(summary)
