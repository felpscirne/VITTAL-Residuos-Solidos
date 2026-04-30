import pandas as pd

from app.services.forecast_service import (
    _aggregate_weather_by_cadence,
    _compute_empirical_interval_margin,
    _generate_future_dates,
    _regularize_series,
    _safe_corr,
    _semi_month_start,
    _smooth_forecast_projection,
    build_rio_grande_holidays,
)


def test_regularize_monthly_series_fills_missing_months_by_interpolation():
    df = pd.DataFrame(
        {
            "ds": ["2025-01-01", "2025-03-01"],
            "y": [10, 30],
        }
    )

    regularized, metrics = _regularize_series(df, cadence="mensal")

    assert regularized["ds"].dt.strftime("%Y-%m").tolist() == ["2025-01", "2025-02", "2025-03"]
    assert regularized["y"].tolist() == [10.0, 20.0, 30.0]
    assert metrics["missing_months_filled"] == 1
    assert metrics["missing_months_original"] == ["2025-02"]


def test_regularize_daily_series_can_preserve_missing_values():
    df = pd.DataFrame(
        {
            "ds": ["2025-01-01", "2025-01-03"],
            "y": [10, 30],
        }
    )

    regularized, metrics = _regularize_series(df, cadence="diaria", fill_missing=False)

    assert regularized["was_missing"].tolist() == [False, True, False]
    assert pd.isna(regularized.loc[1, "y"])
    assert metrics["missing_months_filled"] == 0
    assert metrics["missing_months_original"] == ["2025-01-02"]


def test_generate_future_dates_respects_supported_cadences():
    assert _generate_future_dates(pd.Timestamp("2025-01-01"), 2, "diaria") == [
        pd.Timestamp("2025-01-02"),
        pd.Timestamp("2025-01-03"),
    ]
    assert _generate_future_dates(pd.Timestamp("2025-01-01"), 2, "quinzenal") == [
        pd.Timestamp("2025-01-16"),
        pd.Timestamp("2025-02-01"),
    ]
    assert _generate_future_dates(pd.Timestamp("2025-01-01"), 2, "mensal") == [
        pd.Timestamp("2025-02-01"),
        pd.Timestamp("2025-03-01"),
    ]


def test_semi_month_start_maps_dates_to_first_or_second_half():
    assert _semi_month_start(pd.Timestamp("2025-01-15")) == pd.Timestamp("2025-01-01")
    assert _semi_month_start(pd.Timestamp("2025-01-16")) == pd.Timestamp("2025-01-16")


def test_build_rio_grande_holidays_contains_local_and_movable_holidays():
    holidays = build_rio_grande_holidays(2025, 2025)

    assert set(holidays["holiday"]) == {
        "revolucao_farroupilha",
        "sao_pedro_rio_grande",
        "carnaval_segunda",
        "carnaval_terca",
        "sexta_santa",
        "corpus_christi",
    }
    assert pd.Timestamp("2025-04-18") in set(holidays["ds"])


def test_aggregate_weather_by_cadence_sums_rain_and_counts_rainy_days():
    weather = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02", "2025-01-16"],
            "temp_mean": [20.0, 22.0, 24.0],
            "precip_sum": [4.0, 6.0, 10.0],
        }
    )

    aggregated = _aggregate_weather_by_cadence(weather, "quinzenal")

    assert aggregated.loc[0, "ds"] == pd.Timestamp("2025-01-01")
    assert aggregated.loc[0, "temp_mean"] == 21.0
    assert aggregated.loc[0, "precip_sum"] == 10.0
    assert aggregated.loc[0, "rainy_days"] == 1
    assert aggregated.loc[1, "precip_sum_lag1"] == 10.0


def test_safe_corr_returns_none_for_insufficient_or_constant_data():
    assert _safe_corr(pd.Series([1, 2]), pd.Series([1, 2])) is None
    assert _safe_corr(pd.Series([1, 1, 1]), pd.Series([1, 2, 3])) is None
    assert _safe_corr(pd.Series([1, 2, 3]), pd.Series([1, 2, 3])) == 1.0


def test_compute_empirical_interval_margin_uses_error_quantile_and_history_cap():
    margin = _compute_empirical_interval_margin(
        actual=pd.Series([10, 20, 30]),
        predicted=pd.Series([8, 18, 20]),
        interval_width=0.8,
        history=pd.Series([10, 12, 14, 16]),
    )

    assert margin > 0
    assert margin <= 5.6


def test_smooth_forecast_projection_only_changes_future_rows():
    history = pd.DataFrame(
        {
            "ds": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "y": [100.0, 120.0],
        }
    )
    forecast = pd.DataFrame(
        {
            "ds": pd.to_datetime(["2025-02-01", "2025-03-01", "2025-04-01"]),
            "yhat": [120.0, 300.0, 20.0],
            "yhat_lower": [100.0, 250.0, 0.0],
            "yhat_upper": [140.0, 350.0, 60.0],
        }
    )

    smoothed = _smooth_forecast_projection(history, forecast, "default")

    assert smoothed.loc[0, "yhat"] == 120.0
    assert smoothed.loc[1, "yhat"] != 300.0
    assert smoothed.loc[1, "yhat_lower"] >= 0
