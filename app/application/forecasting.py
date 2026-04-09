from typing import Protocol

from app.services.forecast_service import (
    build_forecast_summary_markdown,
    build_monthly_forecast,
)


class ForecastingRepositoryPort(Protocol):
    def get_volume_mensal(self):
        ...


class ForecastingService:
    def __init__(self, repository: ForecastingRepositoryPort):
        self._repository = repository

    def get_volume_mensal_forecast(self, periods=6):
        monthly_df = self._repository.get_volume_mensal()
        return build_monthly_forecast(monthly_df, periods=periods)

    def get_volume_mensal_forecast_summary(self, periods=6):
        result = self.get_volume_mensal_forecast(periods=periods)
        return build_forecast_summary_markdown(result)


def build_default_forecasting_service():
    from app.infrastructure.analytics_repository import SqlAnalyticsRepositoryAdapter

    return ForecastingService(repository=SqlAnalyticsRepositoryAdapter())


_default_forecasting_service = build_default_forecasting_service()


def get_volume_mensal_forecast(periods=6):
    return _default_forecasting_service.get_volume_mensal_forecast(periods=periods)


def get_volume_mensal_forecast_summary(periods=6):
    return _default_forecasting_service.get_volume_mensal_forecast_summary(periods=periods)
