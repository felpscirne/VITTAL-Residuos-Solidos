from dash import dcc, html, callback, dash_table, no_update
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import engine
from app.services.dashboard_summaries import summarize_fluxo_macro, summarize_fluxo_setor
from app.services.management_insights import render_management_insight


def load_fluxo_macro_data():
    query = """
    SELECT EXTRACT(YEAR FROM data_hora) as year, EXTRACT(MONTH FROM data_hora) as month,
           SUM(CASE WHEN setor = 'CANDIOTA' THEN peso_embalagem_liquido_corrigido ELSE 0 END) as saidas,
           SUM(CASE WHEN setor != 'CANDIOTA' AND setor != 'ACERTO DE PESO' THEN peso_embalagem_liquido_corrigido ELSE 0 END) as entradas
    FROM registro
    GROUP BY year, month
    ORDER BY year, month
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df
    df["balanco"] = (df["entradas"] - df["saidas"]).round(2)
    df["entradas"] = df["entradas"].round(2)
    df["saidas"] = df["saidas"].round(2)
    df["periodo"] = pd.to_datetime(df.assign(day=1)[["year", "month", "day"]]).dt.strftime("%Y-%m")
    return df


def load_fluxo_micro_data():
    query = """
    SELECT EXTRACT(YEAR FROM data_hora) as year, EXTRACT(MONTH FROM data_hora) as month, setor,
           SUM(peso_embalagem_liquido_corrigido) as peso_kg
    FROM registro
    WHERE setor != 'ACERTO DE PESO'
    GROUP BY year, month, setor
    ORDER BY year, month, setor
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df
    df["periodo"] = pd.to_datetime(df.assign(day=1)[["year", "month", "day"]]).dt.strftime("%Y-%m")
    return df


def get_setores_options_dynamic():
    df = load_fluxo_micro_data()
    if df.empty:
        return []
    setores = df[df["setor"] != "CANDIOTA"]["setor"].unique()
    return sorted([{"label": s, "value": s} for s in setores], key=lambda x: x["label"])


def create_macro_fluxo_graph(df, template):
    df_melted = df.melt(id_vars=["periodo"], value_vars=["entradas", "saidas"], var_name="tipo_fluxo", value_name="peso_kg")
    fig = px.bar(
        df_melted,
        x="periodo",
        y="peso_kg",
        color="tipo_fluxo",
        barmode="group",
        title="Fluxo mensal: entradas vs saídas (Candiota)",
        template=template,
    )
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def create_micro_fluxo_graph(df, setor_selecionado, template):
    df_comparativo = pd.concat([df[df["setor"] == "CANDIOTA"], df[df["setor"] == setor_selecionado]])
    fig = px.line(
        df_comparativo,
        x="periodo",
        y="peso_kg",
        color="setor",
        title=f"Comparativo mensal: {setor_selecionado} vs Candiota",
        markers=True,
        template=template,
    )
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


layout = html.Div(
    [
        dmc.Title("Análise de fluxo (entrada vs saída)", order=2),
        dmc.Text("Compare o volume de entrada por setores com o volume de saída registrado em Candiota.", c="dimmed", size="sm"),
        dmc.Divider(variant="solid", my="md"),
        dmc.Alert(
            "Observe equilíbrio entre o que entra no sistema e o que segue para destino final.",
            title="O que esta análise responde?",
            color="ifsc-green",
            variant="light",
            icon=DashIconify(icon="akar-icons:info"),
            mb="md",
        ),
        dmc.Text("Visão geral do balanço mensal", size="lg", fw=500, mb="sm"),
        dmc.Card(children=[dcc.Graph(id="grafico-fluxo-candiota")], withBorder=True, shadow="sm", radius="md", mb="md"),
        dmc.Card(
            children=[
                dmc.ScrollArea(
                    dash_table.DataTable(
                        id="tabela-fluxo-candiota",
                        columns=[
                            {"name": "Período", "id": "periodo"},
                            {"name": "Entradas (kg)", "id": "entradas"},
                            {"name": "Saídas (kg)", "id": "saidas"},
                            {"name": "Balanço (kg)", "id": "balanco"},
                        ],
                        data=[],
                        sort_action="native",
                        page_size=12,
                        style_header={"backgroundColor": "#f8f9fa", "color": "#000", "fontWeight": "bold", "fontFamily": "sans-serif"},
                        style_data={"backgroundColor": "#fff", "color": "#000", "fontFamily": "sans-serif"},
                        style_cell={"border": "1px solid #dee2e6", "padding": "10px"},
                    ),
                    offsetScrollbars=True,
                    type="auto",
                )
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            mb="md",
        ),
        dmc.Card(dcc.Markdown(id="resumo-fluxo-balanco"), withBorder=True, shadow="sm", radius="md", p="md", mb="xl"),
        html.Div(id="insight-fluxo-balanco-gerencial"),
        dmc.Text("Análise setorial detalhada (vs Candiota)", size="lg", fw=500, mb="sm"),
        dmc.Card(
            children=[
                dmc.Select(label="Selecione um setor para comparar", id="select-setor-micro", data=[], value=None, mb="md"),
                dmc.Grid(
                    gutter="md",
                    children=[
                        dmc.GridCol(dcc.Graph(id="grafico-setor-vs-candiota"), span={"base": 12, "md": 8}),
                        dmc.GridCol(html.Div(id="kpi-setor-participacao"), span={"base": 12, "md": 4}),
                    ],
                ),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            mb="md",
        ),
        dmc.Card(dcc.Markdown(id="resumo-fluxo-setor"), withBorder=True, shadow="sm", radius="md", p="md"),
        html.Div(id="insight-fluxo-setor-gerencial"),
    ]
)


@callback(Output("tabela-fluxo-candiota", "data"), Input("url", "pathname"))
def update_table_data(pathname):
    if pathname == "/fluxo-de-caixa":
        return load_fluxo_macro_data().to_dict("records")
    return no_update


@callback([Output("select-setor-micro", "data"), Output("select-setor-micro", "value")], Input("url", "pathname"))
def update_setores_dropdown(pathname):
    if pathname == "/fluxo-de-caixa":
        options = get_setores_options_dynamic()
        value = options[0]["value"] if options else None
        return options, value
    return no_update, no_update


@callback(
    [Output("grafico-fluxo-candiota", "figure"), Output("resumo-fluxo-balanco", "children"), Output("insight-fluxo-balanco-gerencial", "children")],
    [Input("url", "pathname"), Input("mantine-provider", "forceColorScheme")],
)
def update_macro_graph(pathname, color_scheme):
    if pathname != "/fluxo-de-caixa":
        return no_update, no_update, no_update
    df = load_fluxo_macro_data()
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    if df.empty:
        fig = px.bar(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        summary = summarize_fluxo_macro(df)
        return fig, summary, render_management_insight(summary)
    summary = summarize_fluxo_macro(df)
    return create_macro_fluxo_graph(df, template), summary, render_management_insight(summary)


@callback(
    [Output("grafico-setor-vs-candiota", "figure"), Output("kpi-setor-participacao", "children"), Output("resumo-fluxo-setor", "children"), Output("insight-fluxo-setor-gerencial", "children")],
    [Input("select-setor-micro", "value"), Input("mantine-provider", "forceColorScheme")],
)
def update_micro_graph(setor_selecionado, color_scheme):
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    if not setor_selecionado:
        fig = px.line(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", title="Selecione um setor para visualizar")
        summary = "### Resumo analítico\n- Selecione um setor para ver a participação relativa."
        return fig, dmc.Text("Selecione um setor.", c="dimmed"), summary, render_management_insight(summary)
    df = load_fluxo_micro_data()
    if df.empty:
        fig = px.line(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        summary = "### Resumo analítico\n- Não há dados de fluxo disponíveis."
        return fig, dmc.Text("Sem dados.", c="dimmed"), summary, render_management_insight(summary)
    total_saida = df[df["setor"] == "CANDIOTA"]["peso_kg"].sum()
    total_setor = df[df["setor"] == setor_selecionado]["peso_kg"].sum()
    pct = (total_setor / total_saida * 100) if total_saida > 0 else 0
    kpi = dmc.Stack(
        [
            dmc.Text("Participação no total de saída", size="xs", c="dimmed", tt="uppercase"),
            dmc.Text(f"{pct:.1f}%", fw=700, size="xl"),
            dmc.Text(f"{total_setor:,.0f} kg de {total_saida:,.0f} kg", size="sm", c="dimmed"),
        ]
    )
    summary = summarize_fluxo_setor(total_setor, total_saida, pct, setor_selecionado)
    return create_micro_fluxo_graph(df, setor_selecionado, template), kpi, summary, render_management_insight(summary)
