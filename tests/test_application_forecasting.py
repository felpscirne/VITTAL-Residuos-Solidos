import pandas as pd

from app.application import forecasting as forecasting_module


class _FakeForecastingRepository:
    def get_volume_quinzenal(self, tipo_residuo="todos"):
        return pd.DataFrame()

    def get_volume_movimentado_quinzenal(self, tipo_residuo="todos"):
        return pd.DataFrame()

    def get_entradas_quinzenais(self, tipo_residuo="todos"):
        return pd.DataFrame()

    def get_saidas_quinzenais(self, tipo_residuo="todos"):
        return pd.DataFrame()

    def get_setor_volume_quinzenal(self, setor, tipo_residuo="todos"):
        return pd.DataFrame()

    def get_volume_diario(self, tipo_residuo="todos", fill_gaps=True):
        return pd.DataFrame({"ds": pd.to_datetime(["2025-01-01"]), "y": [10.0]})

    def get_volume_movimentado_diario(self, tipo_residuo="todos", fill_gaps=True):
        return pd.DataFrame({"ds": pd.to_datetime(["2025-01-01"]), "y": [30.0]})

    def get_entradas_diarias(self, tipo_residuo="todos", fill_gaps=True):
        return pd.DataFrame({"ds": pd.to_datetime(["2025-01-01"]), "y": [10.0]})

    def get_saidas_diarias(self, tipo_residuo="todos", fill_gaps=True):
        return pd.DataFrame({"ds": pd.to_datetime(["2025-01-01"]), "y": [20.0]})

    def get_setor_volume_diario(self, setor, tipo_residuo="todos", fill_gaps=True):
        return pd.DataFrame({"ds": pd.to_datetime(["2025-01-01"]), "y": [5.0]})


def test_total_movement_forecast_uses_different_series_than_entries(monkeypatch):
    captured_inputs = []

    def fake_build_monthly_forecast(df, **kwargs):
        captured_inputs.append(df.copy())
        return {
            "status": "ok",
            "history": df.copy(),
            "forecast": df.copy().assign(yhat=df["y"], yhat_lower=df["y"], yhat_upper=df["y"]),
            "metrics": {},
            "public_data": {},
        }

    monkeypatch.setattr(forecasting_module, "build_monthly_forecast", fake_build_monthly_forecast)

    service = forecasting_module.ForecastingService(repository=_FakeForecastingRepository())

    total_result = service.get_volume_movimentado_diario_forecast(periods=7, fill_missing=False)
    entradas_result = service.get_entradas_diarias_forecast(periods=7, fill_missing=False)

    assert len(captured_inputs) == 2
    assert captured_inputs[0]["y"].tolist() == [30.0]
    assert captured_inputs[1]["y"].tolist() == [10.0]
    assert total_result["history"]["y"].tolist() != entradas_result["history"]["y"].tolist()
