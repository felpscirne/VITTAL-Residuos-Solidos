import os
from datetime import datetime
from collections import Counter

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URI = os.getenv('DATABASE_URL')
PASTA_PLANILHAS = 'sheets'

COLUMNS_NAMES = [
    'ticket', 'placa', 'data_hora', 'produto', 'transportadora', 'fornecedor_cliente',
    'peso_entrada', 'peso_saida', 'peso_liquido', 'peso_embalagem_liquido',
    'peso_embalagem_liquido_corrigido', 'peso_nota_fiscal', 'placa_veiculo',
    'diferenca_peso', 'diferenca_peso_porcentagem', 'nro_nota_fiscal', 'setor',
    'destino_procedencia',
]

REQUIRED_COLUMNS = ['ticket', 'data_hora', 'produto', 'fornecedor_cliente', 'setor']
TEXT_COLUMNS = ['placa', 'placa_veiculo', 'produto', 'transportadora', 'fornecedor_cliente', 'setor', 'nro_nota_fiscal']
WEIGHT_COLUMNS = [
    'peso_entrada', 'peso_saida', 'peso_liquido', 'peso_embalagem_liquido',
    'peso_embalagem_liquido_corrigido', 'peso_nota_fiscal', 'diferenca_peso',
]


def carregar_planilhas_em_dataframe(pasta):
    lista_de_dataframes = []
    arquivos = [f for f in os.listdir(pasta) if f.endswith('.ods') and not f.startswith('~')]
    print(f"Encontrados {len(arquivos)} arquivos na pasta '{pasta}':")

    for arquivo in arquivos:
        caminho_completo = os.path.join(pasta, arquivo)
        try:
            df = pd.read_excel(caminho_completo, engine='odf', skiprows=2)
            if df.shape[1] >= len(COLUMNS_NAMES):
                df = df.iloc[:, :len(COLUMNS_NAMES)]
                df.columns = COLUMNS_NAMES
                df['source_file'] = arquivo
                lista_de_dataframes.append(df)
                print(f"  - Lido com sucesso: {arquivo}")
            else:
                print(
                    f"  - ERRO: {arquivo} tem colunas insuficientes. "
                    f"Esperado {len(COLUMNS_NAMES)}, encontrado {df.shape[1]}"
                )
        except Exception as e:
            print(f"  - ERRO ao ler {arquivo}: {e}")

    if not lista_de_dataframes:
        return pd.DataFrame(), arquivos

    return pd.concat(lista_de_dataframes, ignore_index=True), arquivos


def _normalize_text(value):
    if pd.isna(value):
        return None
    text_value = str(value).strip()
    if not text_value or text_value.lower() == 'nan':
        return None
    return text_value


def _to_float(value):
    if pd.isna(value):
        return None

    text_value = str(value).strip().lower()
    if not text_value or text_value == 'nan':
        return None

    text_value = (
        text_value
        .replace('kg', '')
        .replace('%', '')
        .replace('.', '')
        .replace(',', '.')
    )

    filtered = ''.join(ch for ch in text_value if ch.isdigit() or ch in ['.', '-'])
    if not filtered or filtered in ['-', '.', '-.']:
        return None

    try:
        return float(filtered)
    except ValueError:
        return None


def _infer_setor_tipo(codigo_setor):
    if not codigo_setor:
        return 'interno'

    code = codigo_setor.upper()
    if 'CANDIOTA' in code:
        return 'destino'
    if 'ACERTO' in code:
        return 'ajuste'
    if 'INTERNO' in code or 'PATIO' in code:
        return 'interno'
    return 'coleta'


def tratar_planilhas_para_carga(df):
    if df.empty:
        return df, {
            'rows_read': 0,
            'rows_valid': 0,
            'rows_rejected': 0,
            'rejections_by_reason': {},
        }

    treated = df.copy()

    for col in TEXT_COLUMNS:
        treated[col] = treated[col].apply(_normalize_text)

    treated['ticket'] = treated['ticket'].apply(_to_float)
    treated['ticket'] = treated['ticket'].apply(lambda v: int(v) if v is not None and float(v).is_integer() else None)

    treated['data_hora'] = pd.to_datetime(treated['data_hora'], errors='coerce', dayfirst=True)

    for col in WEIGHT_COLUMNS:
        treated[col] = treated[col].apply(_to_float)

    treated['diferenca_peso_porcentagem'] = treated['diferenca_peso_porcentagem'].apply(_to_float)

    # Normalizacao final de campos auxiliares
    treated['setor_tipo'] = treated['setor'].apply(_infer_setor_tipo)
    treated['veiculo_resolvido'] = treated['placa_veiculo'].fillna(treated['placa'])

    rejection_reasons = []
    required_missing = treated[REQUIRED_COLUMNS].isna().any(axis=1)
    invalid_ticket = treated['ticket'].isna() | (treated['ticket'] <= 0)
    invalid_date = treated['data_hora'].isna()

    for idx in treated.index:
        reasons = []
        if required_missing.loc[idx]:
            reasons.append('missing_required_fields')
        if invalid_ticket.loc[idx]:
            reasons.append('invalid_ticket')
        if invalid_date.loc[idx]:
            reasons.append('invalid_data_hora')

        # Pesos de entrada/saida/liq não podem ser negativos
        for weight_col in ['peso_entrada', 'peso_saida', 'peso_liquido', 'peso_embalagem_liquido', 'peso_embalagem_liquido_corrigido', 'peso_nota_fiscal']:
            value = treated.at[idx, weight_col]
            if value is not None and pd.notna(value) and value < 0:
                reasons.append(f'negative_{weight_col}')
                break

        rejection_reasons.append(';'.join(sorted(set(reasons))) if reasons else '')

    treated['_rejection_reason'] = rejection_reasons
    rejected_mask = treated['_rejection_reason'] != ''

    valid_df = treated.loc[~rejected_mask].copy()
    valid_df = valid_df.sort_values(['ticket', 'data_hora']).drop_duplicates(subset=['ticket'], keep='last')
    valid_df = valid_df.drop(columns=['_rejection_reason'])

    rejection_counter = Counter()
    for raw_reasons in treated.loc[rejected_mask, '_rejection_reason'].tolist():
        for reason in raw_reasons.split(';'):
            if reason:
                rejection_counter[reason] += 1

    metrics = {
        'rows_read': len(df),
        'rows_valid': len(valid_df),
        'rows_rejected': int(rejected_mask.sum()),
        'rejections_by_reason': dict(rejection_counter),
    }

    return valid_df, metrics


def _create_audit_table_if_needed(conn):
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS import_auditoria (
                id SERIAL PRIMARY KEY,
                started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMP,
                status VARCHAR(20) NOT NULL,
                files_count INTEGER NOT NULL DEFAULT 0,
                rows_read INTEGER NOT NULL DEFAULT 0,
                rows_valid INTEGER NOT NULL DEFAULT 0,
                rows_new INTEGER NOT NULL DEFAULT 0,
                rows_updated INTEGER NOT NULL DEFAULT 0,
                details TEXT,
                error_message TEXT
            )
            """
        )
    )


def _start_audit(conn, files_count, rows_read):
    return conn.execute(
        text(
            """
            INSERT INTO import_auditoria (status, files_count, rows_read)
            VALUES ('running', :files_count, :rows_read)
            RETURNING id
            """
        ),
        {
            'files_count': files_count,
            'rows_read': rows_read,
        },
    ).scalar_one()


def _finish_audit(conn, audit_id, status, rows_valid, rows_new, rows_updated, details=None, error_message=None):
    conn.execute(
        text(
            """
            UPDATE import_auditoria
            SET
                finished_at = :finished_at,
                status = :status,
                rows_valid = :rows_valid,
                rows_new = :rows_new,
                rows_updated = :rows_updated,
                details = :details,
                error_message = :error_message
            WHERE id = :audit_id
            """
        ),
        {
            'finished_at': datetime.utcnow(),
            'status': status,
            'rows_valid': rows_valid,
            'rows_new': rows_new,
            'rows_updated': rows_updated,
            'details': details,
            'error_message': error_message,
            'audit_id': audit_id,
        },
    )


def enviar_para_postgres(df, db_uri, arquivos, metrics):
    if df.empty:
        print('Nenhum dado válido para enviar ao banco.')
        return

    if not db_uri:
        raise RuntimeError('DATABASE_URL não configurada no ambiente.')

    engine = create_engine(db_uri)

    with engine.begin() as conn:
        _create_audit_table_if_needed(conn)
        audit_id = _start_audit(conn, files_count=len(arquivos), rows_read=metrics.get('rows_read', len(df)))

    try:
        with engine.begin() as conn:
            before_count = conn.execute(text('SELECT COUNT(*) FROM pesagem')).scalar_one()

            staging = df[
                [
                    'ticket', 'data_hora', 'produto', 'transportadora', 'fornecedor_cliente',
                    'veiculo_resolvido', 'setor', 'setor_tipo',
                    'peso_entrada', 'peso_saida', 'peso_liquido', 'peso_embalagem_liquido',
                    'peso_embalagem_liquido_corrigido', 'peso_nota_fiscal', 'diferenca_peso',
                    'diferenca_peso_porcentagem', 'nro_nota_fiscal', 'source_file',
                ]
            ].copy()

            staging_table = 'staging_import_registro'
            conn.execute(text(f'DROP TABLE IF EXISTS {staging_table}'))

            staging.to_sql(staging_table, con=conn, if_exists='replace', index=False)

            conn.execute(
                text(
                    """
                    INSERT INTO produto (nome)
                    SELECT DISTINCT s.produto
                    FROM staging_import_registro s
                    WHERE s.produto IS NOT NULL
                    ON CONFLICT (nome) DO NOTHING
                    """
                )
            )

            conn.execute(
                text(
                    """
                    INSERT INTO empresa (nome, papel)
                    SELECT DISTINCT s.fornecedor_cliente, 'cliente'
                    FROM staging_import_registro s
                    WHERE s.fornecedor_cliente IS NOT NULL
                    ON CONFLICT (nome) DO UPDATE
                    SET papel = CASE
                        WHEN empresa.papel = EXCLUDED.papel THEN empresa.papel
                        WHEN empresa.papel = 'ambos' THEN 'ambos'
                        WHEN empresa.papel = 'interno' THEN EXCLUDED.papel
                        ELSE 'ambos'
                    END
                    """
                )
            )

            conn.execute(
                text(
                    """
                    INSERT INTO empresa (nome, papel)
                    SELECT DISTINCT s.transportadora, 'transportadora'
                    FROM staging_import_registro s
                    WHERE s.transportadora IS NOT NULL
                    ON CONFLICT (nome) DO UPDATE
                    SET papel = CASE
                        WHEN empresa.papel = EXCLUDED.papel THEN empresa.papel
                        WHEN empresa.papel = 'ambos' THEN 'ambos'
                        WHEN empresa.papel = 'interno' THEN EXCLUDED.papel
                        ELSE 'ambos'
                    END
                    """
                )
            )

            conn.execute(
                text(
                    """
                    INSERT INTO setor (codigo, nome, tipo)
                    SELECT DISTINCT s.setor, s.setor, s.setor_tipo
                    FROM staging_import_registro s
                    WHERE s.setor IS NOT NULL
                    ON CONFLICT (codigo) DO UPDATE
                    SET
                        nome = EXCLUDED.nome,
                        tipo = EXCLUDED.tipo
                    """
                )
            )

            conn.execute(
                text(
                    """
                    INSERT INTO veiculo (placa)
                    SELECT DISTINCT s.veiculo_resolvido
                    FROM staging_import_registro s
                    WHERE s.veiculo_resolvido IS NOT NULL
                    ON CONFLICT (placa) DO NOTHING
                    """
                )
            )

            conn.execute(
                text(
                    """
                    INSERT INTO pesagem (
                        ticket,
                        data_hora,
                        id_produto,
                        id_transportadora,
                        id_cliente,
                        id_veiculo,
                        id_setor,
                        peso_entrada,
                        peso_saida,
                        peso_liquido,
                        peso_embalagem_liquido,
                        peso_embalagem_liquido_corrigido,
                        peso_nota_fiscal,
                        diferenca_peso,
                        diferenca_peso_porcentagem,
                        nro_nota_fiscal
                    )
                    SELECT
                        s.ticket,
                        s.data_hora,
                        pr.id_produto,
                        t.id_empresa,
                        c.id_empresa,
                        v.id_veiculo,
                        st.id_setor,
                        s.peso_entrada,
                        s.peso_saida,
                        s.peso_liquido,
                        s.peso_embalagem_liquido,
                        s.peso_embalagem_liquido_corrigido,
                        s.peso_nota_fiscal,
                        s.diferenca_peso,
                        s.diferenca_peso_porcentagem,
                        s.nro_nota_fiscal
                    FROM staging_import_registro s
                    JOIN produto pr ON pr.nome = s.produto
                    JOIN empresa c ON c.nome = s.fornecedor_cliente
                    LEFT JOIN empresa t ON t.nome = s.transportadora
                    LEFT JOIN veiculo v ON v.placa = s.veiculo_resolvido
                    JOIN setor st ON st.codigo = s.setor
                    ON CONFLICT (ticket) DO UPDATE
                    SET
                        data_hora = EXCLUDED.data_hora,
                        id_produto = EXCLUDED.id_produto,
                        id_transportadora = EXCLUDED.id_transportadora,
                        id_cliente = EXCLUDED.id_cliente,
                        id_veiculo = EXCLUDED.id_veiculo,
                        id_setor = EXCLUDED.id_setor,
                        peso_entrada = EXCLUDED.peso_entrada,
                        peso_saida = EXCLUDED.peso_saida,
                        peso_liquido = EXCLUDED.peso_liquido,
                        peso_embalagem_liquido = EXCLUDED.peso_embalagem_liquido,
                        peso_embalagem_liquido_corrigido = EXCLUDED.peso_embalagem_liquido_corrigido,
                        peso_nota_fiscal = EXCLUDED.peso_nota_fiscal,
                        diferenca_peso = EXCLUDED.diferenca_peso,
                        diferenca_peso_porcentagem = EXCLUDED.diferenca_peso_porcentagem,
                        nro_nota_fiscal = EXCLUDED.nro_nota_fiscal
                    """
                )
            )

            conn.execute(text(f'DROP TABLE IF EXISTS {staging_table}'))
            after_count = conn.execute(text('SELECT COUNT(*) FROM pesagem')).scalar_one()

            rows_valid = len(df)
            rows_new = max(after_count - before_count, 0)
            rows_updated = max(rows_valid - rows_new, 0)
            rejections = metrics.get('rejections_by_reason', {})
            details = (
                f"Arquivos processados: {', '.join(arquivos)} | "
                f"Lidas: {metrics.get('rows_read', rows_valid)} | "
                f"Válidas: {rows_valid} | "
                f"Rejeitadas: {metrics.get('rows_rejected', 0)} | "
                f"Motivos: {rejections}"
            )

            _finish_audit(
                conn,
                audit_id=audit_id,
                status='success',
                rows_valid=rows_valid,
                rows_new=rows_new,
                rows_updated=rows_updated,
                details=details,
            )

        print(
            f'Importação concluída com sucesso. '\
            f'Registros válidos: {rows_valid} | Novos: {rows_new} | Atualizados: {rows_updated}'
        )

    except Exception as e:
        with engine.begin() as conn:
            _finish_audit(
                conn,
                audit_id=audit_id,
                status='error',
                rows_valid=0,
                rows_new=0,
                rows_updated=0,
                error_message=str(e),
            )
        raise


if __name__ == '__main__':
    if not os.path.exists(PASTA_PLANILHAS):
        print(f"Pasta '{PASTA_PLANILHAS}' não existe.")
        raise SystemExit(1)

    df_bruto, arquivos = carregar_planilhas_em_dataframe(PASTA_PLANILHAS)
    if df_bruto.empty:
        print('Nenhuma planilha válida foi carregada.')
        raise SystemExit(0)

    df_tratado, metrics = tratar_planilhas_para_carga(df_bruto)
    print(
        'Pré-processamento concluído. '
        f"Lidas: {metrics['rows_read']} | Válidas: {metrics['rows_valid']} | "
        f"Rejeitadas: {metrics['rows_rejected']}"
    )
    if metrics['rejections_by_reason']:
        print(f"Motivos de rejeição: {metrics['rejections_by_reason']}")

    enviar_para_postgres(df_tratado, DATABASE_URI, arquivos, metrics)