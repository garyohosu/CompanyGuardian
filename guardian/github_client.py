import logging
import os

import requests

from guardian.github_auth import GitHubApiResponse, GitHubAuthResolver, GitHubAuthStatus

logger = logging.getLogger(__name__)


class GitHubRepoClient:
    def __init__(self, timeout: int = 15, auth: GitHubAuthResolver | None = None):
        self.timeout = timeout
        self._auth = auth or GitHubAuthResolver(timeout=timeout)

    def get_auth_status(self, refresh: bool = False) -> GitHubAuthStatus:
        return self._auth.get_auth_status(refresh=refresh)

    def log_auth_mode(self, logger_obj=None) -> GitHubAuthStatus:
        return self._auth.log_auth_mode(logger_obj or logger)

    def list_workflow_runs(self, repo: str, workflow: str | None = None, per_page: int = 3) -> list:
        if not repo:
            return []
        endpoint = self._workflow_runs_endpoint(repo, workflow)
        payload = self._request("GET", endpoint, params={"per_page": per_page})
        return list((payload or {}).get("workflow_runs", []) or [])

    def get_latest_workflow_run(self, repo: str, workflow: str | None = None) -> dict | None:
        runs = self.list_workflow_runs(repo, workflow=workflow, per_page=1)
        return runs[0] if runs else None

    def get_latest_commit(self, repo: str) -> dict | None:
        if not repo:
            return None
        payload = self._request(
            "GET",
            f"repos/{repo}/commits",
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
            f"repos/{repo}/actions/runs/{run_id}/jobs",
            params={"per_page": 100},
        )
        return list((payload or {}).get("jobs", []) or [])

    def rerun_failed_jobs(self, repo: str, run_id: int) -> tuple[bool, int]:
        response = self._request_response(
            "POST",
            f"repos/{repo}/actions/runs/{run_id}/rerun-failed-jobs",
        )
        return response.status_code in (201, 204), response.status_code

    def dispatch_workflow(self, repo: str, workflow: str, ref: str = "main") -> tuple[bool, int]:
        response = self._request_response(
            "POST",
            f"repos/{repo}/actions/workflows/{workflow}/dispatches",
            json={"ref": ref},
        )
        return response.status_code in (201, 204), response.status_code

    def get_repo_tree(self, repo: str, ref: str = "main") -> list:
        if not repo:
            return []
        payload = self._request(
            "GET",
            f"repos/{repo}/git/trees/{ref}",
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
        response = self._request_response(
            "GET",
            f"repos/{repo}/contents/{path.lstrip('/')}",
            params={"ref": ref},
            raw=True,
            accept="application/vnd.github.raw",
        )
        if response.status_code >= 400:
            return None
        return response.text

    def _workflow_runs_endpoint(self, repo: str, workflow: str | None) -> str:
        if workflow:
            return f"repos/{repo}/actions/workflows/{workflow}/runs"
        return f"repos/{repo}/actions/runs"

    def _headers(self, accept: str) -> dict:
        headers = {
            "Accept": accept,
            "User-Agent": "CompanyGuardian",
        }
        status = self.get_auth_status()
        if status.mode == "env_token":
            headers["Authorization"] = f"Bearer {os.environ.get('GITHUB_TOKEN', '')}"
        return headers

    def _request(self, method: str, endpoint: str, params: dict | None = None):
        response = self._request_response(method, endpoint, params=params)
        if response.status_code >= 400:
            logger.debug(
                "github request failed mode=%s method=%s endpoint=%s status=%s",
                self.get_auth_status().mode,
                method,
                endpoint,
                response.status_code,
            )
            return None
        try:
            return response.json()
        except Exception:
            return None

    def _request_response(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
        raw: bool = False,
        accept: str = "application/vnd.github+json",
    ) -> GitHubApiResponse:
        status = self.get_auth_status()
        logger.debug(
            "github request mode=%s method=%s endpoint=%s",
            status.mode,
            method,
            endpoint,
        )
        if status.mode == "gh_cli":
            return self._auth.run_gh_api(
                method=method,
                endpoint=endpoint,
                params=params,
                json_body=json,
                accept=accept,
            )

        url = f"https://api.github.com/{endpoint.lstrip('/')}"
        try:
            response = requests.request(
                method,
                url,
                headers=self._headers(accept),
                params=params,
                json=json,
                timeout=self.timeout,
            )
        except Exception as exc:
            return GitHubApiResponse(status_code=599, text=str(exc))

        json_data = None
        if not raw:
            try:
                json_data = response.json()
            except Exception:
                json_data = None
        return GitHubApiResponse(
            status_code=response.status_code,
            text=response.text,
            json_data=json_data,
        )
