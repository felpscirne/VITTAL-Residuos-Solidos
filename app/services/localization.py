ROLE_LABELS = {
    "anonymous": "Sem login",
    "student": "Estudantil",
    "operator": "Operador",
    "management": "Gestão",
}


IMPORT_STATUS_LABELS = {
    "running": "Em andamento",
    "success": "Concluída",
    "error": "Falhou",
    "deleted": "Excluída",
}


def get_role_label(role_name: str | None) -> str:
    if not role_name:
        return "Perfil"
    return ROLE_LABELS.get(role_name, role_name.replace("_", " ").capitalize())


def get_import_status_label(status: str | None) -> str:
    if not status:
        return "Não informado"
    return IMPORT_STATUS_LABELS.get(status, status.replace("_", " ").capitalize())
