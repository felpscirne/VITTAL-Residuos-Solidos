from app.services.error_messages import (
    get_safe_import_error_message,
    sanitize_audit_error_message,
)


def test_sanitize_audit_error_message_returns_empty_for_missing_message():
    assert sanitize_audit_error_message(None) == ""
    assert sanitize_audit_error_message("") == ""


def test_sanitize_audit_error_message_masks_sql_details():
    message = "psycopg.errors.SyntaxError: SELECT * FROM pesagem WHERE ticket = 1"

    assert sanitize_audit_error_message(message) == get_safe_import_error_message()


def test_sanitize_audit_error_message_truncates_non_sensitive_text():
    message = "Falha validada pelo operador. " * 20

    sanitized = sanitize_audit_error_message(message)

    assert sanitized == message[:240]
    assert len(sanitized) == 240
