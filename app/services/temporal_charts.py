from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


GranularityLiteral = str  


def infer_granularity(series: pd.Series) -> GranularityLiteral:
    if series is None or series.empty:
        return "mensal"
    try:
        diffs = pd.to_datetime(series).sort_values().diff().dropna()
    except Exception:
        return "mensal"
    if diffs.empty:
        return "mensal"
    mediana = diffs.median()
    if mediana <= pd.Timedelta(days=2):
        return "diaria"
    if mediana <= pd.Timedelta(days=20):
        return "quinzenal"
    if mediana <= pd.Timedelta(days=45):
        return "mensal"
    return "anual"


def _tick_format_for(granularity: GranularityLiteral) -> str:
    return {
        "diaria": "%d/%m",
        "quinzenal": "%d/%m/%Y",
        "mensal": "%b/%Y",
        "anual": "%Y",
    }.get(granularity, "%d/%m/%Y")


def _marker_settings(n_points: int, granularity: GranularityLiteral) -> dict[str, Any]:
    """Define tamanho dos marcadores e modo de linha em função da densidade."""
    if granularity == "diaria":
        if n_points > 180:
            return {"mode": "lines", "marker_size": 0, "line_width": 1.6}
        if n_points > 60:
            return {"mode": "lines+markers", "marker_size": 3, "line_width": 1.8}
        return {"mode": "lines+markers", "marker_size": 5, "line_width": 2.0}
    if granularity == "quinzenal":
        if n_points > 40:
            return {"mode": "lines+markers", "marker_size": 4, "line_width": 1.8}
        return {"mode": "lines+markers", "marker_size": 6, "line_width": 2.0}
    return {"mode": "lines+markers", "marker_size": 7, "line_width": 2.2}


def _range_selector_for(granularity: GranularityLiteral) -> dict[str, Any] | None:
    """Configura botões de zoom rápido apropriados para cada granularidade."""
    if granularity == "diaria":
        return {
            "buttons": [
                {"count": 7, "label": "7d", "step": "day", "stepmode": "backward"},
                {"count": 30, "label": "30d", "step": "day", "stepmode": "backward"},
                {"count": 90, "label": "90d", "step": "day", "stepmode": "backward"},
                {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
                {"count": 1, "label": "1a", "step": "year", "stepmode": "backward"},
                {"step": "all", "label": "Tudo"},
            ]
        }
    if granularity == "quinzenal":
        return {
            "buttons": [
                {"count": 3, "label": "3m", "step": "month", "stepmode": "backward"},
                {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
                {"count": 1, "label": "1a", "step": "year", "stepmode": "backward"},
                {"step": "all", "label": "Tudo"},
            ]
        }
    return None


def apply_temporal_layout(
    fig: go.Figure,
    *,
    granularity: GranularityLiteral | None = None,
    n_points: int = 0,
    show_rangeslider: bool | None = None,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
) -> go.Figure:
    """Aplica layout padrão (ticks, rangeslider, margens) a uma figura temporal."""
    granularity = granularity or "mensal"
    marker = _marker_settings(n_points, granularity)
    fig.update_traces(
        mode=marker["mode"],
        marker={"size": marker["marker_size"]},
        line={"width": marker["line_width"]},
        selector={"type": "scatter"},
    )

    rangeslider_visible = (
        show_rangeslider
        if show_rangeslider is not None
        else (granularity == "diaria" and n_points > 30)
    )

    xaxis_config: dict[str, Any] = {
        "tickformat": _tick_format_for(granularity),
        "showgrid": True,
        "gridcolor": "rgba(128,128,128,0.15)",
        "rangeslider": {"visible": bool(rangeslider_visible), "thickness": 0.06},
    }
    range_selector = _range_selector_for(granularity)
    if range_selector is not None and rangeslider_visible:
        xaxis_config["rangeselector"] = range_selector

    if xaxis_title is not None:
        xaxis_config["title"] = xaxis_title

    yaxis_config: dict[str, Any] = {
        "showgrid": True,
        "gridcolor": "rgba(128,128,128,0.15)",
    }
    if yaxis_title is not None:
        yaxis_config["title"] = yaxis_title

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 40, "r": 20, "t": 78, "b": 30},
        title={"pad": {"t": 18, "b": 10}},
        hovermode="x unified",
        xaxis=xaxis_config,
        yaxis=yaxis_config,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    return fig


def build_temporal_line_figure(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    title: str,
    template: str,
    granularity: GranularityLiteral | None = None,
    labels: dict[str, str] | None = None,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
    show_rangeslider: bool | None = None,
) -> go.Figure:
    """Cria um gráfico de linha temporal adaptativo à granularidade."""
    if df is None or df.empty:
        fig = px.line(template=template, title=title)
        apply_temporal_layout(
            fig,
            granularity=granularity or "mensal",
            n_points=0,
            show_rangeslider=False,
            xaxis_title=xaxis_title,
            yaxis_title=yaxis_title,
        )
        return fig

    if granularity is None:
        granularity = infer_granularity(df[x])

    n_points = len(df.index)
    fig = px.line(
        df,
        x=x,
        y=y,
        title=title,
        template=template,
        labels=labels or {},
    )
    return apply_temporal_layout(
        fig,
        granularity=granularity,
        n_points=n_points,
        show_rangeslider=show_rangeslider,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
    )
