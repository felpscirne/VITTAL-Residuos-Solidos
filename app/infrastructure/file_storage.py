import base64
import os
import tempfile

import pandas as pd

from import_sheet import COLUMNS_NAMES, tratar_planilhas_para_carga


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

    def _validate_ods_file(self, path):
        try:
            df = pd.read_excel(path, engine='odf', skiprows=2)
            if df.shape[1] < len(COLUMNS_NAMES):
                return False, 'A planilha nao possui a estrutura esperada para importacao.'

            df = df.iloc[:, :len(COLUMNS_NAMES)].copy()
            df.columns = COLUMNS_NAMES
            df['source_file'] = os.path.basename(path)
            treated_df, metrics = tratar_planilhas_para_carga(df)
            if treated_df.empty or metrics.get('rows_valid', 0) == 0:
                return False, 'A planilha nao possui registros validos para importacao.'
            return True, None
        except Exception:
            return False, 'Falha ao validar a planilha enviada.'

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

            is_valid, validation_message = self._validate_ods_file(path)
            if not is_valid:
                if os.path.exists(path):
                    os.remove(path)
                return False, validation_message

            return True, f"Sucesso: '{filename}' enviado."
        except Exception:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return False, 'Falha ao salvar o arquivo enviado.'

    def save_uploaded_files(self, contents_list, filenames):
        contents_seq = contents_list if isinstance(contents_list, list) else [contents_list]
        filenames_seq = filenames if isinstance(filenames, list) else [filenames]

        saved = []
        errors = []
        for contents, filename in zip(contents_seq, filenames_seq):
            success, message = self.save_uploaded_file(contents, filename)
            if success:
                saved.append(filename)
            else:
                errors.append(f"{filename}: {message}")

        return {
            'saved': saved,
            'errors': errors,
        }

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

    def delete_files(self, filenames):
        removed = []
        failed = []
        for filename in filenames or []:
            if self.delete_file(filename):
                removed.append(filename)
            else:
                failed.append(filename)
        return {
            'removed': removed,
            'failed': failed,
        }
