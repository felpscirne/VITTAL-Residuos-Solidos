import pandas as pd

from app.services.import_pipeline import (
    COLUMNS_NAMES,
    OPTIONAL_RESIDUE_TYPE_COLUMN,
    _infer_setor_tipo,
    _normalize_text,
    _to_float,
    process_sheet_dataframe,
)


def _base_row(**overrides):
    row = {column: None for column in COLUMNS_NAMES}
    row.update(
        {
            "ticket": 123,
            "placa": "ABC1234",
            "data_hora": "10/01/2025 08:30",
            "produto": "Residuo",
            "transportadora": "Transportadora",
            "fornecedor_cliente": "Cliente",
            "peso_entrada": "1.500,50 kg",
            "peso_saida": "500,00 kg",
            "peso_liquido": "1000,50",
            "peso_embalagem_liquido": "0",
            "peso_embalagem_liquido_corrigido": "1000,50",
            "peso_nota_fiscal": "1000,50",
            "placa_veiculo": None,
            "diferenca_peso": "0",
            "diferenca_peso_porcentagem": "0%",
            "nro_nota_fiscal": "NF-1",
            "setor": "PATIO 1",
            "destino_procedencia": "Origem",
            OPTIONAL_RESIDUE_TYPE_COLUMN: "Classe II",
            "source_file": "arquivo.ods",
        }
    )
    row.update(overrides)
    return row


def test_normalize_text_converts_empty_values_to_none():
    assert _normalize_text("  abc  ") == "abc"
    assert _normalize_text(" nan ") is None
    assert _normalize_text(None) is None


def test_to_float_accepts_brazilian_number_formats_and_units():
    assert _to_float("1.234,56 kg") == 1234.56
    assert _to_float("-10,5%") == -10.5
    assert _to_float("abc") is None


def test_infer_setor_tipo_classifies_known_sector_codes():
    assert _infer_setor_tipo("CANDIOTA - saida") == "destino"
    assert _infer_setor_tipo("ACERTO BALANCA") == "ajuste"
    assert _infer_setor_tipo("PATIO INTERNO") == "interno"
    assert _infer_setor_tipo("ROTA 01") == "coleta"
    assert _infer_setor_tipo(None) == "interno"


def test_process_sheet_dataframe_normalizes_valid_rows():
    df = pd.DataFrame([_base_row()])

    processed, metrics = process_sheet_dataframe(df)

    assert metrics == {
        "rows_read": 1,
        "rows_valid": 1,
        "rows_rejected": 0,
        "rejections_by_reason": {},
    }
    assert processed.iloc[0]["ticket"] == 123
    assert processed.iloc[0]["setor_tipo"] == "interno"
    assert processed.iloc[0]["veiculo_resolvido"] == "ABC1234"
    assert float(processed.iloc[0]["peso_entrada"]) == 1500.50


def test_process_sheet_dataframe_rejects_invalid_rows_with_reasons():
    df = pd.DataFrame(
        [
            _base_row(ticket="abc"),
            _base_row(ticket=124, data_hora="data invalida"),
            _base_row(ticket=125, produto=None),
            _base_row(ticket=126, peso_liquido="-1"),
        ]
    )

    processed, metrics = process_sheet_dataframe(df)

    assert processed.empty
    assert metrics["rows_read"] == 4
    assert metrics["rows_valid"] == 0
    assert metrics["rows_rejected"] == 4
    assert metrics["rejections_by_reason"] == {
        "invalid_ticket": 1,
        "invalid_data_hora": 1,
        "missing_required_fields": 3,
        "negative_peso_liquido": 1,
    }


def test_process_sheet_dataframe_consolidates_identical_duplicate_tickets():
    df = pd.DataFrame(
        [
            _base_row(ticket=200, data_hora="10/01/2025 08:30", peso_liquido="10"),
            _base_row(ticket=200, data_hora="10/01/2025 08:30", peso_liquido="10"),
        ]
    )

    processed, metrics = process_sheet_dataframe(df)

    assert metrics["rows_valid"] == 1
    assert processed.iloc[0]["ticket"] == 200
    assert float(processed.iloc[0]["peso_liquido"]) == 10.0


def test_process_sheet_dataframe_generates_synthetic_ticket_for_conflicting_duplicates():
    df = pd.DataFrame(
        [
            _base_row(ticket=200, data_hora="10/01/2025 08:30", peso_liquido="10"),
            _base_row(ticket=200, data_hora="11/01/2025 08:30", peso_liquido="20"),
        ]
    )

    processed, metrics = process_sheet_dataframe(df)

    assert metrics["rows_valid"] == 2
    assert 200 in set(processed["ticket"].astype(int))
    assert any(ticket < 0 for ticket in processed["ticket"].astype(int))
