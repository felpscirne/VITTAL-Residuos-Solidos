import pandas as pd
import plotly.graph_objects as go

from app.services.temporal_charts import (
    apply_temporal_layout,
    build_temporal_line_figure,
    infer_granularity,
)


def test_infer_granularity_handles_empty_invalid_and_common_cadences():
    assert infer_granularity(pd.Series(dtype="datetime64[ns]")) == "mensal"
    assert infer_granularity(pd.Series(["nao e data"])) == "mensal"
    assert infer_granularity(pd.Series(pd.date_range("2025-01-01", periods=3, freq="D"))) == "diaria"
    assert infer_granularity(pd.Series(pd.date_range("2025-01-01", periods=3, freq="15D"))) == "quinzenal"
    assert infer_granularity(pd.Series(pd.date_range("2025-01-01", periods=3, freq="MS"))) == "mensal"
    assert infer_granularity(pd.Series(pd.date_range("2020-01-01", periods=3, freq="365D"))) == "anual"


def test_apply_temporal_layout_enables_daily_rangeslider_for_dense_series():
    fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4])])

    updated = apply_temporal_layout(fig, granularity="diaria", n_points=31)

    assert updated.layout.xaxis.rangeslider.visible is True
    assert updated.layout.xaxis.tickformat == "%d/%m"
    assert updated.data[0].mode == "lines+markers"


def test_build_temporal_line_figure_handles_empty_dataframe():
    fig = build_temporal_line_figure(
        pd.DataFrame(),
        x="data",
        y="valor",
        title="Serie",
        template="plotly_white",
    )

    assert fig.layout.title.text == "Serie"
    assert fig.layout.xaxis.rangeslider.visible is False
