from typing import Protocol

from app.extensions import cache
from app.services.forecast_service import (
    build_public_data_markdown,
    build_forecast_summary_markdown,
    build_monthly_forecast,
)


class ForecastingRepositoryPort(Protocol):
    def get_volume_quinzenal(self, tipo_residuo="todos"):
        ...

    def get_volume_movimentado_quinzenal(self, tipo_residuo="todos"):
        ...

    def get_entradas_quinzenais(self, tipo_residuo="todos"):
        ...

    def get_saidas_quinzenais(self, tipo_residuo="todos"):
        ...

    def get_setor_volume_quinzenal(self, setor, tipo_residuo="todos"):
        ...

    def get_volume_diario(self, tipo_residuo="todos", fill_gaps=True):
        ...

    def get_volume_movimentado_diario(self, tipo_residuo="todos", fill_gaps=True):
        ...

    def get_entradas_diarias(self, tipo_residuo="todos", fill_gaps=True):
        ...

    def get_saidas_diarias(self, tipo_residuo="todos", fill_gaps=True):
        ...

    def get_setor_volume_diario(self, setor, tipo_residuo="todos", fill_gaps=True):
        ...


def _profile_for_cadence(cadence: str, setorial: bool = False) -> str:
    if cadence == "diaria":
        return "diaria"
    if setorial:
        return "setor"
    return "default"


class ForecastingService:
    def __init__(self, repository: ForecastingRepositoryPort):
        self._repository = repository

    # ---- Quinzenal (legado) ----
    @cache.memoize(timeout=3600)
    def get_volume_quinzenal_forecast(self, periods=4, interval_width=0.8, tipo_residuo="todos"):
        monthly_df = self._repository.get_volume_quinzenal(tipo_residuo=tipo_residuo)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
            cadence="quinzenal",
            forecast_profile="default",
        )

    @cache.memoize(timeout=3600)
    def get_volume_quinzenal_forecast_summary(self, periods=4, interval_width=0.8, tipo_residuo="todos"):
        result = self.get_volume_quinzenal_forecast(
            periods=periods,
            interval_width=interval_width,
            tipo_residuo=tipo_residuo,
        )
        return build_forecast_summary_markdown(result)

    @cache.memoize(timeout=3600)
    def get_entradas_quinzenais_forecast(self, periods=4, interval_width=0.8, tipo_residuo="todos"):
        monthly_df = self._repository.get_entradas_quinzenais(tipo_residuo=tipo_residuo)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
            cadence="quinzenal",
            forecast_profile="default",
        )

    @cache.memoize(timeout=3600)
    def get_saidas_quinzenais_forecast(self, periods=4, interval_width=0.8, tipo_residuo="todos"):
        monthly_df = self._repository.get_saidas_quinzenais(tipo_residuo=tipo_residuo)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
            cadence="quinzenal",
            forecast_profile="default",
        )

    @cache.memoize(timeout=3600)
    def get_setor_volume_quinzenal_forecast(self, setor, periods=4, interval_width=0.8, tipo_residuo="todos"):
        monthly_df = self._repository.get_setor_volume_quinzenal(setor, tipo_residuo=tipo_residuo)
        return build_monthly_forecast(
            monthly_df,
            periods=periods,
            interval_width=interval_width,
            cadence="quinzenal",
            forecast_profile="setor",
        )

    # ---- Diária (novo, usada pela página de previsões com seleção de dias) ----
    @cache.memoize(timeout=3600)
    def get_volume_diario_forecast(self, periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
        daily_df = self._repository.get_volume_diario(tipo_residuo=tipo_residuo, fill_gaps=False)
        return build_monthly_forecast(
            daily_df,
            periods=periods,
            interval_width=interval_width,
            cadence="diaria",
            forecast_profile="diaria",
            validation_window=validation_window,
            fill_missing=fill_missing,
        )

    @cache.memoize(timeout=3600)
    def get_volume_movimentado_diario_forecast(self, periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
        daily_df = self._repository.get_volume_movimentado_diario(tipo_residuo=tipo_residuo, fill_gaps=False)
        return build_monthly_forecast(
            daily_df,
            periods=periods,
            interval_width=interval_width,
            cadence="diaria",
            forecast_profile="diaria",
            validation_window=validation_window,
            fill_missing=fill_missing,
        )

    @cache.memoize(timeout=3600)
    def get_entradas_diarias_forecast(self, periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
        daily_df = self._repository.get_entradas_diarias(tipo_residuo=tipo_residuo, fill_gaps=False)
        return build_monthly_forecast(
            daily_df,
            periods=periods,
            interval_width=interval_width,
            cadence="diaria",
            forecast_profile="diaria",
            validation_window=validation_window,
            fill_missing=fill_missing,
        )

    @cache.memoize(timeout=3600)
    def get_saidas_diarias_forecast(self, periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
        daily_df = self._repository.get_saidas_diarias(tipo_residuo=tipo_residuo, fill_gaps=False)
        return build_monthly_forecast(
            daily_df,
            periods=periods,
            interval_width=interval_width,
            cadence="diaria",
            forecast_profile="diaria",
            validation_window=validation_window,
            fill_missing=fill_missing,
        )

    @cache.memoize(timeout=3600)
    def get_setor_volume_diario_forecast(self, setor, periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
        daily_df = self._repository.get_setor_volume_diario(setor, tipo_residuo=tipo_residuo, fill_gaps=False)
        return build_monthly_forecast(
            daily_df,
            periods=periods,
            interval_width=interval_width,
            cadence="diaria",
            forecast_profile="diaria",
            validation_window=validation_window,
            fill_missing=fill_missing,
        )


def build_default_forecasting_service():
    from app.infrastructure.analytics_repository import SqlAnalyticsRepositoryAdapter

    return ForecastingService(repository=SqlAnalyticsRepositoryAdapter())


_default_forecasting_service = build_default_forecasting_service()


# ---- Fachadas quinzenais (mantidas para não quebrar chamadas existentes) ----
def get_volume_mensal_forecast(periods=4, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_volume_quinzenal_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_volume_mensal_forecast_summary(periods=4, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_volume_quinzenal_forecast_summary(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_entradas_mensais_forecast(periods=4, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_entradas_quinzenais_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_saidas_mensais_forecast(periods=4, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_saidas_quinzenais_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


def get_setor_volume_mensal_forecast(setor, periods=4, interval_width=0.8, tipo_residuo="todos"):
    return _default_forecasting_service.get_setor_volume_quinzenal_forecast(
        setor,
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
    )


# ---- Fachadas diárias (nova cadência suportada pela página de previsões) ----
def get_volume_diario_forecast(periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
    return _default_forecasting_service.get_volume_diario_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
        validation_window=validation_window,
        fill_missing=fill_missing,
        cache_version=cache_version,
    )


def get_volume_movimentado_diario_forecast(periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
    return _default_forecasting_service.get_volume_movimentado_diario_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
        validation_window=validation_window,
        fill_missing=fill_missing,
        cache_version=cache_version,
    )


def get_entradas_diarias_forecast(periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
    return _default_forecasting_service.get_entradas_diarias_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
        validation_window=validation_window,
        fill_missing=fill_missing,
        cache_version=cache_version,
    )


def get_saidas_diarias_forecast(periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
    return _default_forecasting_service.get_saidas_diarias_forecast(
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
        validation_window=validation_window,
        fill_missing=fill_missing,
        cache_version=cache_version,
    )


def get_setor_volume_diario_forecast(setor, periods=15, interval_width=0.8, tipo_residuo="todos", validation_window=30, fill_missing=True, cache_version="daily-gap-v2"):
    return _default_forecasting_service.get_setor_volume_diario_forecast(
        setor,
        periods=periods,
        interval_width=interval_width,
        tipo_residuo=tipo_residuo,
        validation_window=validation_window,
        fill_missing=fill_missing,
        cache_version=cache_version,
    )


def get_public_data_context_markdown(result):
    return build_public_data_markdown(result)
