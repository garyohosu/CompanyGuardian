import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GitPusher:

    def push_outputs(self, files: list) -> bool:
        if not files:
            logger.info("git add targets=none commit=skip push=skip")
            return True
        try:
            logger.info("git add targets=%s", ",".join(files))
            self._git_add(files)
            message = f"CompanyGuardian: {datetime.now().strftime('%Y-%m-%d')} 自動記録"
            committed = self._git_commit(message)
            if committed:
                logger.info("git commit result=OK message=\"%s\"", message)
                pushed = self._git_push()
                logger.info("git push result=%s", "OK" if pushed else "FAIL")
                return pushed
            logger.info("git commit result=SKIP message=\"nothing to commit\"")
            return True
        except Exception as e:
            logger.error("git push failed message=\"%s\"", e, exc_info=True)
            return False

    def _git_add(self, files: list) -> None:
        subprocess.run(["git", "add"] + files, check=True)

    def _git_commit(self, message: str) -> bool:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True
        combined = f"{result.stdout}\n{result.stderr}".strip().lower()
        if "nothing to commit" in combined or "no changes added to commit" in combined:
            return False
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )

    def _git_push(self) -> bool:
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(
                "git push stderr=\"%s\"",
                (result.stderr or result.stdout or "").strip(),
            )
        return result.returncode == 0
