from typing import Protocol


class FileStoragePort(Protocol):
    def list_files(self):
        ...

    def save_uploaded_file(self, contents, filename):
        ...

    def delete_file(self, filename):
        ...


class EtlRunnerPort(Protocol):
    def start_etl_async(self):
        ...

    def get_etl_status(self):
        ...


class ImportAuditRepositoryPort(Protocol):
    def list_import_audit(self):
        ...


class FileManagementService:
    def __init__(self, file_storage: FileStoragePort, etl_runner: EtlRunnerPort, audit_repository: ImportAuditRepositoryPort):
        self._file_storage = file_storage
        self._etl_runner = etl_runner
        self._audit_repository = audit_repository

    def list_files(self):
        return self._file_storage.list_files()

    def save_uploaded_file(self, contents, filename):
        return self._file_storage.save_uploaded_file(contents, filename)

    def delete_file(self, filename):
        return self._file_storage.delete_file(filename)

    def start_etl_async(self):
        return self._etl_runner.start_etl_async()

    def get_etl_status(self):
        return self._etl_runner.get_etl_status()

    def list_import_audit(self):
        return self._audit_repository.list_import_audit()


def build_default_file_management_service():
    from app.infrastructure.etl_runner import SubprocessEtlRunnerAdapter
    from app.infrastructure.file_storage import LocalFileStorageAdapter
    from app.infrastructure.import_audit_repository import SqlImportAuditRepositoryAdapter

    return FileManagementService(
        file_storage=LocalFileStorageAdapter(),
        etl_runner=SubprocessEtlRunnerAdapter(),
        audit_repository=SqlImportAuditRepositoryAdapter(),
    )
