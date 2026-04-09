from typing import Protocol

from app.services.forecast_service import (
    build_public_data_markdown,
    build_forecast_summary_markdown,
    build_monthly_forecast,
)


class ForecastingRepositoryPort(Protocol):
    def get_volume_mensal(self):
        ...

    def get_entradas_mensais(self):
        ...

    def get_saidas_mensais(self):
        ...

    def get_setor_volume_mensal(self, setor):
        ...


class ForecastingService:
    def __init__(self, repository: ForecastingRepositoryPort):
        self._repository = repository

    def get_volume_mensal_forecast(self, periods=6, interval_width=0.8):
        monthly_df = self._repository.get_volume_mensal()
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
        )

    def get_volume_mensal_forecast_summary(self, periods=6, interval_width=0.8):
        result = self.get_volume_mensal_forecast(
            periods=periods,
            interval_width=interval_width,
        )
        return build_forecast_summary_markdown(result)

    def get_entradas_mensais_forecast(self, periods=6, interval_width=0.8):
        monthly_df = self._repository.get_entradas_mensais()
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
        )

    def get_saidas_mensais_forecast(self, periods=6, interval_width=0.8):
        monthly_df = self._repository.get_saidas_mensais()
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
        )

    def get_setor_volume_mensal_forecast(self, setor, periods=6, interval_width=0.8):
        monthly_df = self._repository.get_setor_volume_mensal(setor)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
        )


def build_default_forecasting_service():
    from app.infrastructure.analytics_repository import SqlAnalyticsRepositoryAdapter

    return ForecastingService(repository=SqlAnalyticsRepositoryAdapter())


_default_forecasting_service = build_default_forecasting_service()


def get_volume_mensal_forecast(periods=6, interval_width=0.8):
    return _default_forecasting_service.get_volume_mensal_forecast(
        periods=periods,
        interval_width=interval_width,
    )


def get_volume_mensal_forecast_summary(periods=6, interval_width=0.8):
    return _default_forecasting_service.get_volume_mensal_forecast_summary(
        periods=periods,
        interval_width=interval_width,
    )


def get_entradas_mensais_forecast(periods=6, interval_width=0.8):
    return _default_forecasting_service.get_entradas_mensais_forecast(
        periods=periods,
        interval_width=interval_width,
    )


def get_saidas_mensais_forecast(periods=6, interval_width=0.8):
    return _default_forecasting_service.get_saidas_mensais_forecast(
        periods=periods,
        interval_width=interval_width,
    )


def get_setor_volume_mensal_forecast(setor, periods=6, interval_width=0.8):
    return _default_forecasting_service.get_setor_volume_mensal_forecast(
        setor,
        periods=periods,
        interval_width=interval_width,
    )


def get_public_data_context_markdown(result):
    return build_public_data_markdown(result)
