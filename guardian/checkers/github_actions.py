import os
import requests
from datetime import datetime
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

_FAILED_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}
_PENDING_STATUSES = {"in_progress", "queued", "waiting", "requested"}


class GithubActionsChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        repo = company["repo"] if isinstance(company, dict) else company.repo
        workflow = company["workflow"] if isinstance(company, dict) else company.workflow
        repo_visibility = company["repo_visibility"] if isinstance(company, dict) else company.repo_visibility
        github_auth_required = company["github_auth_required"] if isinstance(company, dict) else company.github_auth_required
        token = os.environ.get("GITHUB_TOKEN", "")

        if (github_auth_required or repo_visibility == "private") and not token:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.GITHUB_ACTIONS,
                status=CheckStatus.WARNING,
                error_code=ErrorCode.GITHUB_AUTH_REQUIRED,
                detail="GitHub 認証が必要",
                checked_at=datetime.now(),
            )

        run = self._fetch_latest_run(repo, workflow)

        if run is None:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.GITHUB_ACTIONS,
                status=CheckStatus.WARNING,
                error_code=None,
                detail="実行履歴なし",
                checked_at=datetime.now(),
            )

        conclusion = run.get("conclusion")
        status = run.get("status")

        if conclusion == "success":
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.GITHUB_ACTIONS,
                status=CheckStatus.OK,
                error_code=None,
                detail=f"conclusion={conclusion}",
                checked_at=datetime.now(),
            )

        if conclusion in _FAILED_CONCLUSIONS:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.GITHUB_ACTIONS,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.ACTION_FAILED,
                detail=f"conclusion={conclusion}",
                checked_at=datetime.now(),
            )

        # in_progress / queued / no conclusion
        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.GITHUB_ACTIONS,
            status=CheckStatus.WARNING,
            error_code=None,
            detail=f"status={status}",
            checked_at=datetime.now(),
        )

    def _fetch_latest_run(self, repo: str, workflow: str) -> dict:
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        params = {"per_page": 1}
        if workflow:
            url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs"
        else:
            url = f"https://api.github.com/repos/{repo}/actions/runs"

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            runs = data.get("workflow_runs", [])
            return runs[0] if runs else None
        except Exception:
            return None
