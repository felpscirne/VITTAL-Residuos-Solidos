from dash import dcc, html, callback, no_update
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from app.application.analytics import engine, get_anos_options
from app.services.dashboard_summaries import summarize_heatmap
from app.services.management_insights import render_management_insight


dias_map = {0: "Domingo", 1: "Segunda-feira", 2: "Terça-feira", 3: "Quarta-feira", 4: "Quinta-feira", 5: "Sexta-feira", 6: "Sábado"}
dias_completos = list(dias_map.values())
horas_completas = list(range(24))
meses_options = [{"label": "Ano inteiro", "value": "todos"}] + [{"label": nome, "value": str(i)} for i, nome in enumerate(["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], start=1)]


def load_heatmap_data():
    query = """
    SELECT EXTRACT(DOW FROM data_hora) as dia_semana_num, EXTRACT(HOUR FROM data_hora) as hora_do_dia,
           EXTRACT(YEAR FROM data_hora) as ano, EXTRACT(MONTH FROM data_hora) as mes, COUNT(*) as numero_de_registros
    FROM registro
    GROUP BY ano, mes, dia_semana_num, hora_do_dia
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df
    df["dia_semana"] = df["dia_semana_num"].map(dias_map)
    return df


def create_heatmap_graph(df_grouped, template):
    df_pivot = df_grouped.pivot_table(values="numero_de_registros", index="dia_semana", columns="hora_do_dia", fill_value=0)
    df_pivot = df_pivot.reindex(index=dias_completos, columns=horas_completas, fill_value=0)
    df_final = df_pivot.stack().reset_index(name="numero_de_registros")
    fig = px.density_heatmap(
        df_final,
        x="hora_do_dia",
        y="dia_semana",
        z="numero_de_registros",
        title="Mapa de calor: carga de trabalho da balança",
        labels={"hora_do_dia": "Hora do dia", "dia_semana": "Dia da semana", "numero_de_registros": "N de registros"},
        template=template,
        category_orders={"dia_semana": dias_completos, "hora_do_dia": horas_completas},
        color_continuous_scale="Viridis",
    )
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_nticks=24)
    return fig


layout = html.Div(
    [
        dmc.Title("Análise de horários de pico", order=2),
        dmc.Text("A análise mostra os pontos quentes da operação da balança ao cruzar dia da semana e hora.", c="dimmed", size="sm"),
        dmc.Divider(variant="solid", my="md"),
        dmc.Alert(
            "Identifique gargalos, picos de operação e janelas de menor carga.",
            title="O que este gráfico responde?",
            color="ifsc-green",
            variant="light",
            icon=DashIconify(icon="akar-icons:fire"),
            mb="md",
        ),
        dmc.Grid(
            gutter="md",
            children=[
                dmc.GridCol(dmc.Select(label="Selecione o ano", id="filtro-ano-heatmap", data=[], value="todos", clearable=False, leftSection=DashIconify(icon="clarity:calendar-line")), span={"base": 12, "md": 6}),
                dmc.GridCol(dmc.Select(label="Selecione o mês", id="filtro-mes-heatmap", data=meses_options, value="todos", clearable=False, leftSection=DashIconify(icon="clarity:date-line")), span={"base": 12, "md": 6}),
            ],
            mb="md",
        ),
        dmc.Card([dcc.Graph(id="grafico-heatmap")], withBorder=True, shadow="sm", radius="md", mb="md"),
        dmc.Card(dcc.Markdown(id="resumo-heatmap"), withBorder=True, shadow="sm", radius="md", p="md"),
        html.Div(id="insight-heatmap-gerencial"),
    ]
)


@callback(
    [Output("grafico-heatmap", "figure"), Output("resumo-heatmap", "children"), Output("insight-heatmap-gerencial", "children")],
    [Input("url", "pathname"), Input("filtro-ano-heatmap", "value"), Input("filtro-mes-heatmap", "value"), Input("mantine-provider", "forceColorScheme")],
)
def update_heatmap_graph(pathname, ano_val, mes_val, color_scheme):
    if pathname != "/analise-horarios":
        return no_update, no_update, no_update
    df = load_heatmap_data()
    template = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    if ano_val and ano_val != "todos":
        df = df[df["ano"] == int(ano_val)]
    if mes_val and mes_val != "todos":
        df = df[df["mes"] == int(mes_val)]
    if df.empty:
        fig = px.density_heatmap(template=template).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        summary = summarize_heatmap(df)
        return fig, summary, render_management_insight(summary)
    df_grouped = df.groupby(["dia_semana", "hora_do_dia"])["numero_de_registros"].sum().reset_index()
    summary = summarize_heatmap(df_grouped)
    return create_heatmap_graph(df_grouped, template), summary, render_management_insight(summary)


@callback([Output("filtro-ano-heatmap", "data"), Output("filtro-ano-heatmap", "value")], Input("url", "pathname"))
def update_anos_dropdown_horarios(pathname):
    if pathname == "/analise-horarios":
        options_raw, _ = get_anos_options()
        options = [{"label": opt["label"], "value": str(opt["value"])} for opt in options_raw]
        options.insert(0, {"label": "Todos os anos", "value": "todos"})
        return options, "todos"
    return no_update, no_update
