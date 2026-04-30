import pandas as pd

from app.services.dashboard_summaries import (
    summarize_auditoria,
    summarize_fluxo_macro,
    summarize_produtos_ranking,
    summarize_setor_temporal,
)


def test_summarize_produtos_ranking_handles_empty_data():
    assert summarize_produtos_ranking(pd.DataFrame()) == (
        "### Resumo analítico\n- Não há dados de produtos disponíveis."
    )


def test_summarize_produtos_ranking_calculates_top_participation():
    df = pd.DataFrame(
        {
            "produto": ["Metal", "Plastico"],
            "quantidade": [30, 70],
        }
    )

    summary = summarize_produtos_ranking(df)

    assert "Produto líder: **Metal** com 30 registros" in summary
    assert "Participação no top 10: **30.0%**" in summary


def test_summarize_setor_temporal_reports_peak_valley_and_growth():
    df = pd.DataFrame(
        {
            "mes": [1, 2, 3],
            "media_peso": [10.0, 5.0, 15.5],
        }
    )

    summary = summarize_setor_temporal(df, "Aterro", 2025)

    assert "mês 3" in summary
    assert "15.50 kg" in summary
    assert "mês 2" in summary
    assert "5.00 kg" in summary
    assert "5.50 kg" in summary


def test_summarize_auditoria_uses_absolute_mean_for_discrepancies():
    df = pd.DataFrame(
        {
            "ticket": [101, 102],
            "diferenca_percentual": [-20.0, 10.0],
        }
    )

    summary = summarize_auditoria(df, 5, "Cliente A")

    assert "Total de ocorrências acima do limite: **2**" in summary
    assert "ticket **101.0**" in summary
    assert "Média absoluta das discrepâncias: **15.00%**" in summary


def test_summarize_fluxo_macro_identifies_highest_and_lowest_balance():
    df = pd.DataFrame(
        {
            "periodo": ["2025-01", "2025-02", "2025-03"],
            "balanco": [100.0, -50.0, 25.0],
        }
    )

    summary = summarize_fluxo_macro(df)

    assert "Balanço médio mensal: **25.00 kg**" in summary
    assert "2025-01" in summary
    assert "2025-02" in summary
