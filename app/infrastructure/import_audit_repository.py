import pandas as pd

from app.database import engine
from app.services.error_messages import sanitize_audit_error_message


class SqlImportAuditRepositoryAdapter:
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
            COALESCE(error_message, '') AS error_message
        FROM import_auditoria
        ORDER BY id DESC
        LIMIT 20
        """
        try:
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
