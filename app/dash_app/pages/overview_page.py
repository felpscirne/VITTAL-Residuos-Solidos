from dash import callback, dcc, html
from dash.dependencies import Input, Output
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import plotly.express as px

from app.application.analytics import (
    get_kpis_gerais,
    get_qtde_por_ano,
    get_top_produtos_geral,
    get_volume_mensal,
)
from app.services.event_markers import apply_event_markers, get_events_for_period
from app.services.management_insights import render_management_insight


def create_kpi_card(title, value, icon, color):
    return dmc.Card(
        children=[
            dmc.Group(
                [
                    dmc.Text(title, size="xs", c="dimmed", fw=500, style={"textTransform": "uppercase"}),
                    dmc.ThemeIcon(
                        DashIconify(icon=icon, width=20),
                        color=color,
                        variant="light",
                        size="lg",
                        radius="md",
                    ),
                ],
                justify="space-between",
                mb="xs",
            ),
            dmc.Text(value, fw=700, size="xl"),
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        p="md",
    )


layout = dmc.Container(
    [
        dmc.Title("Visão Geral do Dashboard", order=2, mb="xs"),
        dmc.Text(
            "Resumo operacional e previsão temporal do volume de resíduos com foco em planejamento.",
            c="dimmed",
            mb="lg",
        ),
        dmc.Alert(
            children=[
                dmc.Title("Indicadores operacionais", order=5, mb="xs"),
                dmc.Text(
                    "Esta página reúne indicadores consolidados da operação, permitindo acompanhar volume, período coberto e distribuição geral dos registros ao longo do tempo."
                ),
            ],
            title="Visão pública e institucional",
            color="ifsc-green",
            icon=DashIconify(icon="radix-icons:bar-chart"),
            mb="xl",
            variant="light",
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "sm": 2, "lg": 5},
            spacing="md",
            mb="xl",
            children=[
                html.Div(id="overview-kpi-total"),
                html.Div(id="overview-kpi-inicio"),
                html.Div(id="overview-kpi-fim"),
                html.Div(id="overview-kpi-volume"),
                html.Div(id="overview-kpi-media"),
            ],
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "xl": 2},
            spacing="md",
            mb="md",
            children=[
                dmc.Card(
                    dcc.Graph(id="overview-grafico-serie-mensal"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
                dmc.Card(
                    dcc.Graph(id="overview-grafico-ano"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
            ],
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "xl": 2},
            spacing="md",
            children=[
                dmc.Card(
                    dcc.Graph(id="overview-grafico-produtos"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
            ],
        ),
        html.Div(id="overview-management-insight"),
    ],
    fluid=True,
    p=0,
)


@callback(
    [
        Output("overview-kpi-total", "children"),
        Output("overview-kpi-inicio", "children"),
        Output("overview-kpi-fim", "children"),
        Output("overview-kpi-volume", "children"),
        Output("overview-kpi-media", "children"),
        Output("overview-grafico-serie-mensal", "figure"),
        Output("overview-grafico-ano", "figure"),
        Output("overview-grafico-produtos", "figure"),
        Output("overview-management-insight", "children"),
    ],
    [Input("mantine-provider", "forceColorScheme")],
)
def update_overview_graphs(color_scheme):
    template_name = "plotly_dark" if color_scheme == "dark" else "plotly_white"

    kpi_data = get_kpis_gerais()
    df_mensal = get_volume_mensal()
    df_ano = get_qtde_por_ano()
    df_produtos = get_top_produtos_geral()

    total_volume = "N/D"
    media_mensal = "N/D"
    if not df_mensal.empty:
        total_volume_value = float(df_mensal["y"].sum())
        media_mensal_value = float(df_mensal["y"].mean())
        total_volume = f"{total_volume_value:,.0f} kg".replace(",", ".")
        media_mensal = f"{media_mensal_value:,.0f} kg".replace(",", ".")

    kpi_total = create_kpi_card("Total de Registros", kpi_data["total"], "radix-icons:stack", "ifsc-green")
    kpi_inicio = create_kpi_card("Data de Inicio", kpi_data["inicio"], "radix-icons:calendar", "ifsc-green")
    kpi_fim = create_kpi_card("Data de Fim", kpi_data["fim"], "radix-icons:calendar", "ifsc-green")
    kpi_volume = create_kpi_card("Volume Acumulado", total_volume, "radix-icons:archive", "ifsc-green")
    kpi_media = create_kpi_card("Media Mensal", media_mensal, "radix-icons:bar-chart", "ifsc-green")

    fig_mensal = px.line(
        df_mensal,
        x="ds",
        y="y",
        markers=True,
        title="Serie Mensal de Volume de Residuos",
        labels={"ds": "Mes", "y": "Volume (kg)"},
        template=template_name,
    ) if not df_mensal.empty else px.line(template=template_name, title="Serie Mensal de Volume de Residuos")
    fig_mensal.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 20, "t": 50, "b": 30},
    )
    if not df_mensal.empty:
        eventos = get_events_for_period(df_mensal["ds"].min(), df_mensal["ds"].max())
        fig_mensal = apply_event_markers(fig_mensal, eventos)

    fig_ano = px.bar(
        df_ano,
        x="ano",
        y="qtde",
        title="Total de Registros por Ano",
        template=template_name,
    ) if not df_ano.empty else px.bar(template=template_name, title="Total de Registros por Ano")
    fig_ano.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 20, "t": 50, "b": 30},
    )

    fig_produtos = px.pie(
        df_produtos,
        names="produto",
        values="qtde",
        title="Top 10 Produtos por Volume de Registros",
        template=template_name,
    ) if not df_produtos.empty else px.pie(template=template_name, title="Top 10 Produtos por Volume de Registros")
    fig_produtos.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )

    lider_produto = "N/D"
    if not df_produtos.empty:
        lider_produto = str(df_produtos.iloc[0]["produto"])

    overview_summary = (
        "### Resumo analitico\n"
        f"- Total de registros consolidados: **{kpi_data['total']}**.\n"
        f"- Volume acumulado da serie: **{total_volume}**.\n"
        f"- Media do periodo consolidado: **{media_mensal}**.\n"
        f"- Produto de maior recorrencia: **{lider_produto}**.\n"
        "- Leitura gerencial: a visao geral permite relacionar escala operacional, distribuicao temporal e concentracao do mix de residuos antes de aprofundar a analise nas demais paginas."
    )

    return (
        kpi_total,
        kpi_inicio,
        kpi_fim,
        kpi_volume,
        kpi_media,
        fig_mensal,
        fig_ano,
        fig_produtos,
        render_management_insight(overview_summary),
    )
