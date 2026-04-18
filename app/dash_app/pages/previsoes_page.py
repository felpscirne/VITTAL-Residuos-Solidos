from dash import callback, dcc, html
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
import plotly.graph_objects as go

from app.application.analytics import get_setores_options, get_tipos_residuo_options
from app.application.forecasting import (
    get_entradas_diarias_forecast,
    get_public_data_context_markdown,
    get_saidas_diarias_forecast,
    get_setor_volume_diario_forecast,
    get_volume_diario_forecast,
)
from app.services.forecast_service import (
    RIO_GRANDE_PUBLIC_CONTEXT,
    build_forecast_summary_markdown,
)
from app.services.temporal_charts import apply_temporal_layout


DAILY_PRESETS = [
    {"label": "7 dias", "value": "7"},
    {"label": "10 dias", "value": "10"},
    {"label": "15 dias", "value": "15"},
    {"label": "30 dias", "value": "30"},
]

CONFIDENCE_OPTIONS = [
    {"label": "80%", "value": "0.80"},
    {"label": "90%", "value": "0.90"},
    {"label": "95%", "value": "0.95"},
]

RETROSPECTIVE_OPTIONS = [
    {"label": "7 dias", "value": "7"},
    {"label": "14 dias", "value": "14"},
    {"label": "21 dias", "value": "21"},
    {"label": "30 dias", "value": "30"},
    {"label": "45 dias", "value": "45"},
    {"label": "60 dias", "value": "60"},
]


def _interval_label(confidence: float) -> str:
    return f"{int(confidence * 100)}%"

def _forecast_figure(result, title, template_name, interval_label, revision_token):
    fig = go.Figure()
    history_points = 0
    if result["status"] == "ok":
        history = result["history"]
        forecast = result["forecast"]
        history_points = len(history.index)
        observed_end = history["ds"].max()
        future_only = forecast[forecast["ds"] > observed_end].copy()

        fig.add_trace(
            go.Scatter(
                x=history["ds"],
                y=history["y"],
                mode="lines+markers",
                name="Realizado",
                connectgaps=False,
            )
        )

        if not future_only.empty:
            bridge_x = [observed_end] + future_only["ds"].tolist()
            bridge_y = [history.loc[history["ds"] == observed_end, "y"].iloc[0]] + future_only["yhat"].tolist()

            fig.add_trace(
                go.Scatter(
                    x=bridge_x,
                    y=bridge_y,
                    mode="lines+markers",
                    name="Previsto",
                    line={"dash": "dash"},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=future_only["ds"].tolist() + future_only["ds"].tolist()[::-1],
                    y=future_only["yhat_upper"].tolist() + future_only["yhat_lower"].tolist()[::-1],
                    fill="toself",
                    fillcolor="rgba(76, 175, 80, 0.15)",
                    line={"color": "rgba(255,255,255,0)"},
                    hoverinfo="skip",
                    name=f"Intervalo preditivo ({interval_label})",
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
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(
            title=title,
            template=template_name,
            height=180,
            margin={"l": 20, "r": 20, "t": 48, "b": 20},
            uirevision=revision_token,
            datarevision=revision_token,
        )
        return fig

    fig.update_layout(title=title, template=template_name, height=420)
    fig.update_layout(uirevision=revision_token, datarevision=revision_token)
    apply_temporal_layout(
        fig,
        granularity="diaria",
        n_points=history_points,
        xaxis_title="Data",
        yaxis_title="Volume (kg)",
    )
    return fig


setores_options = get_setores_options()
setor_inicial = setores_options[0]["value"] if setores_options else None
tipos_residuo_options = get_tipos_residuo_options()
tipo_residuo_inicial = tipos_residuo_options[0]["value"] if tipos_residuo_options else "todos"


layout = dmc.Container(
    [
        dmc.Title("Previsão Inteligente", order=2, mb="xs"),
        dmc.Text(
            "Módulo gerencial de projeção diária para apoio logístico e planejamento. "
            "O gestor escolhe o horizonte de dias, a janela de validação retrospectiva "
            "e o intervalo preditivo nominal que deseja visualizar.",
            c="dimmed",
            mb="lg",
        ),
        dmc.Alert(
            [
                dmc.Text("Como ler esta página", fw=700, mb=4),
                dmc.Text(
                    "A linha principal mostra o histórico diário e a continuação prevista. "
                    "A faixa ao redor da previsão mostra a variação provável estimada a partir do erro recente, "
                    "com limite para evitar ampliar o gráfico além do que a série já demonstrou como plausível. "
                    "A janela retrospectiva define quantos dias já conhecidos o sistema usa para medir o erro antes de prever o futuro.",
                    size="sm",
                ),
            ],
            color="ifsc-green",
            variant="light",
            mb="md",
        ),
        dmc.SimpleGrid(
            cols={"base": 1, "lg": 5},
            spacing="md",
            mb="md",
            children=[
                html.Div(
                    [
                        dmc.Text("Horizonte (dias)", size="sm", fw=500, mb=4),
                        dmc.SegmentedControl(
                            id="previsao-horizonte-preset",
                            data=DAILY_PRESETS,
                            value="30",
                            fullWidth=True,
                            mb=6,
                        ),
                        dmc.NumberInput(
                            id="previsao-horizonte-custom",
                            description="Quantos dias à frente deseja projetar. Horizontes maiores aumentam a incerteza.",
                            value=30,
                            min=1,
                            max=365,
                            step=1,
                        ),
                    ]
                ),
                dmc.Select(
                    id="previsao-confianca-select",
                    label="Intervalo preditivo nominal",
                    data=CONFIDENCE_OPTIONS,
                    value="0.80",
                    allowDeselect=False,
                    description="Controla a largura nominal da faixa de incerteza. Valores maiores tornam o intervalo mais conservador.",
                ),
                dmc.Select(
                    id="previsao-validacao-select",
                    label="Janela de validação retrospectiva",
                    data=RETROSPECTIVE_OPTIONS,
                    value="30",
                    allowDeselect=False,
                    description="Define quantos dias do histórico recente serão usados para verificar o erro do modelo.",
                ),
                dmc.Select(
                    id="previsao-tipo-residuo-select",
                    label="Tipo de resíduo",
                    data=tipos_residuo_options,
                    value=tipo_residuo_inicial,
                    allowDeselect=False,
                ),
                dmc.Card(
                    [
                        dmc.Text("Recorte geográfico", fw=700, mb=4),
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
            withBorder=True,
            radius="md",
            p="md",
            mb="md",
            children=[
                dmc.Switch(
                    id="previsao-missing-toggle",
                    label="Deixar o sistema lidar com lacunas da série",
                    checked=True,
                    mb="xs",
                ),
                dmc.Text(
                    "Quando ativado, os dias faltantes permanecem ausentes na série e o sistema os considera diretamente no ajuste. "
                    "Quando desativado, os dias faltantes são preenchidos com zero antes da análise.",
                    size="sm",
                    c="dimmed",
                    mb="sm",
                ),
                dmc.Text(id="previsao-confianca-banner-text", size="sm", c="dimmed"),
            ],
        ),
        dcc.Loading(
            type="circle",
            color="#0b7285",
            children=[
                dmc.Card(
                    [
                        dmc.Title("Fontes públicas consideradas", order=4, mb="sm"),
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
                                    label="Setor para previsão específica",
                                    data=setores_options,
                                    value=setor_inicial,
                                    searchable=True,
                                    mb="lg",
                                ),
                                dcc.Graph(id="previsao-setor-graph", style={"marginTop": "1rem"}),
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
        ),
    ],
    fluid=True,
    p=0,
)


@callback(
    Output("previsao-horizonte-custom", "value"),
    Input("previsao-horizonte-preset", "value"),
    State("previsao-horizonte-custom", "value"),
    prevent_initial_call=True,
)
def sync_preset_to_custom(preset_value, current_custom):
    if preset_value is None:
        return current_custom
    try:
        return int(preset_value)
    except (TypeError, ValueError):
        return current_custom


def _resolve_horizon(horizonte_custom):
    try:
        return max(1, min(365, int(horizonte_custom or 30)))
    except (TypeError, ValueError):
        return 30


@callback(
    [
        Output("previsao-volume-total-graph", "figure"),
        Output("previsao-volume-total-summary", "children"),
        Output("previsao-entradas-graph", "figure"),
        Output("previsao-entradas-summary", "children"),
        Output("previsao-saidas-graph", "figure"),
        Output("previsao-saidas-summary", "children"),
        Output("previsao-public-data-summary", "children"),
        Output("previsao-confianca-banner-text", "children"),
    ],
    [
        Input("mantine-provider", "forceColorScheme"),
        Input("previsao-horizonte-custom", "value"),
        Input("previsao-confianca-select", "value"),
        Input("previsao-validacao-select", "value"),
        Input("previsao-tipo-residuo-select", "value"),
        Input("previsao-missing-toggle", "checked"),
    ],
)
def update_previsoes_gerais(color_scheme, horizonte_custom, confianca, validacao, tipo_residuo, prophet_missing_toggle):
    template_name = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    confianca = float(confianca or 0.80)
    horizonte = _resolve_horizon(horizonte_custom)
    validacao = max(7, int(validacao or 30))
    interval_label = _interval_label(confianca)
    tipo_residuo = tipo_residuo or "todos"
    fill_missing = not bool(prophet_missing_toggle)
    tipo_label = next(
        (opt["label"] for opt in tipos_residuo_options if opt["value"] == tipo_residuo),
        "Todos os resíduos",
    )

    total_result = get_volume_diario_forecast(
        periods=horizonte,
        interval_width=confianca,
        tipo_residuo=tipo_residuo,
        validation_window=validacao,
        fill_missing=fill_missing,
        cache_version="daily-gap-v2",
    )
    entradas_result = get_entradas_diarias_forecast(
        periods=horizonte,
        interval_width=confianca,
        tipo_residuo=tipo_residuo,
        validation_window=validacao,
        fill_missing=fill_missing,
        cache_version="daily-gap-v2",
    )
    saidas_result = get_saidas_diarias_forecast(
        periods=horizonte,
        interval_width=confianca,
        tipo_residuo=tipo_residuo,
        validation_window=validacao,
        fill_missing=fill_missing,
        cache_version="daily-gap-v2",
    )

    unidade = "dia" if horizonte == 1 else "dias"
    banner_text = (
        f"Horizonte solicitado: {horizonte} {unidade}. "
        f"Intervalo preditivo nominal: {interval_label}. "
        f"Janela de validação retrospectiva: {validacao} dias. "
        f"Tratamento manual de lacunas com zero: {'ativo' if fill_missing else 'desativado'}."
    )
    revision_token = f"{horizonte}-{confianca}-{validacao}-{tipo_residuo}-{fill_missing}"

    return (
        _forecast_figure(
            total_result,
            f"Previsão do volume total - {tipo_label}",
            template_name,
            interval_label,
            revision_token + "-total",
        ),
        build_forecast_summary_markdown(total_result),
        _forecast_figure(
            entradas_result,
            f"Previsão das entradas - {tipo_label}",
            template_name,
            interval_label,
            revision_token + "-entradas",
        ),
        build_forecast_summary_markdown(entradas_result),
        _forecast_figure(
            saidas_result,
            f"Previsão das saídas para Candiota - {tipo_label}",
            template_name,
            interval_label,
            revision_token + "-saidas",
        ),
        build_forecast_summary_markdown(saidas_result),
        get_public_data_context_markdown(total_result),
        banner_text,
    )


@callback(
    [
        Output("previsao-setor-graph", "figure"),
        Output("previsao-setor-summary", "children"),
    ],
    [
        Input("mantine-provider", "forceColorScheme"),
        Input("previsao-setor-select", "value"),
        Input("previsao-horizonte-custom", "value"),
        Input("previsao-confianca-select", "value"),
        Input("previsao-validacao-select", "value"),
        Input("previsao-tipo-residuo-select", "value"),
        Input("previsao-missing-toggle", "checked"),
    ],
)
def update_previsao_setorial(color_scheme, setor, horizonte_custom, confianca, validacao, tipo_residuo, prophet_missing_toggle):
    template_name = "plotly_dark" if color_scheme == "dark" else "plotly_white"
    confianca = float(confianca or 0.80)
    horizonte = _resolve_horizon(horizonte_custom)
    validacao = max(7, int(validacao or 30))
    interval_label = _interval_label(confianca)
    tipo_residuo = tipo_residuo or "todos"
    fill_missing = not bool(prophet_missing_toggle)
    tipo_label = next(
        (opt["label"] for opt in tipos_residuo_options if opt["value"] == tipo_residuo),
        "Todos os resíduos",
    )

    if not setor:
        setor_result = {
            "status": "no_data",
            "message": "Selecione um setor para visualizar a previsão.",
        }
    else:
        setor_result = get_setor_volume_diario_forecast(
            setor,
            periods=horizonte,
            interval_width=confianca,
            tipo_residuo=tipo_residuo,
            validation_window=validacao,
            fill_missing=fill_missing,
            cache_version="daily-gap-v2",
        )
    revision_token = f"{setor}-{horizonte}-{confianca}-{validacao}-{tipo_residuo}-{fill_missing}"

    return (
        _forecast_figure(
            setor_result,
            f"Previsão do setor: {setor or 'N/D'} - {tipo_label}",
            template_name,
            interval_label,
            revision_token,
        ),
        build_forecast_summary_markdown(setor_result),
    )
