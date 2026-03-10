import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GitHubAuthStatus:
    mode: str
    detail: str = ""


@dataclass
class GitHubApiResponse:
    status_code: int
    text: str = ""
    json_data: object | None = None

    def json(self):
        if self.json_data is not None:
            return self.json_data
        if not self.text:
            return {}
        return json.loads(self.text)


class GitHubAuthResolver:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._status_cache: GitHubAuthStatus | None = None

    def get_auth_status(self, refresh: bool = False) -> GitHubAuthStatus:
        if refresh or self._status_cache is None:
            self._status_cache = self._detect_auth_status()
        return self._status_cache

    def log_auth_mode(self, logger_obj=None) -> GitHubAuthStatus:
        log = logger_obj or logger
        status = self.get_auth_status()
        detail_part = f" detail=\"{status.detail}\"" if status.detail else ""
        if status.mode == "none":
            log.warning("github auth mode=%s%s", status.mode, detail_part)
        else:
            log.info("github auth mode=%s%s", status.mode, detail_part)
        return status

    def run_gh_api(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_body: dict | None = None,
        accept: str = "application/vnd.github+json",
    ) -> GitHubApiResponse:
        gh = shutil.which("gh")
        if not gh:
            return GitHubApiResponse(status_code=599, text="")

        command = [
            gh,
            "api",
            endpoint.lstrip("/"),
            "--hostname",
            "github.com",
            "--method",
            method.upper(),
            "--include",
        ]
        if accept:
            command += ["-H", f"Accept: {accept}"]

        for key, value in (params or {}).items():
            command += ["-f", f"{key}={self._stringify(value)}"]
        for key, value in (json_body or {}).items():
            command += ["-f", f"{key}={self._stringify(value)}"]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except Exception as exc:
            return GitHubApiResponse(status_code=599, text=str(exc))

        return self._parse_gh_api_response(completed)

    def _detect_auth_status(self) -> GitHubAuthStatus:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            return GitHubAuthStatus(mode="env_token")

        gh = shutil.which("gh")
        if not gh:
            return GitHubAuthStatus(mode="none", detail="gh not installed")

        try:
            completed = subprocess.run(
                [gh, "auth", "status", "--hostname", "github.com"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except Exception as exc:
            return GitHubAuthStatus(mode="none", detail=f"gh auth status failed: {exc}")

        if completed.returncode == 0:
            return GitHubAuthStatus(mode="gh_cli")

        detail = self._first_line(completed.stderr or completed.stdout)
        return GitHubAuthStatus(mode="none", detail=detail or "gh auth status failed")

    def _parse_gh_api_response(self, completed: subprocess.CompletedProcess) -> GitHubApiResponse:
        raw_output = completed.stdout or ""
        body = raw_output
        parts = re.split(r"\r?\n\r?\n", raw_output, maxsplit=1)
        if len(parts) == 2:
            body = parts[1]

        status_code = self._extract_status_code(raw_output)
        if status_code is None:
            status_code = self._extract_status_code(completed.stderr or "")
        if status_code is None:
            status_code = 200 if completed.returncode == 0 else 599

        json_data = None
        try:
            json_data = json.loads(body) if body else {}
        except Exception:
            json_data = None
        return GitHubApiResponse(status_code=status_code, text=body, json_data=json_data)

    def _extract_status_code(self, text: str) -> int | None:
        if not text:
            return None
        match = re.search(r"HTTP/\S+\s+(\d{3})", text)
        if match:
            return int(match.group(1))
        match = re.search(r"\(HTTP (\d{3})\)", text)
        if match:
            return int(match.group(1))
        return None

    def _first_line(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return ""
        return cleaned.splitlines()[0].strip()

    def _stringify(self, value) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
