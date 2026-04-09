import os
import subprocess
import sys
import threading


class SubprocessEtlRunnerAdapter:
    def __init__(self, script_name='import_sheet.py'):
        self._script_name = script_name
        self._status = {
            'is_running': False,
            'message': '',
            'color': 'gray',
        }

    def _run_import_script(self):
        self._status['is_running'] = True
        self._status['message'] = 'O script de importacao esta rodando... Isso pode levar alguns minutos.'
        self._status['color'] = 'blue'

        try:
            result = subprocess.run(
                [sys.executable, self._script_name],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
            )

            if result.returncode == 0:
                self._status['message'] = 'Sucesso! Importacao concluida.'
                self._status['color'] = 'green'
            else:
                stderr_output = (result.stderr or '').strip()
                self._status['message'] = f'Erro na execucao:\n{stderr_output}'
                self._status['color'] = 'red'
        except Exception as e:
            self._status['message'] = f'Erro critico ao tentar rodar o script: {str(e)}'
            self._status['color'] = 'red'
        finally:
            self._status['is_running'] = False

    def start_etl_async(self):
        if self._status['is_running']:
            return False

        thread = threading.Thread(target=self._run_import_script, daemon=True)
        thread.start()
        return True

    def get_etl_status(self):
        return self._status['is_running'], self._status['message'], self._status['color']
