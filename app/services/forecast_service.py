from __future__ import annotations

import math
from datetime import date, datetime, timedelta
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
            "name": "BrasilAPI - Feriados Nacionais",
            "url": "https://brasilapi.com.br/docs#tag/Feriados",
            "kind": "feriados_nacionais",
            "description": "Referencia publica para feriados nacionais do Brasil.",
        },
        {
            "name": "Prefeitura Municipal do Rio Grande - Sao Pedro",
            "url": "https://www.riogrande.rs.gov.br/consulta/index.php/noticias/detalhes%2B23b81%2C%2Camanha---feriado-de-sao-pedro---e-dia-de-passe-livre-no-municipio.html",
            "kind": "feriado_municipal",
            "description": "Confirmacao publica do feriado municipal de Sao Pedro em 29 de junho.",
        },
        {
            "name": "Wikidata - Rio Grande (Q869571)",
            "url": "https://www.wikidata.org/wiki/Q869571",
            "kind": "localizacao",
            "description": "Coordenadas publicas do municipio de Rio Grande - RS.",
        },
    ],
}


def _empty_result(status: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "history": pd.DataFrame(),
        "forecast": pd.DataFrame(),
        "metrics": {},
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


def build_rio_grande_holidays(start_year: int, end_year: int) -> pd.DataFrame:
    rows = []
    for year in range(start_year, end_year + 1):
        easter = _easter_date(year)
        movable = {
            "carnaval_segunda": easter - timedelta(days=48),
            "carnaval_terca": easter - timedelta(days=47),
            "sexta_santa": easter - timedelta(days=2),
            "corpus_christi": easter + timedelta(days=60),
        }
        fixed = {
            "confraternizacao_universal": date(year, 1, 1),
            "tiradentes": date(year, 4, 21),
            "dia_do_trabalhador": date(year, 5, 1),
            "independencia_do_brasil": date(year, 9, 7),
            "revolucao_farroupilha": date(year, 9, 20),
            "nossa_senhora_aparecida": date(year, 10, 12),
            "finados": date(year, 11, 2),
            "proclamacao_da_republica": date(year, 11, 15),
            "natal": date(year, 12, 25),
            "sao_pedro_rio_grande": date(year, 6, 29),
        }
        for holiday_name, holiday_date in {**fixed, **movable}.items():
            rows.append(
                {
                    "holiday": holiday_name,
                    "ds": pd.Timestamp(holiday_date),
                    "lower_window": 0,
                    "upper_window": 0,
                }
            )
    return pd.DataFrame(rows)


def fetch_rio_grande_weather_monthly(start_date: pd.Timestamp, end_date: pd.Timestamp) -> tuple[pd.DataFrame, str]:
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

    model_df = series_df.merge(weather_df, on="ds", how="left")
    climatology = _build_monthly_climatology(weather_df)
    future_dates = pd.date_range(series_df["ds"].max() + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
    future_regressors = pd.DataFrame({"ds": future_dates})
    future_regressors["month_num"] = future_regressors["ds"].dt.month
    future_regressors = future_regressors.merge(climatology, on="month_num", how="left").drop(columns=["month_num"])
    return model_df, future_regressors, weather_status, ["temp_mean", "precip_sum"]


def build_monthly_forecast(monthly_df: pd.DataFrame, periods: int = 6, interval_width: float = 0.8) -> dict[str, Any]:
    if monthly_df is None or monthly_df.empty:
        return _empty_result("no_data", "Nao ha dados suficientes para gerar previsao.")

    required_columns = {"ds", "y"}
    if not required_columns.issubset(monthly_df.columns):
        return _empty_result("invalid_data", "A serie temporal precisa conter as colunas ds e y.")

    series_df = monthly_df.copy()
    series_df["ds"] = pd.to_datetime(series_df["ds"])
    series_df["y"] = pd.to_numeric(series_df["y"], errors="coerce")
    series_df = series_df.dropna(subset=["ds", "y"]).sort_values("ds")

    if len(series_df) < 3:
        return _empty_result("insufficient_data", "Sao necessarios pelo menos 3 pontos mensais para calcular a previsao.")

    if Prophet is None:
        return _empty_result(
            "unavailable",
            "O modulo de previsao nao esta disponivel neste ambiente no momento.",
        )

    holiday_df = build_rio_grande_holidays(series_df["ds"].dt.year.min(), (series_df["ds"].dt.year.max() + 2))
    model_df, future_regressors, weather_status, weather_features = _attach_weather_regressors(series_df, periods)

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=interval_width,
        holidays=holiday_df,
    )

    for regressor in weather_features:
        if regressor in model_df.columns and model_df[regressor].notna().any():
            model.add_regressor(regressor)

    fit_df = model_df.dropna().copy() if weather_features else model_df.copy()
    if len(fit_df) < 3:
        fit_df = series_df.copy()

    model.fit(fit_df)

    future = model.make_future_dataframe(periods=periods, freq="MS")
    if weather_features:
        future = future.merge(model_df[["ds", *weather_features]], on="ds", how="left")
        if not future_regressors.empty:
            for regressor in weather_features:
                future.loc[future["ds"].isin(future_regressors["ds"]), regressor] = future_regressors.set_index("ds")[regressor]
        for regressor in weather_features:
            future[regressor] = pd.to_numeric(future[regressor], errors="coerce")
            future[regressor] = future[regressor].fillna(future[regressor].mean())

    forecast = model.predict(future)
    forecast_view = forecast[["ds", "yhat", "yhat_lower", "yhat_upper", "trend"]].copy()
    history = series_df.merge(forecast_view[["ds", "yhat"]], on="ds", how="left")

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
        },
        "public_data": {
            "location": RIO_GRANDE_PUBLIC_CONTEXT,
            "sources": RIO_GRANDE_PUBLIC_CONTEXT["sources"],
            "weather_status": weather_status,
            "holiday_status": "ok",
            "features_used": ["serie_historica_interna", "feriados_publicos_rio_grande_rs", *weather_features],
        },
    }


def build_forecast_summary_markdown(result: dict[str, Any]) -> str:
    status = result.get("status")
    if status != "ok":
        return "### Previsao temporal\n" f"- Status: {status}\n" f"- Observacao: {result.get('message', 'Nao foi possivel gerar a previsao.')}"

    metrics = result["metrics"]
    direction = "crescimento" if metrics["trend_pct"] >= 0 else "queda"
    confianca = int(metrics["confidence"] * 100)
    return (
        "### Resumo preditivo\n"
        f"- Observacoes historicas: {metrics['observations']}\n"
        f"- Horizonte de previsao: {metrics['forecast_periods']} meses\n"
        f"- Faixa de confianca exibida: **{confianca}%**\n"
        f"- Erro medio absoluto (MAE): {metrics['mae']:.2f}\n"
        f"- Raiz do erro quadratico medio (RMSE): {metrics['rmse']:.2f}\n"
        f"- Ultimo volume observado: {metrics['last_actual']:.2f} kg\n"
        f"- Volume previsto no fim do horizonte: {metrics['last_forecast']:.2f} kg\n"
        f"- Tendencia estimada: {direction} de {abs(metrics['trend_pct']):.2f}% no horizonte projetado\n"
        "- Interpretacao: use a projecao como apoio ao planejamento logistico e orcamentario, confrontando previsto versus realizado."
    )


def build_public_data_markdown(result: dict[str, Any]) -> str:
    public_data = result.get("public_data", {})
    location = public_data.get("location", RIO_GRANDE_PUBLIC_CONTEXT)
    weather_status = public_data.get("weather_status", "desconhecido")
    holiday_status = public_data.get("holiday_status", "desconhecido")
    features_used = public_data.get("features_used", [])
    sources = public_data.get("sources", [])

    lines = [
        "### Dados publicos usados no modelo",
        f"- Localizacao de referencia: **{location['city']} - {location['state']}**, coordenadas aproximadas **{location['latitude']}, {location['longitude']}**.",
        f"- Status do clima publico: **{weather_status}**.",
        f"- Status dos feriados publicos: **{holiday_status}**.",
        f"- Variaveis externas usadas: **{', '.join(features_used) if features_used else 'nenhuma'}**.",
        "- Classificacao do tipo de residuo: derivada internamente a partir do campo `produto`, com categorias operacionais como domiciliar, hospitalar e reciclavel.",
        "- Fontes:",
    ]
    for source in sources:
        lines.append(f"  - [{source['name']}]({source['url']}): {source['description']}")
    return "\n".join(lines)
