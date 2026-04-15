import os
import zlib
from collections import Counter
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, text

load_dotenv()

DATABASE_URI = os.getenv("DATABASE_URL")
IMPORT_INITIATED_BY = os.getenv("IMPORT_INITIATED_BY", "Sistema")
PASTA_PLANILHAS = "sheets"

COLUMNS_NAMES = [
    "ticket", "placa", "data_hora", "produto", "transportadora", "fornecedor_cliente",
    "peso_entrada", "peso_saida", "peso_liquido", "peso_embalagem_liquido",
    "peso_embalagem_liquido_corrigido", "peso_nota_fiscal", "placa_veiculo",
    "diferenca_peso", "diferenca_peso_porcentagem", "nro_nota_fiscal", "setor",
    "destino_procedencia",
]

REQUIRED_COLUMNS = ["ticket", "data_hora", "produto", "fornecedor_cliente", "setor"]
TEXT_COLUMNS = ["placa", "placa_veiculo", "produto", "transportadora", "fornecedor_cliente", "setor", "nro_nota_fiscal"]
WEIGHT_COLUMNS = [
    "peso_entrada", "peso_saida", "peso_liquido", "peso_embalagem_liquido",
    "peso_embalagem_liquido_corrigido", "peso_nota_fiscal", "diferenca_peso",
]


def listar_arquivos_planilha(pasta):
    return [f for f in os.listdir(pasta) if f.endswith(".ods") and not f.startswith("~")]


def carregar_planilha_individual(caminho_completo, arquivo):
    try:
        df = pd.read_excel(caminho_completo, engine="odf", skiprows=2)
        if df.shape[1] < len(COLUMNS_NAMES):
            print(
                f"  - ERRO: {arquivo} tem colunas insuficientes. "
                f"Esperado {len(COLUMNS_NAMES)}, encontrado {df.shape[1]}"
            )
            return pd.DataFrame()

        df = df.iloc[:, :len(COLUMNS_NAMES)].copy()
        df.columns = COLUMNS_NAMES
        df["source_file"] = arquivo
        print(f"  - Lido com sucesso: {arquivo}")
        return df
    except Exception as exc:
        print(f"  - ERRO ao ler {arquivo}: {exc}")
        return pd.DataFrame()


def _normalize_text(value):
    if pd.isna(value):
        return None
    text_value = str(value).strip()
    if not text_value or text_value.lower() == "nan":
        return None
    return text_value


def _to_float(value):
    if pd.isna(value):
        return None

    text_value = str(value).strip().lower()
    if not text_value or text_value == "nan":
        return None

    text_value = (
        text_value
        .replace("kg", "")
        .replace("%", "")
        .replace(".", "")
        .replace(",", ".")
    )

    filtered = "".join(ch for ch in text_value if ch.isdigit() or ch in [".", "-"])
    if not filtered or filtered in ["-", ".", "-."]:
        return None

    try:
        return float(filtered)
    except ValueError:
        return None


def _infer_setor_tipo(codigo_setor):
    if not codigo_setor:
        return "interno"

    code = codigo_setor.upper()
    if "CANDIOTA" in code:
        return "destino"
    if "ACERTO" in code:
        return "ajuste"
    if "INTERNO" in code or "PATIO" in code:
        return "interno"
    return "coleta"


def _comparison_signature(source):
    data_hora = pd.to_datetime(source.get("data_hora"), errors="coerce")
    data_hora_key = None if pd.isna(data_hora) else data_hora.strftime("%Y-%m-%d %H:%M:%S")

    def _norm_text(value):
        if pd.isna(value) or value is None:
            return None
        return str(value).strip().lower()

    def _norm_float(value):
        if pd.isna(value) or value is None:
            return None
        return round(float(value), 3)

    return (
        data_hora_key,
        _norm_text(source.get("produto")),
        _norm_text(source.get("fornecedor_cliente")),
        _norm_text(source.get("setor")),
        _norm_float(source.get("peso_liquido")),
        _norm_float(source.get("peso_embalagem_liquido_corrigido")),
    )


def _generate_synthetic_ticket(row, used_tickets, conn):
    source_file = row.get("source_file") or "arquivo"
    original_ticket = row.get("ticket") or 0
    hash_seed = f"{source_file}|{original_ticket}|{row.get('data_hora')}"
    synthetic_seed = (zlib.crc32(str(hash_seed).encode("utf-8")) % 2_147_483_647) + 1
    new_ticket = -synthetic_seed

    while new_ticket in used_tickets or new_ticket < -2_147_483_648:
        new_ticket += 1
        if new_ticket == 0:
            new_ticket = -1

    while conn.execute(text("SELECT 1 FROM pesagem WHERE ticket = :ticket"), {"ticket": new_ticket}).scalar():
        new_ticket += 1
        if new_ticket == 0:
            new_ticket = -1

    used_tickets.add(new_ticket)
    return new_ticket


def _resolve_ticket_collisions(df):
    if df.empty or "ticket" not in df.columns or "source_file" not in df.columns:
        return df

    resolved = df.copy()
    valid_mask = resolved["ticket"].notna()
    collision_counts = resolved.loc[valid_mask, "ticket"].value_counts()
    colliding_tickets = collision_counts[collision_counts > 1].index.tolist()
    used_tickets = set(resolved.loc[valid_mask, "ticket"].dropna().astype(int).tolist())

    if not colliding_tickets:
        return resolved

    for ticket in colliding_tickets:
        ticket_mask = valid_mask & (resolved["ticket"] == ticket)
        duplicate_rows = resolved.loc[ticket_mask].copy()

        comparable_cols = [
            "data_hora", "produto", "fornecedor_cliente", "setor",
            "peso_liquido", "peso_embalagem_liquido_corrigido", "source_file",
        ]
        if duplicate_rows[comparable_cols].drop_duplicates().shape[0] <= 1:
            continue

        for idx, row in duplicate_rows.iloc[1:].iterrows():
            resolved.at[idx, "ticket"] = _generate_synthetic_ticket(row, used_tickets, _MemoryTicketLookup())

    return resolved


class _MemoryTicketLookup:
    def execute(self, *args, **kwargs):
        return _DummyScalar()


class _DummyScalar:
    def scalar(self):
        return None


def _resolve_ticket_collisions_against_database(df, conn):
    if df.empty or "ticket" not in df.columns:
        return df

    valid_tickets = [
        int(ticket)
        for ticket in df["ticket"].dropna().astype(int).tolist()
        if int(ticket) > 0
    ]
    if not valid_tickets:
        return df

    existing_rows = conn.execute(
        text(
            """
            SELECT
                ticket,
                data_hora,
                produto,
                fornecedor_cliente,
                setor,
                peso_liquido,
                peso_embalagem_liquido_corrigido
            FROM registro
            WHERE ticket IN :tickets
            """
        ).bindparams(bindparam("tickets", expanding=True)),
        {"tickets": sorted(set(valid_tickets))},
    ).mappings().all()

    if not existing_rows:
        return df

    existing_signatures = {}
    used_tickets = set(valid_tickets)
    for row in existing_rows:
        ticket = int(row["ticket"])
        existing_signatures.setdefault(ticket, set()).add(_comparison_signature(row))
        used_tickets.add(ticket)

    resolved = df.copy()
    for idx, row in resolved.iterrows():
        ticket = row.get("ticket")
        if pd.isna(ticket):
            continue

        ticket = int(ticket)
        if ticket <= 0 or ticket not in existing_signatures:
            continue

        incoming_signature = _comparison_signature(row)
        if incoming_signature in existing_signatures[ticket]:
            continue

        resolved.at[idx, "ticket"] = _generate_synthetic_ticket(row, used_tickets, conn)

    return resolved


def tratar_planilhas_para_carga(df):
    if df.empty:
        return df, {
            "rows_read": 0,
            "rows_valid": 0,
            "rows_rejected": 0,
            "rejections_by_reason": {},
        }

    treated = df.copy()

    for col in TEXT_COLUMNS:
        treated[col] = treated[col].apply(_normalize_text)

    treated["ticket"] = treated["ticket"].apply(_to_float)
    treated["ticket"] = treated["ticket"].apply(lambda v: int(v) if v is not None and float(v).is_integer() else None)
    treated["data_hora"] = pd.to_datetime(treated["data_hora"], errors="coerce", dayfirst=True)

    for col in WEIGHT_COLUMNS:
        treated[col] = treated[col].apply(_to_float)

    treated["diferenca_peso_porcentagem"] = treated["diferenca_peso_porcentagem"].apply(_to_float)
    treated["setor_tipo"] = treated["setor"].apply(_infer_setor_tipo)
    treated["veiculo_resolvido"] = treated["placa_veiculo"].fillna(treated["placa"])

    rejection_reasons = []
    required_missing = treated[REQUIRED_COLUMNS].isna().any(axis=1)
    invalid_ticket = treated["ticket"].isna() | (treated["ticket"] <= 0)
    invalid_date = treated["data_hora"].isna()

    for idx in treated.index:
        reasons = []
        if required_missing.loc[idx]:
            reasons.append("missing_required_fields")
        if invalid_ticket.loc[idx]:
            reasons.append("invalid_ticket")
        if invalid_date.loc[idx]:
            reasons.append("invalid_data_hora")

        for weight_col in [
            "peso_entrada", "peso_saida", "peso_liquido",
            "peso_embalagem_liquido", "peso_embalagem_liquido_corrigido", "peso_nota_fiscal",
        ]:
            value = treated.at[idx, weight_col]
            if value is not None and pd.notna(value) and value < 0:
                reasons.append(f"negative_{weight_col}")
                break

        rejection_reasons.append(";".join(sorted(set(reasons))) if reasons else "")

    treated["_rejection_reason"] = rejection_reasons
    rejected_mask = treated["_rejection_reason"] != ""

    valid_df = treated.loc[~rejected_mask].copy()
    valid_df = _resolve_ticket_collisions(valid_df)
    valid_df = valid_df.sort_values(["ticket", "data_hora"]).drop_duplicates(subset=["ticket"], keep="last")
    valid_df = valid_df.drop(columns=["_rejection_reason"])

    numeric_columns = WEIGHT_COLUMNS + ["diferenca_peso_porcentagem"]
    for column in numeric_columns:
        if column in valid_df.columns:
            valid_df[column] = pd.to_numeric(valid_df[column], errors="coerce").astype("Float64")

    if "ticket" in valid_df.columns:
        valid_df["ticket"] = pd.to_numeric(valid_df["ticket"], errors="coerce").astype("Int64")

    if "data_hora" in valid_df.columns:
        valid_df["data_hora"] = pd.to_datetime(valid_df["data_hora"], errors="coerce")

    rejection_counter = Counter()
    for raw_reasons in treated.loc[rejected_mask, "_rejection_reason"].tolist():
        for reason in raw_reasons.split(";"):
            if reason:
                rejection_counter[reason] += 1

    metrics = {
        "rows_read": len(df),
        "rows_valid": len(valid_df),
        "rows_rejected": int(rejected_mask.sum()),
        "rejections_by_reason": dict(rejection_counter),
    }

    return valid_df, metrics


def _ensure_audit_table_schema(conn):
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS import_auditoria (
                id SERIAL PRIMARY KEY,
                started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMP,
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                source_file VARCHAR(255),
                initiated_by VARCHAR(255),
                files_count INTEGER NOT NULL DEFAULT 0,
                rows_read INTEGER NOT NULL DEFAULT 0,
                rows_valid INTEGER NOT NULL DEFAULT 0,
                rows_new INTEGER NOT NULL DEFAULT 0,
                rows_updated INTEGER NOT NULL DEFAULT 0,
                deleted_rows INTEGER NOT NULL DEFAULT 0,
                deleted_at TIMESTAMP,
                deleted_by VARCHAR(255),
                details TEXT,
                error_message TEXT
            )
            """
        )
    )


def _ensure_pesagem_import_tracking(conn):
    conn.execute(text("ALTER TABLE pesagem ADD COLUMN IF NOT EXISTS import_audit_id INTEGER"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS started_at TIMESTAMP NOT NULL DEFAULT NOW()"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS finished_at TIMESTAMP"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'running'"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS source_file VARCHAR(255)"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS initiated_by VARCHAR(255)"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS files_count INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_read INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_valid INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_new INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_updated INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS deleted_rows INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(255)"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS details TEXT"))
    conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS error_message TEXT"))


def _start_audit(conn, source_file, initiated_by, files_count, rows_read):
    return conn.execute(
        text(
            """
            INSERT INTO import_auditoria (status, source_file, initiated_by, files_count, rows_read)
            VALUES ('running', :source_file, :initiated_by, :files_count, :rows_read)
            RETURNING id
            """
        ),
        {
            "source_file": source_file,
            "initiated_by": initiated_by,
            "files_count": files_count,
            "rows_read": rows_read,
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
            "finished_at": datetime.utcnow(),
            "status": status,
            "rows_valid": rows_valid,
            "rows_new": rows_new,
            "rows_updated": rows_updated,
            "details": details,
            "error_message": error_message,
            "audit_id": audit_id,
        },
    )


def _cleanup_processed_files(arquivos):
    for arquivo in arquivos:
        caminho = os.path.join(PASTA_PLANILHAS, arquivo)
        if os.path.exists(caminho):
            try:
                os.remove(caminho)
            except OSError:
                pass


def enviar_para_postgres(df, db_uri, arquivos, metrics, initiated_by):
    if df.empty:
        print("Nenhum dado valido para enviar ao banco.")
        return

    if not db_uri:
        raise RuntimeError("DATABASE_URL nao configurada no ambiente.")

    engine = create_engine(db_uri)

    with engine.begin() as conn:
        _ensure_audit_table_schema(conn)
        _ensure_pesagem_import_tracking(conn)
        audit_id = _start_audit(
            conn,
            source_file=", ".join(arquivos),
            initiated_by=initiated_by,
            files_count=len(arquivos),
            rows_read=metrics.get("rows_read", len(df)),
        )

    try:
        with engine.begin() as conn:
            df = _resolve_ticket_collisions_against_database(df, conn)
            before_count = conn.execute(text("SELECT COUNT(*) FROM pesagem")).scalar_one()

            staging = df[
                [
                    "ticket", "data_hora", "produto", "transportadora", "fornecedor_cliente",
                    "veiculo_resolvido", "setor", "setor_tipo", "peso_entrada", "peso_saida",
                    "peso_liquido", "peso_embalagem_liquido", "peso_embalagem_liquido_corrigido",
                    "peso_nota_fiscal", "diferenca_peso", "diferenca_peso_porcentagem",
                    "nro_nota_fiscal", "source_file",
                ]
            ].copy()

            staging_table = "staging_import_registro"
            conn.execute(text(f"DROP TABLE IF EXISTS {staging_table}"))
            staging.to_sql(staging_table, con=conn, if_exists="replace", index=False)

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
                    SET nome = EXCLUDED.nome,
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
                        nro_nota_fiscal,
                        import_audit_id
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
                        s.nro_nota_fiscal,
                        :audit_id
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
                        nro_nota_fiscal = EXCLUDED.nro_nota_fiscal,
                        import_audit_id = EXCLUDED.import_audit_id
                    """
                ),
                {"audit_id": audit_id},
            )

            conn.execute(text(f"DROP TABLE IF EXISTS {staging_table}"))
            after_count = conn.execute(text("SELECT COUNT(*) FROM pesagem")).scalar_one()

            rows_valid = len(df)
            rows_new = max(after_count - before_count, 0)
            rows_updated = max(rows_valid - rows_new, 0)
            rejections = metrics.get("rejections_by_reason", {})
            details = (
                f"Arquivo processado: {', '.join(arquivos)} | "
                f"Usuario responsavel: {initiated_by} | "
                f"Lidas: {metrics.get('rows_read', rows_valid)} | "
                f"Validas: {rows_valid} | "
                f"Rejeitadas: {metrics.get('rows_rejected', 0)} | "
                f"Motivos: {rejections}"
            )

            _finish_audit(
                conn,
                audit_id=audit_id,
                status="success",
                rows_valid=rows_valid,
                rows_new=rows_new,
                rows_updated=rows_updated,
                details=details,
            )

        _cleanup_processed_files(arquivos)
        print(
            "Importacao concluida com sucesso. "
            f"Registros validos: {rows_valid} | Novos: {rows_new} | Atualizados: {rows_updated}"
        )
    except Exception as exc:
        with engine.begin() as conn:
            _finish_audit(
                conn,
                audit_id=audit_id,
                status="error",
                rows_valid=0,
                rows_new=0,
                rows_updated=0,
                details=f"Arquivo processado: {', '.join(arquivos)} | Usuario responsavel: {initiated_by}",
                error_message=str(exc),
            )
        _cleanup_processed_files(arquivos)
        raise


def registrar_arquivo_sem_dados(db_uri, arquivo, metrics, initiated_by):
    if not db_uri:
        raise RuntimeError("DATABASE_URL nao configurada no ambiente.")

    engine = create_engine(db_uri)
    with engine.begin() as conn:
        _ensure_audit_table_schema(conn)
        _ensure_pesagem_import_tracking(conn)
        audit_id = _start_audit(
            conn,
            source_file=arquivo,
            initiated_by=initiated_by,
            files_count=1,
            rows_read=metrics.get("rows_read", 0),
        )
        _finish_audit(
            conn,
            audit_id=audit_id,
            status="error",
            rows_valid=0,
            rows_new=0,
            rows_updated=0,
            details=f"Arquivo processado: {arquivo} | Usuario responsavel: {initiated_by}",
            error_message="A planilha nao possui registros validos para importacao.",
        )
    _cleanup_processed_files([arquivo])


if __name__ == "__main__":
    if not os.path.exists(PASTA_PLANILHAS):
        print(f"Pasta '{PASTA_PLANILHAS}' nao existe.")
        raise SystemExit(1)

    arquivos = listar_arquivos_planilha(PASTA_PLANILHAS)
    if not arquivos:
        print("Nenhuma planilha valida foi carregada.")
        raise SystemExit(0)

    print(f"Encontrados {len(arquivos)} arquivos na pasta '{PASTA_PLANILHAS}':")
    for arquivo in arquivos:
        caminho = os.path.join(PASTA_PLANILHAS, arquivo)
        df_bruto = carregar_planilha_individual(caminho, arquivo)
        if df_bruto.empty:
            continue

        df_tratado, metrics = tratar_planilhas_para_carga(df_bruto)
        print(
            "Pre-processamento concluido. "
            f"Lidas: {metrics['rows_read']} | Validas: {metrics['rows_valid']} | "
            f"Rejeitadas: {metrics['rows_rejected']}"
        )
        if metrics["rejections_by_reason"]:
            print(f"Motivos de rejeicao: {metrics['rejections_by_reason']}")

        if df_tratado.empty:
            registrar_arquivo_sem_dados(DATABASE_URI, arquivo, metrics, IMPORT_INITIATED_BY)
            continue

        enviar_para_postgres(df_tratado, DATABASE_URI, [arquivo], metrics, IMPORT_INITIATED_BY)
