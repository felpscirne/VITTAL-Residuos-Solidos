import base64
import os


class LocalFileStorageAdapter:
    def __init__(self, sheets_folder='sheets'):
        self._sheets_folder = sheets_folder

    def _ensure_sheets_folder(self):
        if not os.path.exists(self._sheets_folder):
            os.makedirs(self._sheets_folder, exist_ok=True)

    def list_files(self):
        self._ensure_sheets_folder()

        files = []
        for file_name in os.listdir(self._sheets_folder):
            if file_name.endswith('.ods') and not file_name.startswith('~'):
                path = os.path.join(self._sheets_folder, file_name)
                try:
                    size = os.path.getsize(path) / 1024
                    files.append({'filename': file_name, 'size': f'{size:.2f} KB'})
                except OSError:
                    continue

        return sorted(files, key=lambda x: x['filename'])

    def save_uploaded_file(self, contents, filename):
        if not filename or not filename.lower().endswith('.ods'):
            return False, 'Apenas arquivos .ods permitidos.'

        self._ensure_sheets_folder()

        path = os.path.join(self._sheets_folder, filename)
        if os.path.exists(path):
            return False, f"O arquivo '{filename}' ja existe. Exclua antes de enviar novamente."

        try:
            _, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            with open(path, 'wb') as file_obj:
                file_obj.write(decoded)
            return True, f"Sucesso: '{filename}' enviado."
        except Exception as e:
            return False, f'Erro ao salvar: {str(e)}'

    def delete_file(self, filename):
        if not filename:
            return False

        path = os.path.join(self._sheets_folder, filename)
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception:
            return False

        return False
