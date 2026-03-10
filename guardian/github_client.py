import os

import requests


class GitHubRepoClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def list_workflow_runs(self, repo: str, workflow: str | None = None, per_page: int = 3) -> list:
        if not repo:
            return []
        url = self._workflow_runs_url(repo, workflow)
        payload = self._request("GET", url, params={"per_page": per_page})
        return list((payload or {}).get("workflow_runs", []) or [])

    def get_latest_workflow_run(self, repo: str, workflow: str | None = None) -> dict | None:
        runs = self.list_workflow_runs(repo, workflow=workflow, per_page=1)
        return runs[0] if runs else None

    def get_latest_commit(self, repo: str) -> dict | None:
        if not repo:
            return None
        payload = self._request(
            "GET",
            f"https://api.github.com/repos/{repo}/commits",
            params={"per_page": 1},
        )
        if isinstance(payload, list) and payload:
            return payload[0]
        return None

    def get_run_jobs(self, repo: str, run_id: int) -> list:
        if not repo or not run_id:
            return []
        payload = self._request(
            "GET",
            f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs",
            params={"per_page": 100},
        )
        return list((payload or {}).get("jobs", []) or [])

    def rerun_failed_jobs(self, repo: str, run_id: int) -> tuple[bool, int]:
        response = self._request_response(
            "POST",
            f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/rerun-failed-jobs",
        )
        return response.status_code in (201, 204), response.status_code

    def dispatch_workflow(self, repo: str, workflow: str, ref: str = "main") -> tuple[bool, int]:
        response = self._request_response(
            "POST",
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches",
            json={"ref": ref},
        )
        return response.status_code in (201, 204), response.status_code

    def get_repo_tree(self, repo: str, ref: str = "main") -> list:
        if not repo:
            return []
        payload = self._request(
            "GET",
            f"https://api.github.com/repos/{repo}/git/trees/{ref}",
            params={"recursive": 1},
        )
        return list((payload or {}).get("tree", []) or [])

    def path_exists(self, repo: str, path: str, ref: str = "main") -> bool:
        if not path:
            return False
        normalized = path.strip("/")
        for item in self.get_repo_tree(repo, ref=ref):
            if str(item.get("path", "")).strip("/") == normalized:
                return True
        return False

    def path_prefix_exists(self, repo: str, prefix: str, ref: str = "main") -> bool:
        if not prefix:
            return False
        normalized = prefix.strip("/")
        for item in self.get_repo_tree(repo, ref=ref):
            if str(item.get("path", "")).strip("/").startswith(normalized):
                return True
        return False

    def get_raw_text(self, repo: str, path: str, ref: str = "main") -> str | None:
        if not repo or not path:
            return None
        url = f"https://raw.githubusercontent.com/{repo}/{ref}/{path.lstrip('/')}"
        response = self._request_response("GET", url, raw=True, allow_404=True)
        if response.status_code >= 400:
            return None
        return response.text

    def _workflow_runs_url(self, repo: str, workflow: str | None) -> str:
        if workflow:
            return f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs"
        return f"https://api.github.com/repos/{repo}/actions/runs"

    def _headers(self) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CompanyGuardian",
        }
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(self, method: str, url: str, params: dict | None = None):
        response = self._request_response(method, url, params=params)
        if response.status_code >= 400:
            return None
        try:
            return response.json()
        except Exception:
            return None

    def _request_response(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json: dict | None = None,
        raw: bool = False,
        allow_404: bool = False,
    ):
        try:
            response = requests.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json,
                timeout=self.timeout,
            )
        except Exception:
            response = requests.Response()
            response.status_code = 599
            response._content = b""
            return response
        if response.status_code >= 400 and not (allow_404 and response.status_code == 404):
            return response
        return response
