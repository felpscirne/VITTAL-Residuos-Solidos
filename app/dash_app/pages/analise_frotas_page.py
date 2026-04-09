from dash import dcc, html, callback, no_update
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import engine
from app.services.dashboard_summaries import summarize_frota


def load_frota_data():
    query = """
    SELECT placa_veiculo, COALESCE(fornecedor_cliente, 'Nao Especificada') as entidade_responsavel,
           COUNT(*) as total_viagens, AVG(peso_liquido) as peso_medio_por_viagem
    FROM registro
    WHERE setor != 'CANDIOTA' AND setor != 'ACERTO DE PESO' AND peso_liquido > 0
    GROUP BY placa_veiculo, fornecedor_cliente
    ORDER BY total_viagens DESC;
    """
    df = pd.read_sql(query, engine)
    df["peso_medio_por_viagem"] = df["peso_medio_por_viagem"].round(2)
    return df


def create_frota_scatter_graph(df, template):
    fig = px.scatter(df, x="total_viagens", y="peso_medio_por_viagem", title="Eficiencia (Peso Medio) vs. Volume por Veiculo", labels={"total_viagens": "Total de Viagens", "peso_medio_por_viagem": "Peso Medio por Viagem"}, hover_name="placa_veiculo", color="entidade_responsavel", template=template)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def create_frota_ranking_graph(df, template):
    df_piores = df.nsmallest(15, "peso_medio_por_viagem").copy()
    df_piores["tipo"] = "15 Piores"
    df_melhores = df.nlargest(15, "peso_medio_por_viagem").copy()
    df_melhores["tipo"] = "15 Melhores"
    df_ranking = pd.concat([df_piores, df_melhores])
    fig = px.bar(df_ranking, x="peso_medio_por_viagem", y="placa_veiculo", orientation="h", color="tipo", title="Ranking de Eficiencia de Veiculos", template=template, facet_col="tipo")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_yaxes(matches=None, showticklabels=True)
    return fig


layout = html.Div([
    dmc.Title("Analise de Eficiencia da Frota", order=2),
    dmc.Text("Identifique veiculos mais e menos eficientes da operacao de coleta.", c="dimmed", size="sm"),
    dmc.Divider(variant="solid", my="md"),
    dmc.Alert("Placas com muitas viagens e baixo peso medio merecem atencao operacional.", title="Dica de analise", color="ifsc-green", variant="light", icon=DashIconify(icon="akar-icons:light-bulb"), mb="md"),
    dmc.Card(
        [
            dmc.Grid(
                gutter="md",
                children=[
                    dmc.GridCol(dmc.Select(label="Filtrar por Empresa/Entidade", id="filtro-entidade-frota", data=[{"label": "Todas as Entidades", "value": "todas"}], value="todas", leftSection=DashIconify(icon="domain")), span={"base": 12, "md": 6}),
                    dmc.GridCol([dmc.Text(id="label-slider-frota", children="Filtrar por N minimo de viagens: 0", size="sm", fw=500, mb=5), dmc.Slider(id="filtro-viagens-frota", min=0, max=500, step=1, value=0, updatemode="drag", color="teal", marks=[{"value": 0, "label": "0"}, {"value": 250, "label": "250"}, {"value": 500, "label": "500"}])], span={"base": 12, "md": 6}),
                ],
            )
        ],
        withBorder=True, shadow="sm", radius="md", mb="md"
    ),
    dmc.Card(dcc.Markdown(id="resumo-frota"), withBorder=True, shadow="sm", radius="md", p="md", mb="md"),
    dmc.Card([dcc.Graph(id="grafico-frota-scatter")], withBorder=True, shadow="sm", radius="md", mb="md"),
    dmc.Card([dcc.Graph(id="grafico-frota-ranking")], withBorder=True, shadow="sm", radius="md", mb="md"),
])


@callback([Output("filtro-entidade-frota", "data"), Output("filtro-viagens-frota", "max"), Output("filtro-viagens-frota", "marks")], Input("url", "pathname"))
def update_frota_filters(pathname):
    if pathname == "/analise-frotas":
        df = load_frota_data()
        if df.empty:
            return [{"label": "Todas as Entidades", "value": "todas"}], 100, {0: "0"}
        ents = sorted([{"label": t, "value": t} for t in df["entidade_responsavel"].unique()], key=lambda x: x["label"])
        ents.insert(0, {"label": "Todas as Entidades", "value": "todas"})
        max_v = int(df["total_viagens"].max())
        return ents, max_v, {0: "0", int(max_v / 2): str(int(max_v / 2)), max_v: str(max_v)}
    return no_update, no_update, no_update


@callback(
    [Output("grafico-frota-scatter", "figure"), Output("grafico-frota-ranking", "figure"), Output("label-slider-frota", "children"), Output("resumo-frota", "children")],
    [Input("url", "pathname"), Input("filtro-entidade-frota", "value"), Input("filtro-viagens-frota", "value"), Input("mantine-provider", "forceColorScheme")],
)
def update_frota_graphs(pathname, entidade, min_viagens, color_scheme):
    if pathname != "/analise-frotas":
        return no_update, no_update, no_update, no_update
    df = load_frota_data()
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    if entidade and entidade != "todas":
        df = df[df["entidade_responsavel"] == entidade]
    if min_viagens is not None:
        df = df[df["total_viagens"] >= min_viagens]
    if df.empty:
        empty_fig = px.scatter(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return empty_fig, empty_fig, f"Filtrar por N minimo de viagens: {min_viagens}", summarize_frota(df)
    return create_frota_scatter_graph(df, template), create_frota_ranking_graph(df, template), f"Filtrar por N minimo de viagens: {min_viagens}", summarize_frota(df)
