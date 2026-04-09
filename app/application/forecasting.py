from typing import Protocol

from app.services.forecast_service import (
    build_public_data_markdown,
    build_forecast_summary_markdown,
    build_monthly_forecast,
)


class ForecastingRepositoryPort(Protocol):
    def get_volume_mensal(self, tipo_residuo="todos"):
        ...

    def get_entradas_mensais(self, tipo_residuo="todos"):
        ...

    def get_saidas_mensais(self, tipo_residuo="todos"):
        ...

    def get_setor_volume_mensal(self, setor, tipo_residuo="todos"):
        ...


class ForecastingService:
    def __init__(self, repository: ForecastingRepositoryPort):
        self._repository = repository

    def get_volume_mensal_forecast(self, periods=6, interval_width=0.8, tipo_residuo="todos"):
        monthly_df = self._repository.get_volume_mensal(tipo_residuo=tipo_residuo)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
        )

    def get_volume_mensal_forecast_summary(self, periods=6, interval_width=0.8, tipo_residuo="todos"):
        result = self.get_volume_mensal_forecast(
            periods=periods,
            interval_width=interval_width,
            tipo_residuo=tipo_residuo,
        )
        return build_forecast_summary_markdown(result)

    def get_entradas_mensais_forecast(self, periods=6, interval_width=0.8, tipo_residuo="todos"):
        monthly_df = self._repository.get_entradas_mensais(tipo_residuo=tipo_residuo)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
        )

    def get_saidas_mensais_forecast(self, periods=6, interval_width=0.8, tipo_residuo="todos"):
        monthly_df = self._repository.get_saidas_mensais(tipo_residuo=tipo_residuo)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
        )

    def get_setor_volume_mensal_forecast(self, setor, periods=6, interval_width=0.8, tipo_residuo="todos"):
        monthly_df = self._repository.get_setor_volume_mensal(setor, tipo_residuo=tipo_residuo)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
        )


def build_default_forecasting_service():
    from app.infrastructure.analytics_repository import SqlAnalyticsRepositoryAdapter

    return ForecastingService(repository=SqlAnalyticsRepositoryAdapter())


_default_forecasting_service = build_default_forecasting_service()


def get_volume_mensal_forecast(periods=6, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_volume_mensal_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_volume_mensal_forecast_summary(periods=6, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_volume_mensal_forecast_summary(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_entradas_mensais_forecast(periods=6, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_entradas_mensais_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_saidas_mensais_forecast(periods=6, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_saidas_mensais_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_setor_volume_mensal_forecast(setor, periods=6, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_setor_volume_mensal_forecast(
        setor,
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_public_data_context_markdown(result):
    return build_public_data_markdown(result)
