import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GitPusher:

    def push_outputs(self, files: list) -> bool:
        try:
            self._git_add(files)
            message = f"CompanyGuardian: {datetime.now().strftime('%Y-%m-%d')} 自動記録"
            self._git_commit(message)
            return self._git_push()
        except Exception as e:
            logger.error(f"git push 失敗: {e}")
            return False

    def _git_add(self, files: list) -> None:
        subprocess.run(["git", "add"] + files, check=True)

    def _git_commit(self, message: str) -> None:
        subprocess.run(["git", "commit", "-m", message], check=True)

    def _git_push(self) -> bool:
        result = subprocess.run(["git", "push"], capture_output=True)
        return result.returncode == 0
