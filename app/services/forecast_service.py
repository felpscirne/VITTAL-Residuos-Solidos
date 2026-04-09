from __future__ import annotations

import math
from typing import Any

import pandas as pd

try:
    from prophet import Prophet
    PROPHET_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - depends on local runtime/install
    Prophet = None
    PROPHET_IMPORT_ERROR = str(exc)


def _empty_result(status: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "history": pd.DataFrame(),
        "forecast": pd.DataFrame(),
        "metrics": {},
    }


def build_monthly_forecast(monthly_df: pd.DataFrame, periods: int = 6) -> dict[str, Any]:
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
        return _empty_result(
            "insufficient_data",
            "Sao necessarios pelo menos 3 pontos mensais para calcular a previsao.",
        )

    if Prophet is None:
        return _empty_result(
            "unavailable",
            "Prophet indisponivel neste ambiente. "
            f"Detalhe tecnico: {PROPHET_IMPORT_ERROR or 'nao foi possivel importar a biblioteca.'}",
        )

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.8,
    )
    model.fit(series_df)

    future = model.make_future_dataframe(periods=periods, freq="MS")
    forecast = model.predict(future)

    forecast_view = forecast[
        ["ds", "yhat", "yhat_lower", "yhat_upper", "trend"]
    ].copy()
    history = series_df.merge(forecast_view[["ds", "yhat"]], on="ds", how="left")

    mae = float((history["y"] - history["yhat"]).abs().mean())
    rmse = float(math.sqrt(((history["y"] - history["yhat"]) ** 2).mean()))
    last_actual = float(history["y"].iloc[-1])
    last_forecast = forecast_view["yhat"].iloc[-1]
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
            "last_forecast": float(last_forecast),
            "trend_pct": trend_pct,
            "observations": int(len(history)),
            "forecast_periods": int(periods),
        },
    }


def build_forecast_summary_markdown(result: dict[str, Any]) -> str:
    status = result.get("status")
    if status != "ok":
        return (
            "### Previsao temporal\n"
            f"- Status: {status}\n"
            f"- Observacao: {result.get('message', 'Nao foi possivel gerar a previsao.')}"
        )

    metrics = result["metrics"]
    direction = "crescimento" if metrics["trend_pct"] >= 0 else "queda"

    return (
        "### Resumo preditivo\n"
        f"- Observacoes historicas: {metrics['observations']}\n"
        f"- Horizonte de previsao: {metrics['forecast_periods']} meses\n"
        f"- Erro medio absoluto (MAE): {metrics['mae']:.2f}\n"
        f"- Raiz do erro quadratico medio (RMSE): {metrics['rmse']:.2f}\n"
        f"- Ultimo volume observado: {metrics['last_actual']:.2f} kg\n"
        f"- Volume previsto no fim do horizonte: {metrics['last_forecast']:.2f} kg\n"
        f"- Tendencia estimada: {direction} de {abs(metrics['trend_pct']):.2f}% no horizonte projetado\n"
        "- Interpretacao: use esta projecao como apoio ao planejamento logistico e orcamentario, "
        "sempre confrontando previsto versus realizado."
    )
