from dash import callback, dcc, html
from dash.dependencies import Input, Output
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import plotly.express as px
import plotly.graph_objects as go

from app.application.analytics import (
    get_kpis_gerais,
    get_top_produtos_geral,
    get_volume_mensal,
)
from app.application.forecasting import (
    get_volume_mensal_forecast,
    get_volume_mensal_forecast_summary,
)


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
        dmc.Title("Visao Geral do Dashboard", order=2, mb="xs"),
        dmc.Text(
            "Resumo operacional e previsao temporal do volume de residuos com foco em planejamento.",
            c="dimmed",
            mb="lg",
        ),
        dmc.Alert(
            children=[
                dmc.Title("Nova abordagem analitica", order=5, mb="xs"),
                dmc.Text(
                    "Esta tela prioriza metricas consolidadas e previsao temporal para apoiar "
                    "o planejamento logistico e orcamentario do projeto."
                ),
            ],
            title="Contexto do TCC",
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
                    dcc.Graph(id="overview-grafico-forecast"),
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
                dmc.Card(
                    dcc.Markdown(id="overview-forecast-summary"),
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
            ],
        ),
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
        Output("overview-grafico-forecast", "figure"),
        Output("overview-grafico-produtos", "figure"),
        Output("overview-forecast-summary", "children"),
    ],
    [Input("mantine-provider", "forceColorScheme")],
)
def update_overview_graphs(color_scheme):
    template_name = "plotly_dark" if color_scheme == "dark" else "plotly_white"

    kpi_data = get_kpis_gerais()
    df_mensal = get_volume_mensal()
    df_produtos = get_top_produtos_geral()
    forecast_result = get_volume_mensal_forecast(periods=6)
    forecast_summary = get_volume_mensal_forecast_summary(periods=6)

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

    fig_forecast = go.Figure()
    if forecast_result["status"] == "ok":
        history = forecast_result["history"]
        forecast = forecast_result["forecast"]
        observed_end = history["ds"].max()
        future_only = forecast[forecast["ds"] > observed_end].copy()

        fig_forecast.add_trace(
            go.Scatter(
                x=history["ds"],
                y=history["y"],
                mode="lines+markers",
                name="Realizado",
            )
        )
        fig_forecast.add_trace(
            go.Scatter(
                x=forecast["ds"],
                y=forecast["yhat"],
                mode="lines",
                name="Previsto",
                line={"dash": "dash"},
            )
        )
        fig_forecast.add_trace(
            go.Scatter(
                x=future_only["ds"].tolist() + future_only["ds"].tolist()[::-1],
                y=future_only["yhat_upper"].tolist() + future_only["yhat_lower"].tolist()[::-1],
                fill="toself",
                fillcolor="rgba(76, 175, 80, 0.15)",
                line={"color": "rgba(255,255,255,0)"},
                hoverinfo="skip",
                name="Intervalo de confianca",
            )
        )
        fig_forecast.update_layout(title="Previsao Mensal com Prophet")
    else:
        fig_forecast = px.line(template=template_name, title="Previsao Mensal com Prophet")
        fig_forecast.add_annotation(
            text=forecast_result["message"],
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    fig_forecast.update_layout(
        template=template_name,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 20, "t": 50, "b": 30},
        xaxis_title="Mes",
        yaxis_title="Volume (kg)",
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

    return (
        kpi_total,
        kpi_inicio,
        kpi_fim,
        kpi_volume,
        kpi_media,
        fig_mensal,
        fig_forecast,
        fig_produtos,
        forecast_summary,
    )
