from __future__ import annotations

from functools import lru_cache
import math
from datetime import date, datetime, timedelta
import re
from typing import Any

import pandas as pd
import requests

try:
    from prophet import Prophet
    PROPHET_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover
    Prophet = None
    PROPHET_IMPORT_ERROR = str(exc)


RIO_GRANDE_PUBLIC_CONTEXT = {
    "city": "Rio Grande",
    "state": "RS",
    "country": "Brasil",
    "latitude": -32.035,
    "longitude": -52.09861,
    "timezone": "America/Sao_Paulo",
    "sources": [
        {
            "name": "Open-Meteo Historical Weather API",
            "url": "https://open-meteo.com/en/docs/historical-weather-api",
            "kind": "clima_historico",
            "description": "Temperatura média diária e precipitação diária para Rio Grande - RS.",
        },
        {
            "name": "Feriados.com.br - Rio Grande/RS",
            "url": "https://feriados.com.br/RS/Rio%20Grande",
            "kind": "feriados_municipais_estaduais_federais",
            "description": "Calendário público com feriados municipais, estaduais e federais de Rio Grande - RS.",
        },
        {
            "name": "Wikidata - Rio Grande (Q869571)",
            "url": "https://www.wikidata.org/wiki/Q869571",
            "kind": "localizacao",
            "description": "Coordenadas públicas do município de Rio Grande - RS.",
        },
    ],
}

FEATURE_LABELS = {
    "serie_historica_interna": "Histórico operacional",
    "feriados_publicos_rio_grande_rs": "Feriados públicos de Rio Grande e do Brasil",
    "temp_mean": "Temperatura média",
    "precip_sum": "Precipitação acumulada",
}

SMOOTHING_LABELS = {
    "rolling_median_ewma": "Média Móvel Exponencialmente Ponderada",
    "none": "Sem estabilização adicional",
}

MODEL_CONFIG_LABELS = {
    "padrao": "Padrão",
    "conservador": "Mais conservadora",
    "equilibrado": "Equilibrada",
    "sensivel": "Mais sensível a mudanças",
}


def _empty_result(status: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "history": pd.DataFrame(),
        "forecast": pd.DataFrame(),
        "metrics": {
            "missing_months_filled": 0,
            "missing_months_original": [],
            "cadence_label": "quinzenas",
            "retrospective_periods": 0,
        },
        "public_data": {
            "location": RIO_GRANDE_PUBLIC_CONTEXT,
            "sources": RIO_GRANDE_PUBLIC_CONTEXT["sources"],
            "weather_status": "not_used",
            "holiday_status": "not_used",
            "features_used": [],
            "insights": [],
        },
    }


def _easter_date(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


@lru_cache(maxsize=24)
def fetch_feriados_combr_holidays(year: int) -> tuple[pd.DataFrame, str]:
    api_urls = [
        f"https://www.feriados.com.br/feriados-rio_grande-rs.php?ano={year}",
        f"https://www.feriados.com.br/feriados-rio_grande-rs.php",
    ]
    pattern = re.compile(r"(\d{2}/\d{2}/\d{4})\s*-\s*([^<\\n\\r]+)")

    try:
        html_content = ""
        for api_url in api_urls:
            response = requests.get(
                api_url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 IFEsCS Forecast Bot"},
            )
            response.raise_for_status()
            html_content = response.text
            if str(year) in html_content:
                break

        rows = []
        for date_str, holiday_name in pattern.findall(html_content):
            holiday_date = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
            if pd.isna(holiday_date) or holiday_date.year != year:
                continue
            normalized_name = (
                str(holiday_name or "feriado")
                .strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
                .replace(".", "")
                .replace("ç", "c")
                .replace("ã", "a")
                .replace("á", "a")
                .replace("é", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ú", "u")
            )
            rows.append(
                {
                    "holiday": f"feriados_com_br_{normalized_name}",
                    "ds": holiday_date.normalize(),
                    "lower_window": 0,
                    "upper_window": 0,
                }
            )

        holidays_df = pd.DataFrame(rows).drop_duplicates(subset=["holiday", "ds"])
        if holidays_df.empty:
            return pd.DataFrame(), "empty"
        return holidays_df, "ok"
    except Exception:  # pragma: no cover
        return pd.DataFrame(), "unavailable"


def build_rio_grande_holidays(start_year: int, end_year: int) -> pd.DataFrame:
    rows = []
    for year in range(start_year, end_year + 1):
        easter = _easter_date(year)
        fixed = {
            "revolucao_farroupilha": date(year, 9, 20),
            "sao_pedro_rio_grande": date(year, 6, 29),
            "carnaval_segunda": easter - timedelta(days=48),
            "carnaval_terca": easter - timedelta(days=47),
            "sexta_santa": easter - timedelta(days=2),
            "corpus_christi": easter + timedelta(days=60),
        }
        for holiday_name, holiday_date in fixed.items():
            rows.append(
                {
                    "holiday": holiday_name,
                    "ds": pd.Timestamp(holiday_date),
                    "lower_window": 0,
                    "upper_window": 0,
                }
            )
    return pd.DataFrame(rows)


def _build_holiday_dataframe(start_year: int, end_year: int) -> tuple[pd.DataFrame, str]:
    public_rows = []
    statuses = []
    for year in range(start_year, end_year + 1):
        holidays_df, status = fetch_feriados_combr_holidays(year)
        statuses.append(status)
        if not holidays_df.empty:
            public_rows.append(holidays_df)

    local_holidays = build_rio_grande_holidays(start_year, end_year)
    combined_frames = [local_holidays]
    if public_rows:
        combined_frames.extend(public_rows)

    combined = pd.concat(combined_frames, ignore_index=True).drop_duplicates(subset=["holiday", "ds"])
    overall_status = "ok" if any(status == "ok" for status in statuses) else "partial"
    return combined, overall_status


@lru_cache(maxsize=24)
def _fetch_rio_grande_weather_monthly_cached(start_date_str: str, end_date_str: str) -> tuple[pd.DataFrame, str]:
    start_date = pd.Timestamp(start_date_str)
    end_date = pd.Timestamp(end_date_str)
    api_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": RIO_GRANDE_PUBLIC_CONTEXT["latitude"],
        "longitude": RIO_GRANDE_PUBLIC_CONTEXT["longitude"],
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": RIO_GRANDE_PUBLIC_CONTEXT["timezone"],
    }
    try:
        response = requests.get(api_url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        daily = payload.get("daily", {})
        weather_df = pd.DataFrame(
            {
                "date": pd.to_datetime(daily.get("time", [])),
                "temp_mean": daily.get("temperature_2m_mean", []),
                "precip_sum": daily.get("precipitation_sum", []),
            }
        )
        if weather_df.empty:
            return pd.DataFrame(), "empty"
        weather_df["month"] = weather_df["date"].dt.to_period("M").dt.to_timestamp()
        monthly = weather_df.groupby("month", as_index=False).agg(
            temp_mean=("temp_mean", "mean"),
            precip_sum=("precip_sum", "sum"),
        )
        monthly = monthly.rename(columns={"month": "ds"})
        return monthly, "ok"
    except Exception:  # pragma: no cover
        return pd.DataFrame(), "unavailable"


def fetch_rio_grande_weather_monthly(start_date: pd.Timestamp, end_date: pd.Timestamp) -> tuple[pd.DataFrame, str]:
    return _fetch_rio_grande_weather_monthly_cached(
        pd.Timestamp(start_date).strftime("%Y-%m-%d"),
        pd.Timestamp(end_date).strftime("%Y-%m-%d"),
    )


def _regularize_monthly_series(monthly_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    series_df = monthly_df.copy()
    series_df["ds"] = pd.to_datetime(series_df["ds"], errors="coerce")
    series_df["y"] = pd.to_numeric(series_df["y"], errors="coerce")
    series_df = (
        series_df.dropna(subset=["ds"])
        .groupby("ds", as_index=False)
        .agg(y=("y", "sum"))
        .sort_values("ds")
    )
    if series_df.empty:
        return series_df, {"missing_months_filled": 0, "missing_months_original": []}

    full_range = pd.date_range(series_df["ds"].min(), series_df["ds"].max(), freq="MS")
    regularized = (
        series_df.set_index("ds")
        .reindex(full_range)
        .rename_axis("ds")
        .reset_index()
    )
    missing_mask = regularized["y"].isna()
    missing_months = regularized.loc[missing_mask, "ds"].dt.strftime("%Y-%m").tolist()

    regularized["y"] = pd.to_numeric(regularized["y"], errors="coerce")
    regularized["y"] = regularized["y"].interpolate(method="linear", limit_direction="both")
    regularized["y"] = regularized["y"].fillna(0)
    regularized["y"] = regularized["y"].clip(lower=0)
    regularized["was_missing"] = missing_mask

    return regularized, {
        "missing_months_filled": int(len(missing_months)),
        "missing_months_original": missing_months,
    }


def _semi_month_start(ts: pd.Timestamp) -> pd.Timestamp:
    month_start = ts.to_period("M").to_timestamp()
    return month_start if ts.day <= 15 else month_start + pd.Timedelta(days=15)


def _generate_cadence_range(start: pd.Timestamp, end: pd.Timestamp, cadence: str) -> pd.DatetimeIndex:
    if cadence != "quinzenal":
        return pd.date_range(start, end, freq="MS")

    current = _semi_month_start(pd.Timestamp(start))
    limit = _semi_month_start(pd.Timestamp(end))
    values = []
    while current <= limit:
        values.append(current)
        if current.day == 1:
            current = current + pd.Timedelta(days=15)
        else:
            next_month = (current + pd.offsets.MonthBegin(1)).normalize()
            current = next_month
    return pd.DatetimeIndex(values)


def _generate_future_dates(last_ds: pd.Timestamp, periods: int, cadence: str) -> list[pd.Timestamp]:
    future_dates = []
    current = pd.Timestamp(last_ds)
    for _ in range(periods):
        if cadence == "quinzenal":
            if current.day == 1:
                current = current + pd.Timedelta(days=15)
            else:
                current = (current + pd.offsets.MonthBegin(1)).normalize()
        else:
            current = current + pd.offsets.MonthBegin(1)
        future_dates.append(pd.Timestamp(current))
    return future_dates


def _regularize_series(monthly_df: pd.DataFrame, cadence: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    if cadence != "quinzenal":
        return _regularize_monthly_series(monthly_df)

    series_df = monthly_df.copy()
    series_df["ds"] = pd.to_datetime(series_df["ds"], errors="coerce")
    series_df["y"] = pd.to_numeric(series_df["y"], errors="coerce")
    series_df = (
        series_df.dropna(subset=["ds"])
        .assign(ds=lambda df: df["ds"].apply(_semi_month_start))
        .groupby("ds", as_index=False)
        .agg(y=("y", "sum"))
        .sort_values("ds")
    )
    if series_df.empty:
        return series_df, {"missing_months_filled": 0, "missing_months_original": []}

    full_range = _generate_cadence_range(series_df["ds"].min(), series_df["ds"].max(), cadence)
    regularized = series_df.set_index("ds").reindex(full_range).rename_axis("ds").reset_index()
    missing_mask = regularized["y"].isna()
    missing_labels = regularized.loc[missing_mask, "ds"].dt.strftime("%Y-%m-%d").tolist()
    regularized["y"] = pd.to_numeric(regularized["y"], errors="coerce")
    regularized["y"] = regularized["y"].interpolate(method="linear", limit_direction="both")
    regularized["y"] = regularized["y"].fillna(0).clip(lower=0)
    regularized["was_missing"] = missing_mask
    return regularized, {
        "missing_months_filled": int(len(missing_labels)),
        "missing_months_original": missing_labels,
    }


def _stabilize_monthly_signal(series_df: pd.DataFrame) -> pd.DataFrame:
    stabilized = series_df.copy()
    stabilized["y"] = pd.to_numeric(stabilized["y"], errors="coerce").fillna(0)

    if len(stabilized) >= 6:
        rolling_median = stabilized["y"].rolling(window=3, center=True, min_periods=1).median()
        ewma = stabilized["y"].ewm(span=3, adjust=False).mean()
        stabilized["y_model"] = ((rolling_median * 0.5) + (ewma * 0.5)).clip(lower=0)
    else:
        stabilized["y_model"] = stabilized["y"]

    return stabilized


def _build_monthly_climatology(weather_df: pd.DataFrame) -> pd.DataFrame:
    if weather_df.empty:
        return pd.DataFrame(columns=["month_num", "temp_mean", "precip_sum"])
    climatology = weather_df.copy()
    climatology["month_num"] = climatology["ds"].dt.month
    return climatology.groupby("month_num", as_index=False).agg(
        temp_mean=("temp_mean", "mean"),
        precip_sum=("precip_sum", "mean"),
    )


def _safe_corr(series_a: pd.Series, series_b: pd.Series) -> float | None:
    clean = pd.DataFrame(
        {
            "a": pd.to_numeric(series_a, errors="coerce"),
            "b": pd.to_numeric(series_b, errors="coerce"),
        }
    ).dropna()
    if len(clean) < 3 or clean["a"].nunique() <= 1 or clean["b"].nunique() <= 1:
        return None
    corr = clean["a"].corr(clean["b"])
    if pd.isna(corr):
        return None
    return float(corr)


def _describe_correlation(label: str, corr: float | None) -> str | None:
    if corr is None:
        return None
    abs_corr = abs(corr)
    if abs_corr < 0.15:
        strength = "relação pouco evidente"
    elif abs_corr < 0.35:
        strength = "relação discreta"
    elif abs_corr < 0.60:
        strength = "relação moderada"
    else:
        strength = "relação forte"
    direction = "positiva" if corr >= 0 else "negativa"
    return f"{label}: {strength} ({direction}, correlação aproximada de {corr:.2f})"


def _build_external_factor_insights(model_df: pd.DataFrame, holiday_df: pd.DataFrame, weather_features: list[str]) -> list[str]:
    if model_df is None or model_df.empty or "y" not in model_df.columns:
        return []

    enriched = model_df.copy()
    enriched["ds"] = pd.to_datetime(enriched["ds"], errors="coerce")
    enriched["y"] = pd.to_numeric(enriched["y"], errors="coerce")
    enriched = enriched.dropna(subset=["ds", "y"])
    if enriched.empty:
        return []

    insights = []

    if "temp_mean" in weather_features and "temp_mean" in enriched.columns:
        temp_text = _describe_correlation("Temperatura média", _safe_corr(enriched["y"], enriched["temp_mean"]))
        if temp_text:
            insights.append(temp_text)

    if "precip_sum" in weather_features and "precip_sum" in enriched.columns:
        precip_text = _describe_correlation("Precipitação acumulada", _safe_corr(enriched["y"], enriched["precip_sum"]))
        if precip_text:
            insights.append(precip_text)

    if holiday_df is not None and not holiday_df.empty:
        holiday_periods = set(pd.to_datetime(holiday_df["ds"], errors="coerce").dropna().dt.to_period("M").astype(str).tolist())
        if holiday_periods:
            enriched["period_key"] = enriched["ds"].dt.to_period("M").astype(str)
            enriched["has_holiday"] = enriched["period_key"].isin(holiday_periods)
            holiday_slice = enriched[enriched["has_holiday"]]
            regular_slice = enriched[~enriched["has_holiday"]]
            if not holiday_slice.empty and not regular_slice.empty:
                holiday_mean = float(holiday_slice["y"].mean())
                regular_mean = float(regular_slice["y"].mean())
                diff_pct = ((holiday_mean - regular_mean) / regular_mean * 100) if regular_mean else 0.0
                if abs(diff_pct) < 5:
                    holiday_desc = "sem diferença relevante frente aos demais períodos"
                elif diff_pct > 0:
                    holiday_desc = f"volumes historicamente acima da média em cerca de {abs(diff_pct):.1f}%"
                else:
                    holiday_desc = f"volumes historicamente abaixo da média em cerca de {abs(diff_pct):.1f}%"
                insights.append(f"Feriados públicos: {holiday_desc}")

    return insights


def _attach_weather_regressors(series_df: pd.DataFrame, periods: int) -> tuple[pd.DataFrame, pd.DataFrame, str, list[str]]:
    weather_df, weather_status = fetch_rio_grande_weather_monthly(series_df["ds"].min(), series_df["ds"].max())
    if weather_df.empty:
        return series_df, pd.DataFrame(), weather_status, []

    model_df = series_df.copy()
    model_df["month_key"] = model_df["ds"].dt.to_period("M").dt.to_timestamp()
    weather_df = weather_df.copy()
    weather_df["month_key"] = pd.to_datetime(weather_df["ds"]).dt.to_period("M").dt.to_timestamp()
    model_df = model_df.merge(weather_df[["month_key", "temp_mean", "precip_sum"]], on="month_key", how="left")
    climatology = _build_monthly_climatology(weather_df)
    future_dates = _generate_future_dates(series_df["ds"].max(), periods, "quinzenal")
    future_regressors = pd.DataFrame({"ds": future_dates})
    future_regressors["month_num"] = future_regressors["ds"].dt.month
    future_regressors = future_regressors.merge(climatology, on="month_num", how="left").drop(columns=["month_num"])
    return model_df, future_regressors, weather_status, ["temp_mean", "precip_sum"]


def _default_model_config(observations: int, use_weather: bool) -> dict[str, Any]:
    return {
        "config_name": "padrao",
        "changepoint_prior_scale": 0.03,
        "seasonality_prior_scale": 5.0,
        "holidays_prior_scale": 3.0,
        "yearly_seasonality": observations >= 18,
        "use_weather": use_weather,
    }


def _candidate_model_configs(observations: int, use_weather: bool) -> list[dict[str, Any]]:
    base = _default_model_config(observations, use_weather)
    candidates = [
        base,
        {
            **base,
            "config_name": "conservador",
            "changepoint_prior_scale": 0.01,
            "seasonality_prior_scale": 3.0,
            "holidays_prior_scale": 2.0,
        },
        {
            **base,
            "config_name": "equilibrado",
            "changepoint_prior_scale": 0.05,
            "seasonality_prior_scale": 7.0,
            "holidays_prior_scale": 4.0,
        },
        {
            **base,
            "config_name": "sensivel",
            "changepoint_prior_scale": 0.08,
            "seasonality_prior_scale": 8.0,
            "holidays_prior_scale": 5.0,
        },
    ]
    if observations < 12:
        for candidate in candidates:
            candidate["yearly_seasonality"] = False
    return candidates


def _build_prophet_model(
    interval_width: float,
    holiday_df: pd.DataFrame,
    use_weather: bool,
    observations: int,
    model_config: dict[str, Any] | None = None,
) -> Prophet:
    config = model_config or _default_model_config(observations, use_weather)
    yearly_seasonality = bool(config.get("yearly_seasonality", observations >= 18))
    effective_use_weather = bool(config.get("use_weather", use_weather))
    n_changepoints = min(max(observations - 2, 0), 6)
    model = Prophet(
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="additive",
        changepoint_prior_scale=float(config.get("changepoint_prior_scale", 0.03)),
        seasonality_prior_scale=float(config.get("seasonality_prior_scale", 5.0)),
        holidays_prior_scale=float(config.get("holidays_prior_scale", 3.0)),
        n_changepoints=n_changepoints,
        interval_width=interval_width,
        holidays=holiday_df,
        stan_backend="CMDSTANPY",
    )
    if effective_use_weather:
        model.add_regressor("temp_mean", standardize=True)
        model.add_regressor("precip_sum", standardize=True)
    return model


def _score_validation_result(validation_metrics: dict[str, float]) -> float:
    mae = float(validation_metrics.get("retrospective_mae", 0.0))
    rmse = float(validation_metrics.get("retrospective_rmse", 0.0))
    coverage = float(validation_metrics.get("retrospective_interval_coverage", 0.0))
    periods = int(validation_metrics.get("retrospective_periods", 0))
    if periods <= 0:
        return float("inf")
    coverage_penalty = abs(coverage - 0.8) * max(mae, 1.0)
    return mae + (0.35 * rmse) + coverage_penalty


def _compute_empirical_interval_margin(
    actual: pd.Series,
    predicted: pd.Series,
    interval_width: float,
) -> float:
    comparison = pd.DataFrame(
        {
            "actual": pd.to_numeric(actual, errors="coerce"),
            "predicted": pd.to_numeric(predicted, errors="coerce"),
        }
    ).dropna()
    if comparison.empty:
        return 0.0

    absolute_error = (comparison["actual"] - comparison["predicted"]).abs()
    quantile = min(max(float(interval_width), 0.5), 0.99)
    margin = float(absolute_error.quantile(quantile))
    if not math.isfinite(margin):
        return 0.0
    return max(margin, float(absolute_error.median()))


def _apply_empirical_interval_calibration(
    forecast_df: pd.DataFrame,
    calibration_margin: float,
) -> pd.DataFrame:
    calibrated = forecast_df.copy()
    raw_half_width = ((calibrated["yhat_upper"] - calibrated["yhat_lower"]) / 2).fillna(0)
    effective_half_width = raw_half_width.clip(lower=float(max(calibration_margin, 0.0)))
    calibrated["yhat_lower"] = (calibrated["yhat"] - effective_half_width).clip(lower=0)
    calibrated["yhat_upper"] = calibrated["yhat"] + effective_half_width
    return calibrated


def _run_retrospective_validation(
    fit_df: pd.DataFrame,
    holiday_df: pd.DataFrame,
    interval_width: float,
    use_weather: bool,
    periods: int,
    cadence: str,
    model_config: dict[str, Any] | None = None,
) -> dict[str, float]:
    if len(fit_df) < 8:
        return {
            "retrospective_mae": 0.0,
            "retrospective_rmse": 0.0,
            "retrospective_periods": 0,
            "retrospective_interval_coverage": 0.0,
        }

    holdout_periods = min(max(periods, 2), max(2, len(fit_df) // 4))
    train_df = fit_df.iloc[:-holdout_periods].copy()
    validation_df = fit_df.iloc[-holdout_periods:].copy()
    if len(train_df) < 4 or validation_df.empty:
        return {
            "retrospective_mae": 0.0,
            "retrospective_rmse": 0.0,
            "retrospective_periods": 0,
            "retrospective_interval_coverage": 0.0,
        }

    model = _build_prophet_model(
        interval_width=interval_width,
        holiday_df=holiday_df,
        use_weather=use_weather,
        observations=len(train_df),
        model_config=model_config,
    )
    model.fit(train_df)

    future_dates = pd.DataFrame({"ds": validation_df["ds"].tolist()})
    if use_weather:
        future_dates = future_dates.merge(validation_df[["ds", "temp_mean", "precip_sum"]], on="ds", how="left")
        for regressor in ["temp_mean", "precip_sum"]:
            future_dates[regressor] = pd.to_numeric(future_dates[regressor], errors="coerce")
            future_dates[regressor] = future_dates[regressor].interpolate(method="linear", limit_direction="both")
            future_dates[regressor] = future_dates[regressor].fillna(future_dates[regressor].mean())

    predicted = model.predict(future_dates)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    for column in ["yhat", "yhat_lower", "yhat_upper"]:
        predicted[column] = pd.to_numeric(predicted[column], errors="coerce")
    predicted["yhat_lower"] = predicted["yhat_lower"].clip(lower=0)
    predicted["yhat_upper"] = predicted[["yhat_upper", "yhat"]].max(axis=1)

    comparison = validation_df[["ds", "y"]].merge(predicted, on="ds", how="left")
    comparison = comparison.dropna(subset=["yhat", "yhat_lower", "yhat_upper"])
    if comparison.empty:
        return {
            "retrospective_mae": 0.0,
            "retrospective_rmse": 0.0,
            "retrospective_periods": 0,
            "retrospective_interval_coverage": 0.0,
        }

    mae = float((comparison["y"] - comparison["yhat"]).abs().mean())
    rmse = float(math.sqrt(((comparison["y"] - comparison["yhat"]) ** 2).mean()))
    raw_coverage = float(
        (
            (comparison["y"] >= comparison["yhat_lower"]) &
            (comparison["y"] <= comparison["yhat_upper"])
        ).mean()
    )
    calibration_margin = _compute_empirical_interval_margin(
        actual=comparison["y"],
        predicted=comparison["yhat"],
        interval_width=interval_width,
    )
    adjusted_lower = (comparison["yhat"] - calibration_margin).clip(lower=0)
    adjusted_upper = comparison["yhat"] + calibration_margin
    coverage = float(
        (
            (comparison["y"] >= adjusted_lower) &
            (comparison["y"] <= adjusted_upper)
        ).mean()
    )
    covered_periods = int(
        (
            (comparison["y"] >= adjusted_lower) &
            (comparison["y"] <= adjusted_upper)
        ).sum()
    )
    return {
        "retrospective_mae": mae,
        "retrospective_rmse": rmse,
        "retrospective_periods": int(len(comparison)),
        "retrospective_interval_coverage": coverage,
        "retrospective_raw_interval_coverage": raw_coverage,
        "retrospective_interval_margin": float(calibration_margin),
        "retrospective_covered_periods": covered_periods,
    }


def _select_best_model_config(
    fit_df: pd.DataFrame,
    holiday_df: pd.DataFrame,
    interval_width: float,
    use_weather: bool,
    periods: int,
    cadence: str,
) -> tuple[dict[str, Any], dict[str, float], list[dict[str, Any]]]:
    candidates = _candidate_model_configs(len(fit_df), use_weather)
    evaluations = []
    best_config = candidates[0]
    best_metrics = {
        "retrospective_mae": 0.0,
        "retrospective_rmse": 0.0,
        "retrospective_periods": 0,
        "retrospective_interval_coverage": 0.0,
    }
    best_score = float("inf")

    for candidate in candidates:
        try:
            validation_metrics = _run_retrospective_validation(
                fit_df=fit_df,
                holiday_df=holiday_df,
                interval_width=interval_width,
                use_weather=bool(candidate.get("use_weather", use_weather)),
                periods=periods,
                cadence=cadence,
                model_config=candidate,
            )
            score = _score_validation_result(validation_metrics)
            evaluations.append(
                {
                    "config_name": candidate.get("config_name", "configuracao"),
                    "score": score,
                    "mae": float(validation_metrics.get("retrospective_mae", 0.0)),
                    "rmse": float(validation_metrics.get("retrospective_rmse", 0.0)),
                    "coverage": float(validation_metrics.get("retrospective_interval_coverage", 0.0)),
                }
            )
            if score < best_score:
                best_score = score
                best_config = candidate
                best_metrics = validation_metrics
        except Exception:
            continue

    return best_config, best_metrics, evaluations


def build_monthly_forecast(
    monthly_df: pd.DataFrame,
    periods: int = 4,
    interval_width: float = 0.8,
    cadence: str = "quinzenal",
) -> dict[str, Any]:
    if monthly_df is None or monthly_df.empty:
        return _empty_result("no_data", "Não há dados suficientes para gerar previsão.")

    required_columns = {"ds", "y"}
    if not required_columns.issubset(monthly_df.columns):
        return _empty_result("invalid_data", "A série temporal precisa conter as colunas ds e y.")

    series_df, gap_info = _regularize_series(monthly_df, cadence)
    series_df = series_df.dropna(subset=["ds", "y"]).sort_values("ds")
    series_df = _stabilize_monthly_signal(series_df)
    cadence_label = "quinzenas" if cadence == "quinzenal" else "meses"

    if len(series_df) < 3:
        result = _empty_result("insufficient_data", "São necessários pelo menos 3 pontos mensais para calcular a previsão.")
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result

    if Prophet is None:
        result = _empty_result(
            "unavailable",
            f"O módulo de previsão não está disponível neste ambiente no momento. {PROPHET_IMPORT_ERROR or ''}".strip(),
        )
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result

    holiday_df, holiday_status = _build_holiday_dataframe(series_df["ds"].dt.year.min(), (series_df["ds"].dt.year.max() + 2))
    model_df, future_regressors, weather_status, weather_features = _attach_weather_regressors(series_df, periods)
    use_weather = all(feature in model_df.columns and model_df[feature].notna().any() for feature in weather_features)

    try:
        fit_df = model_df.copy()
        fit_df["y"] = fit_df["y_model"] if "y_model" in fit_df.columns else fit_df["y"]
        if use_weather:
            for regressor in weather_features:
                fit_df[regressor] = pd.to_numeric(fit_df[regressor], errors="coerce")
                fit_df[regressor] = fit_df[regressor].interpolate(method="linear", limit_direction="both")
                fit_df[regressor] = fit_df[regressor].fillna(fit_df[regressor].mean())
        fit_df = fit_df.dropna(subset=["ds", "y"]).copy()

        selected_config, retrospective_metrics, calibration_runs = _select_best_model_config(
            fit_df=fit_df,
            holiday_df=holiday_df,
            interval_width=interval_width,
            use_weather=use_weather,
            periods=periods,
            cadence=cadence,
        )

        model = _build_prophet_model(
            interval_width=interval_width,
            holiday_df=holiday_df,
            use_weather=bool(selected_config.get("use_weather", use_weather)),
            observations=len(series_df),
            model_config=selected_config,
        )
    except Exception as exc:
        result = _empty_result(
            "unavailable",
            f"O ambiente atual não conseguiu inicializar o Prophet para esta previsão. {exc}",
        )
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result

    try:
        model.fit(fit_df)
    except Exception as exc:
        result = _empty_result(
            "unavailable",
            f"O ambiente atual não conseguiu ajustar o modelo Prophet com segurança. {exc}",
        )
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result

    future = pd.DataFrame({"ds": fit_df["ds"].tolist() + _generate_future_dates(fit_df["ds"].max(), periods, cadence)})
    effective_use_weather = bool(selected_config.get("use_weather", use_weather))
    if effective_use_weather:
        future = future.merge(fit_df[["ds", *weather_features]], on="ds", how="left")
        if not future_regressors.empty:
            for regressor in weather_features:
                future.loc[future["ds"].isin(future_regressors["ds"]), regressor] = future_regressors.set_index("ds")[regressor]
        for regressor in weather_features:
            future[regressor] = pd.to_numeric(future[regressor], errors="coerce")
            future[regressor] = future[regressor].interpolate(method="linear", limit_direction="both")
            future[regressor] = future[regressor].fillna(future[regressor].mean())

    try:
        forecast = model.predict(future)
    except Exception as exc:
        result = _empty_result(
            "unavailable",
            f"O ambiente atual não conseguiu gerar a previsão com Prophet. {exc}",
        )
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result
    forecast_view = forecast[["ds", "yhat", "yhat_lower", "yhat_upper", "trend"]].copy()
    for column in ["yhat", "yhat_lower", "yhat_upper", "trend"]:
        forecast_view[column] = pd.to_numeric(forecast_view[column], errors="coerce")
    forecast_view["yhat"] = forecast_view["yhat"].clip(lower=0)
    forecast_view["yhat_lower"] = forecast_view["yhat_lower"].clip(lower=0)
    forecast_view["yhat_upper"] = forecast_view[["yhat_upper", "yhat"]].max(axis=1)
    history = series_df.merge(forecast_view[["ds", "yhat"]], on="ds", how="left")

    mae = float((history["y"] - history["yhat"]).abs().mean())
    rmse = float(math.sqrt(((history["y"] - history["yhat"]) ** 2).mean()))
    last_actual = float(history["y"].iloc[-1])
    last_forecast = float(forecast_view["yhat"].iloc[-1])
    trend_pct = float(((last_forecast - last_actual) / last_actual) * 100) if last_actual else 0.0

    return {
        "status": "ok",
        "message": "Previsão gerada com Prophet.",
        "history": history,
        "forecast": _apply_empirical_interval_calibration(
            forecast_view,
            retrospective_metrics.get("retrospective_interval_margin", 0.0),
        ),
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "last_actual": last_actual,
            "last_forecast": last_forecast,
            "trend_pct": trend_pct,
            "observations": int(len(history)),
            "forecast_periods": int(periods),
            "confidence": float(interval_width),
            "signal_smoothing": "rolling_median_ewma" if len(series_df) >= 6 else "none",
            "auto_recalibration_enabled": True,
            "selected_model_config": selected_config.get("config_name", "padrao"),
            "selected_changepoint_prior_scale": float(selected_config.get("changepoint_prior_scale", 0.03)),
            "selected_seasonality_prior_scale": float(selected_config.get("seasonality_prior_scale", 5.0)),
            "selected_holidays_prior_scale": float(selected_config.get("holidays_prior_scale", 3.0)),
            "selected_yearly_seasonality": bool(selected_config.get("yearly_seasonality", len(series_df) >= 18)),
            "calibration_runs": calibration_runs,
            "cadence_label": cadence_label,
            **retrospective_metrics,
            **gap_info,
        },
        "public_data": {
            "location": RIO_GRANDE_PUBLIC_CONTEXT,
            "sources": RIO_GRANDE_PUBLIC_CONTEXT["sources"],
            "weather_status": weather_status,
            "holiday_status": holiday_status,
            "features_used": ["serie_historica_interna", "feriados_publicos_rio_grande_rs", *(weather_features if effective_use_weather else [])],
            "insights": _build_external_factor_insights(model_df, holiday_df, weather_features if effective_use_weather else []),
        },
    }


def build_forecast_summary_markdown(result: dict[str, Any]) -> str:
    status = result.get("status")
    if status != "ok":
        return "### Previsão temporal\n" f"- Status: {status}\n" f"- Observação: {result.get('message', 'Não foi possível gerar a previsão.')}"

    metrics = result["metrics"]
    direction = "crescimento" if metrics["trend_pct"] >= 0 else "queda"
    intervalo_nominal = int(metrics["confidence"] * 100)
    cadence_label = metrics.get("cadence_label", "períodos")
    cobertura_empirica = metrics.get("retrospective_interval_coverage", 0.0) * 100
    cobertura_original = metrics.get("retrospective_raw_interval_coverage", 0.0) * 100
    smoothing_label = SMOOTHING_LABELS.get(metrics.get("signal_smoothing", "none"), metrics.get("signal_smoothing", "none"))
    recalibration_status = "ativa" if metrics.get("auto_recalibration_enabled") else "inativa"
    selected_model_label = MODEL_CONFIG_LABELS.get(
        metrics.get("selected_model_config", "padrao"),
        metrics.get("selected_model_config", "padrao"),
    )
    retrospective_periods = metrics.get("retrospective_periods", 0)
    covered_periods = metrics.get("retrospective_covered_periods", 0)
    calibration_margin = metrics.get("retrospective_interval_margin", 0.0)
    return (
        "### Resumo preditivo\n"
        f"- Série histórica utilizada: **{metrics['observations']} observações**.\n"
        f"- Horizonte projetado: **{metrics['forecast_periods']} {cadence_label}**.\n"
        f"- Períodos ausentes tratados antes do ajuste: **{metrics.get('missing_months_filled', 0)}**.\n"
        f"- Estabilização usada no treino: **{smoothing_label}**.\n"
        f"- Autoajuste histórico: **{recalibration_status}**.\n"
        f"- Configuração escolhida com base no histórico recente: **{selected_model_label}**.\n"
        f"- Erro médio absoluto da série agregada: **{metrics['mae']:.2f} kg por quinzena**.\n"
        f"- Erro quadrático médio da série agregada: **{metrics['rmse']:.2f} kg por quinzena**.\n"
        f"- Validação retrospectiva: **{retrospective_periods} períodos** comparados com dados já conhecidos.\n"
        f"- Erro médio na validação retrospectiva: **{metrics.get('retrospective_mae', 0.0):.2f} kg por quinzena**.\n"
        f"- Intervalo preditivo nominal exibido: **{intervalo_nominal}%**.\n"
        f"- Cobertura do intervalo original na validação: **{cobertura_original:.2f}%**.\n"
        f"- Cobertura empírica após recalibração: **{cobertura_empirica:.2f}%** ({covered_periods} de {retrospective_periods} períodos ficaram dentro do intervalo).\n"
        f"- Margem adicional aplicada ao intervalo com base no erro histórico: **±{calibration_margin:.2f} kg**.\n"
        f"- Último volume observado: **{metrics['last_actual']:.2f} kg**.\n"
        f"- Volume previsto no fim do horizonte: **{metrics['last_forecast']:.2f} kg**.\n"
        f"- Tendência estimada para o horizonte projetado: **{direction} de {abs(metrics['trend_pct']):.2f}%**.\n"
        "- Como interpretar: o intervalo exibido é ajustado com base no erro recente da própria previsão para representar melhor a variação observada no histórico."
    )


def build_public_data_markdown(result: dict[str, Any]) -> str:
    public_data = result.get("public_data", {})
    location = public_data.get("location", RIO_GRANDE_PUBLIC_CONTEXT)
    weather_status = public_data.get("weather_status", "desconhecido")
    holiday_status = public_data.get("holiday_status", "desconhecido")
    features_used = public_data.get("features_used", [])
    sources = public_data.get("sources", [])
    insights = public_data.get("insights", [])
    feature_labels = [FEATURE_LABELS.get(feature, feature) for feature in features_used]

    lines = [
        "### Fatores externos considerados",
        f"- Localização de referência: **{location['city']} - {location['state']}**, coordenadas aproximadas **{location['latitude']}, {location['longitude']}**.",
        f"- Situação da base pública de clima: **{weather_status}**.",
        f"- Situação da base pública de feriados: **{holiday_status}**.",
        f"- Informações externas usadas na previsão: **{', '.join(feature_labels) if feature_labels else 'nenhuma'}**.",
        f"- Períodos ausentes tratados na série: **{result.get('metrics', {}).get('missing_months_filled', 0)}**.",
        "- Classificação do tipo de resíduo: derivada internamente a partir do campo `produto`, com categorias operacionais como domiciliar, hospitalar e reciclável.",
    ]
    if insights:
        lines.append("- Indícios observados na série:")
        for insight in insights:
            lines.append(f"  - {insight}.")
        lines.append("- Observação metodológica: esses indícios mostram associações observadas na série histórica. Eles ajudam a investigação gerencial, mas não devem ser tratados isoladamente como causalidade comprovada.")
    lines.append("- Fontes públicas consultadas:")
    for source in sources:
        lines.append(f"  - [{source['name']}]({source['url']}): {source['description']}")
    return "\n".join(lines)
