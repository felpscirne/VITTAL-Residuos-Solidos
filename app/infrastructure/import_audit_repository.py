import pandas as pd
from sqlalchemy import text

from app.database import engine
from app.extensions import cache
from app.services.error_messages import sanitize_audit_error_message


class SqlImportAuditRepositoryAdapter:
    def _ensure_audit_table_schema(self):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS import_auditoria (
                        id SERIAL PRIMARY KEY,
                        started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        finished_at TIMESTAMP,
                        status VARCHAR(20) NOT NULL DEFAULT 'running',
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
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS started_at TIMESTAMP NOT NULL DEFAULT NOW()"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS finished_at TIMESTAMP"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'running'"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS files_count INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_read INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_valid INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_new INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS rows_updated INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS details TEXT"))
            conn.execute(text("ALTER TABLE import_auditoria ADD COLUMN IF NOT EXISTS error_message TEXT"))

    def list_import_audit(self):
        query = """
        SELECT
            id,
            started_at,
            finished_at,
            status,
            files_count,
            rows_read,
            rows_valid,
            rows_new,
            rows_updated,
            COALESCE(details, '') AS details,
            COALESCE(error_message, '') AS error_message
        FROM import_auditoria
        ORDER BY id DESC
        LIMIT 20
        """
        try:
            self._ensure_audit_table_schema()
            df = pd.read_sql(query, engine)
            if df.empty:
                return []

            for col in ['started_at', 'finished_at']:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
                df[col] = df[col].fillna('')

            df["error_message"] = df["error_message"].apply(sanitize_audit_error_message)

            return df.to_dict('records')
        except Exception:
            return []

    def delete_imported_data(self, audit_id):
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        DELETE FROM pesagem
                        WHERE import_audit_id = :audit_id
                        """
                    ),
                    {'audit_id': audit_id},
                )
                cache.clear()
                return result.rowcount or 0
        except Exception:
            return 0

    def reset_import_data(self):
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        TRUNCATE TABLE pesagem, produto, empresa, veiculo, setor, import_auditoria
                        RESTART IDENTITY CASCADE
                        """
                    )
                )
            cache.clear()
            return True
        except Exception:
            return False
