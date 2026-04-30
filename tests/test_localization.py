from app.services.localization import get_import_status_label, get_role_label


def test_get_role_label_handles_known_empty_and_unknown_roles():
    assert get_role_label("management") == "Gestão"
    assert get_role_label(None) == "Perfil"
    assert get_role_label("custom_role") == "Custom role"


def test_get_import_status_label_handles_known_empty_and_unknown_statuses():
    assert get_import_status_label("success") == "Concluída"
    assert get_import_status_label("") == "Não informado"
    assert get_import_status_label("waiting_review") == "Waiting review"
