def get_safe_import_error_message() -> str:
    return (
        "Falha ao processar a importacao. Consulte os logs internos do servidor "
        "ou o historico de auditoria para detalhes tecnicos."
    )


def get_safe_database_error_message() -> str:
    return "Falha ao acessar ou salvar dados. Tente novamente e, se persistir, verifique os logs internos."


def sanitize_audit_error_message(message: str | None) -> str:
    if not message:
        return ""

    lowered = message.lower()
    sensitive_markers = [
        "select ",
        "insert ",
        "update ",
        "delete ",
        "from ",
        "where ",
        "join ",
        "sql",
        "psycopg",
        "traceback",
        "syntax error",
        "relation ",
        "column ",
        "table ",
    ]
    if any(marker in lowered for marker in sensitive_markers):
        return get_safe_import_error_message()

    return message[:240]
