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
            "description": "Temperatura media diaria e precipitacao diaria para Rio Grande - RS.",
        },
        {
            "name": "Feriados.com.br - Rio Grande/RS",
            "url": "https://feriados.com.br/RS/Rio%20Grande",
            "kind": "feriados_municipais_estaduais_federais",
            "description": "Calendario publico com feriados municipais, estaduais e federais de Rio Grande - RS.",
        },
        {
            "name": "Wikidata - Rio Grande (Q869571)",
            "url": "https://www.wikidata.org/wiki/Q869571",
            "kind": "localizacao",
            "description": "Coordenadas publicas do municipio de Rio Grande - RS.",
        },
    ],
}

FEATURE_LABELS = {
    "serie_historica_interna": "Historico operacional",
    "feriados_publicos_rio_grande_rs": "Feriados publicos de Rio Grande e do Brasil",
    "temp_mean": "Temperatura media",
    "precip_sum": "Precipitacao acumulada",
}

SMOOTHING_LABELS = {
    "rolling_median_ewma": "Media Movel Exponencialmente Ponderada",
    "none": "Sem estabilizacao adicional",
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


def _build_prophet_model(interval_width: float, holiday_df: pd.DataFrame, use_weather: bool, observations: int) -> Prophet:
    yearly_seasonality = observations >= 18
    n_changepoints = min(max(observations - 2, 0), 6)
    model = Prophet(
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="additive",
        changepoint_prior_scale=0.03,
        seasonality_prior_scale=5.0,
        holidays_prior_scale=3.0,
        n_changepoints=n_changepoints,
        interval_width=interval_width,
        holidays=holiday_df,
        stan_backend="CMDSTANPY",
    )
    if use_weather:
        model.add_regressor("temp_mean", standardize=True)
        model.add_regressor("precip_sum", standardize=True)
    return model


def _run_retrospective_validation(
    fit_df: pd.DataFrame,
    holiday_df: pd.DataFrame,
    interval_width: float,
    use_weather: bool,
    periods: int,
    cadence: str,
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
    coverage = float(
        (
            (comparison["y"] >= comparison["yhat_lower"]) &
            (comparison["y"] <= comparison["yhat_upper"])
        ).mean()
    )
    return {
        "retrospective_mae": mae,
        "retrospective_rmse": rmse,
        "retrospective_periods": int(len(comparison)),
        "retrospective_interval_coverage": coverage,
    }


def build_monthly_forecast(
    monthly_df: pd.DataFrame,
    periods: int = 4,
    interval_width: float = 0.8,
    cadence: str = "quinzenal",
) -> dict[str, Any]:
    if monthly_df is None or monthly_df.empty:
        return _empty_result("no_data", "Nao ha dados suficientes para gerar previsao.")

    required_columns = {"ds", "y"}
    if not required_columns.issubset(monthly_df.columns):
        return _empty_result("invalid_data", "A serie temporal precisa conter as colunas ds e y.")

    series_df, gap_info = _regularize_series(monthly_df, cadence)
    series_df = series_df.dropna(subset=["ds", "y"]).sort_values("ds")
    series_df = _stabilize_monthly_signal(series_df)
    cadence_label = "quinzenas" if cadence == "quinzenal" else "meses"

    if len(series_df) < 3:
        result = _empty_result("insufficient_data", "Sao necessarios pelo menos 3 pontos mensais para calcular a previsao.")
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result

    if Prophet is None:
        result = _empty_result(
            "unavailable",
            f"O modulo de previsao nao esta disponivel neste ambiente no momento. {PROPHET_IMPORT_ERROR or ''}".strip(),
        )
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result

    holiday_df, holiday_status = _build_holiday_dataframe(series_df["ds"].dt.year.min(), (series_df["ds"].dt.year.max() + 2))
    model_df, future_regressors, weather_status, weather_features = _attach_weather_regressors(series_df, periods)
    use_weather = all(feature in model_df.columns and model_df[feature].notna().any() for feature in weather_features)

    try:
        model = _build_prophet_model(
            interval_width=interval_width,
            holiday_df=holiday_df,
            use_weather=use_weather,
            observations=len(series_df),
        )
    except Exception as exc:
        result = _empty_result(
            "unavailable",
            f"O ambiente atual nao conseguiu inicializar o Prophet para esta previsao. {exc}",
        )
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result

    fit_df = model_df.copy()
    fit_df["y"] = fit_df["y_model"] if "y_model" in fit_df.columns else fit_df["y"]
    if use_weather:
        for regressor in weather_features:
            fit_df[regressor] = pd.to_numeric(fit_df[regressor], errors="coerce")
            fit_df[regressor] = fit_df[regressor].interpolate(method="linear", limit_direction="both")
            fit_df[regressor] = fit_df[regressor].fillna(fit_df[regressor].mean())
    fit_df = fit_df.dropna(subset=["ds", "y"]).copy()

    try:
        model.fit(fit_df)
    except Exception as exc:
        result = _empty_result(
            "unavailable",
            f"O ambiente atual nao conseguiu ajustar o modelo Prophet com seguranca. {exc}",
        )
        result["metrics"].update(gap_info | {"cadence_label": cadence_label})
        return result

    future = pd.DataFrame({"ds": fit_df["ds"].tolist() + _generate_future_dates(fit_df["ds"].max(), periods, cadence)})
    if use_weather:
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
            f"O ambiente atual nao conseguiu gerar a previsao com Prophet. {exc}",
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
    retrospective_metrics = _run_retrospective_validation(
        fit_df=fit_df,
        holiday_df=holiday_df,
        interval_width=interval_width,
        use_weather=use_weather,
        periods=periods,
        cadence=cadence,
    )

    mae = float((history["y"] - history["yhat"]).abs().mean())
    rmse = float(math.sqrt(((history["y"] - history["yhat"]) ** 2).mean()))
    last_actual = float(history["y"].iloc[-1])
    last_forecast = float(forecast_view["yhat"].iloc[-1])
    trend_pct = float(((last_forecast - last_actual) / last_actual) * 100) if last_actual else 0.0

    return {
        "status": "ok",
        "message": "Previsao gerada com Prophet.",
        "history": history,
        "forecast": forecast_view,
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
            "cadence_label": cadence_label,
            **retrospective_metrics,
            **gap_info,
        },
        "public_data": {
            "location": RIO_GRANDE_PUBLIC_CONTEXT,
            "sources": RIO_GRANDE_PUBLIC_CONTEXT["sources"],
            "weather_status": weather_status,
            "holiday_status": holiday_status,
            "features_used": ["serie_historica_interna", "feriados_publicos_rio_grande_rs", *(weather_features if use_weather else [])],
        },
    }


def build_forecast_summary_markdown(result: dict[str, Any]) -> str:
    status = result.get("status")
    if status != "ok":
        return "### Previsao temporal\n" f"- Status: {status}\n" f"- Observacao: {result.get('message', 'Nao foi possivel gerar a previsao.')}"

    metrics = result["metrics"]
    direction = "crescimento" if metrics["trend_pct"] >= 0 else "queda"
    intervalo_nominal = int(metrics["confidence"] * 100)
    cadence_label = metrics.get("cadence_label", "periodos")
    cobertura_empirica = metrics.get("retrospective_interval_coverage", 0.0) * 100
    smoothing_label = SMOOTHING_LABELS.get(metrics.get("signal_smoothing", "none"), metrics.get("signal_smoothing", "none"))
    return (
        "### Resumo preditivo\n"
        f"- Observacoes historicas: {metrics['observations']}\n"
        f"- Horizonte de previsao: {metrics['forecast_periods']} {cadence_label}\n"
        f"- Intervalo preditivo nominal exibido: **{intervalo_nominal}%**\n"
        f"- Periodos ausentes tratados antes do ajuste: {metrics.get('missing_months_filled', 0)}\n"
        f"- Estabilizacao da serie para treino: {smoothing_label}\n"

        f"- Erro medio absoluto (MAE): {metrics['mae']:.2f}\n"
        f"- Raiz do erro quadratico medio (RMSE): {metrics['rmse']:.2f}\n"
        f"- Validacao retrospectiva ({metrics.get('retrospective_periods', 0)} periodos): MAE {metrics.get('retrospective_mae', 0.0):.2f} | RMSE {metrics.get('retrospective_rmse', 0.0):.2f}\n"
        f"- Cobertura empirica do intervalo na validacao: {cobertura_empirica:.2f}%\n"
        f"- Ultimo volume observado: {metrics['last_actual']:.2f} kg\n"
        f"- Volume previsto no fim do horizonte: {metrics['last_forecast']:.2f} kg\n"
        f"- Tendencia estimada: {direction} de {abs(metrics['trend_pct']):.2f}% no horizonte projetado\n"
        "- Interpretacao: o percentual nominal do intervalo e a cobertura empirica observada nao sao necessariamente iguais; a validacao retrospectiva indica quao bem o intervalo cobriu os valores reais recentes."
    )


def build_public_data_markdown(result: dict[str, Any]) -> str:
    public_data = result.get("public_data", {})
    location = public_data.get("location", RIO_GRANDE_PUBLIC_CONTEXT)
    weather_status = public_data.get("weather_status", "desconhecido")
    holiday_status = public_data.get("holiday_status", "desconhecido")
    features_used = public_data.get("features_used", [])
    sources = public_data.get("sources", [])
    feature_labels = [FEATURE_LABELS.get(feature, feature) for feature in features_used]

    lines = [
        "### Dados publicos usados no modelo",
        f"- Localizacao de referencia: **{location['city']} - {location['state']}**, coordenadas aproximadas **{location['latitude']}, {location['longitude']}**.",
        f"- Status do clima publico: **{weather_status}**.",
        f"- Status dos feriados publicos: **{holiday_status}**.",
        f"- Variaveis externas usadas: **{', '.join(feature_labels) if feature_labels else 'nenhuma'}**.",
        f"- Periodos ausentes tratados na serie: **{result.get('metrics', {}).get('missing_months_filled', 0)}**.",
        "- Classificacao do tipo de residuo: derivada internamente a partir do campo `produto`, com categorias operacionais como domiciliar, hospitalar e reciclavel.",
        "- Fontes:",
    ]
    for source in sources:
        lines.append(f"  - [{source['name']}]({source['url']}): {source['description']}")
    return "\n".join(lines)
