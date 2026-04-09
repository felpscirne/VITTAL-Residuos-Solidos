from dash import callback, dcc, html
from dash.dependencies import Input, Output
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import plotly.graph_objects as go

from app.application.analytics import get_setores_options, get_tipos_residuo_options
from app.application.forecasting import (
    get_entradas_mensais_forecast,
    get_public_data_context_markdown,
    get_saidas_mensais_forecast,
    get_setor_volume_mensal_forecast,
    get_volume_mensal_forecast,
)
from app.services.forecast_service import (
    build_forecast_summary_markdown,
    RIO_GRANDE_PUBLIC_CONTEXT,
)


HORIZON_OPTIONS = [
    {"label": "3 meses", "value": 3},
    {"label": "6 meses", "value": 6},
    {"label": "12 meses", "value": 12},
]

CONFIDENCE_OPTIONS = [
    {"label": "80%", "value": 0.80},
    {"label": "90%", "value": 0.90},
    {"label": "95%", "value": 0.95},
]


def _forecast_figure(result, title, template_name, confidence_label):
    fig = go.Figure()
    if result["status"] == "ok":
        history = result["history"]
        forecast = result["forecast"]
        observed_end = history["ds"].max()
        future_only = forecast[forecast["ds"] > observed_end].copy()

        fig.add_trace(
            go.Scatter(
                x=history["ds"],
                y=history["y"],
                mode="lines+markers",
                name="Realizado",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=forecast["ds"],
                y=forecast["yhat"],
                mode="lines",
                name="Previsto",
                line={"dash": "dash"},
            )
        )

        if not future_only.empty:
            fig.add_trace(
                go.Scatter(
                    x=future_only["ds"].tolist() + future_only["ds"].tolist()[::-1],
                    y=future_only["yhat_upper"].tolist() + future_only["yhat_lower"].tolist()[::-1],
                    fill="toself",
                    fillcolor="rgba(76, 175, 80, 0.15)",
                    line={"color": "rgba(255,255,255,0)"},
                    hoverinfo="skip",
                    name=f"Faixa de confianca ({confidence_label})",
                )
            )
    else:
        fig.add_annotation(
            text=result["message"],
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    fig.update_layout(
        title=title,
        template=template_name,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 20, "t": 50, "b": 30},
        xaxis_title="Mes",
        yaxis_title="Volume (kg)",
    )
    return fig


setores_options = get_setores_options()
setor_inicial = setores_options[0]["value"] if setores_options else None
tipos_residuo_options = get_tipos_residuo_options()
tipo_residuo_inicial = tipos_residuo_options[0]["value"] if tipos_residuo_options else "todos"


layout = dmc.Container(
    [
        dmc.Title("Previsoes com Prophet", order=2, mb="xs"),
        dmc.Text(
            "Modulo gerencial para previsao temporal de residuos, apoio logistico e planejamento orcamentario com dados publicos de Rio Grande - RS.",
            c="dimmed",
            mb="lg",
        ),
        dmc.Alert(
            children=[
                dmc.Title("Acesso restrito", order=5, mb="xs"),
                dmc.Text(
                    "As previsoes ficam disponiveis apenas para perfis com permissao especifica de gestao."
                ),
            ],
            title="Controle de acesso",
            color="orange",
            icon=DashIconify(icon="radix-icons:lock-closed"),
            mb="lg",
            variant="light",
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "lg": 4},
            spacing="md",
            mb="md",
            children=[
                dmc.Select(
                    id="previsao-horizonte-select",
                    label="Horizonte de previsao",
                    data=HORIZON_OPTIONS,
                    value=6,
                    allowDeselect=False,
                ),
                dmc.Select(
                    id="previsao-confianca-select",
                    label="Faixa de confianca",
                    data=CONFIDENCE_OPTIONS,
                    value=0.80,
                    allowDeselect=False,
                ),
                dmc.Select(
                    id="previsao-tipo-residuo-select",
                    label="Tipo de residuo",
                    data=tipos_residuo_options,
                    value=tipo_residuo_inicial,
                    allowDeselect=False,
                ),
                dmc.Card(
                    [
                        dmc.Text("Recorte geografico", fw=700, mb=4),
                        dmc.Text(
                            f"{RIO_GRANDE_PUBLIC_CONTEXT['city']} - {RIO_GRANDE_PUBLIC_CONTEXT['state']}, "
                            f"Brasil ({RIO_GRANDE_PUBLIC_CONTEXT['latitude']}, {RIO_GRANDE_PUBLIC_CONTEXT['longitude']})",
                            size="sm",
                            c="dimmed",
                        ),
                    ],
                    withBorder=True,
                    radius="md",
                    p="md",
                ),
            ],
        ),
        dmc.Card(
            [
                dmc.Title("Fontes publicas consideradas", order=4, mb="sm"),
                dcc.Markdown(
                    id="previsao-public-data-summary",
                    link_target="_blank",
                ),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            p="md",
            mb="md",
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "xl": 2},
            spacing="md",
            mb="md",
            children=[
                dmc.Card(
                    [
                        dcc.Graph(id="previsao-volume-total-graph"),
                        dcc.Markdown(id="previsao-volume-total-summary"),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
                dmc.Card(
                    [
                        dcc.Graph(id="previsao-entradas-graph"),
                        dcc.Markdown(id="previsao-entradas-summary"),
                    ],
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
            mb="md",
            children=[
                dmc.Card(
                    [
                        dcc.Graph(id="previsao-saidas-graph"),
                        dcc.Markdown(id="previsao-saidas-summary"),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    p="md",
                ),
                dmc.Card(
                    [
                        dmc.Select(
                            id="previsao-setor-select",
                            label="Setor para previsao especifica",
                            data=setores_options,
                            value=setor_inicial,
                            searchable=True,
                            mb="md",
                        ),
                        dcc.Graph(id="previsao-setor-graph"),
                        dcc.Markdown(id="previsao-setor-summary"),
                    ],
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
        Output("previsao-volume-total-graph", "figure"),
        Output("previsao-volume-total-summary", "children"),
        Output("previsao-entradas-graph", "figure"),
        Output("previsao-entradas-summary", "children"),
        Output("previsao-saidas-graph", "figure"),
        Output("previsao-saidas-summary", "children"),
        Output("previsao-setor-graph", "figure"),
        Output("previsao-setor-summary", "children"),
        Output("previsao-public-data-summary", "children"),
    ],
    [
        Input("mantine-provider", "forceColorScheme"),
        Input("previsao-setor-select", "value"),
        Input("previsao-horizonte-select", "value"),
        Input("previsao-confianca-select", "value"),
        Input("previsao-tipo-residuo-select", "value"),
    ],
)
def update_previsoes(color_scheme, setor, horizonte, confianca, tipo_residuo):
    template_name = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    horizonte = int(horizonte or 6)
    confianca = float(confianca or 0.80)
    confidence_label = f"{int(confianca * 100)}%"
    tipo_residuo = tipo_residuo or "todos"
    tipo_label = next(
        (opt["label"] for opt in tipos_residuo_options if opt["value"] == tipo_residuo),
        "Todos os residuos",
    )

    total_result = get_volume_mensal_forecast(
        periods=horizonte,
        interval_width=confianca,
        tipo_residuo=tipo_residuo,
    )
    entradas_result = get_entradas_mensais_forecast(
        periods=horizonte,
        interval_width=confianca,
        tipo_residuo=tipo_residuo,
    )
    saidas_result = get_saidas_mensais_forecast(
        periods=horizonte,
        interval_width=confianca,
        tipo_residuo=tipo_residuo,
    )
    setor_result = get_setor_volume_mensal_forecast(
        setor,
        periods=horizonte,
        interval_width=confianca,
        tipo_residuo=tipo_residuo,
    ) if setor else {
        "status": "no_data",
        "message": "Selecione um setor para visualizar a previsao.",
    }

    return (
        _forecast_figure(
            total_result,
            f"Previsao do Volume Total - {tipo_label}",
            template_name,
            confidence_label,
        ),
        build_forecast_summary_markdown(total_result),
        _forecast_figure(
            entradas_result,
            f"Previsao das Entradas - {tipo_label}",
            template_name,
            confidence_label,
        ),
        build_forecast_summary_markdown(entradas_result),
        _forecast_figure(
            saidas_result,
            f"Previsao das Saidas para Candiota - {tipo_label}",
            template_name,
            confidence_label,
        ),
        build_forecast_summary_markdown(saidas_result),
        _forecast_figure(
            setor_result,
            f"Previsao do Setor: {setor or 'N/D'} - {tipo_label}",
            template_name,
            confidence_label,
        ),
        build_forecast_summary_markdown(setor_result),
        get_public_data_context_markdown(total_result),
    )
