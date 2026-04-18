import os
import subprocess
import sys
import threading
from app.services.error_messages import get_safe_import_error_message


class SubprocessEtlRunnerAdapter:
    def __init__(self):
        self._status = {
            'is_running': False,
            'message': '',
            'color': 'gray',
        }

    def _run_import_script(self, initiated_by=None):
        self._status['is_running'] = True
        self._status['message'] = 'Processando arquivos enviados... Isso pode levar alguns minutos.'
        self._status['color'] = 'blue'

        try:
            env = os.environ.copy()
            if initiated_by:
                env['IMPORT_INITIATED_BY'] = initiated_by
            result = subprocess.run(
                [
                    sys.executable,
                    '-c',
                    (
                        'import os; '
                        'from app.services.import_pipeline import run_pending_imports; '
                        'raise SystemExit('
                        'run_pending_imports('
                        'sheets_folder="sheets", '
                        'initiated_by=os.getenv("IMPORT_INITIATED_BY", "Sistema")'
                        ')'
                        ')'
                    ),
                ],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                env=env,
            )

            if result.returncode == 0:
                self._status['message'] = 'Processamento finalizado. Consulte o historico para ver quais arquivos concluiram ou falharam.'
                self._status['color'] = 'green'
            elif result.returncode == 2:
                self._status['message'] = 'Processamento finalizado com alguns arquivos falhando. Consulte o historico para detalhes.'
                self._status['color'] = 'yellow'
            else:
                self._status['message'] = get_safe_import_error_message()
                self._status['color'] = 'red'
        except Exception:
            self._status['message'] = get_safe_import_error_message()
            self._status['color'] = 'red'
        finally:
            self._status['is_running'] = False

    def start_etl_async(self, initiated_by=None):
        if self._status['is_running']:
            return False

        thread = threading.Thread(target=self._run_import_script, kwargs={'initiated_by': initiated_by}, daemon=True)
        thread.start()
        return True

    def get_etl_status(self):
        return self._status['is_running'], self._status['message'], self._status['color']
