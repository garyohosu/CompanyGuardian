import logging
from datetime import datetime

from guardian.github_client import GitHubRepoClient
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

_FAILED_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}
logger = logging.getLogger(__name__)


class GithubActionsChecker:
    def __init__(self, github_client: GitHubRepoClient | None = None):
        self._github = github_client or GitHubRepoClient()

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        repo = company["repo"] if isinstance(company, dict) else company.repo
        workflow = company["workflow"] if isinstance(company, dict) else company.workflow
        repo_visibility = company["repo_visibility"] if isinstance(company, dict) else company.repo_visibility
        github_auth_required = company["github_auth_required"] if isinstance(company, dict) else company.github_auth_required
        auth_status = self._github.get_auth_status()
        logger.debug(
            "target=%s checker=github_actions repo=%s workflow=%s auth_mode=%s",
            company_id,
            repo,
            workflow,
            auth_status.mode,
        )

        if (github_auth_required or repo_visibility == "private") and auth_status.mode == "none":
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.GITHUB_ACTIONS,
                status=CheckStatus.WARNING,
                error_code=ErrorCode.GITHUB_AUTH_REQUIRED,
                detail="GitHub 認証が必要",
                checked_at=datetime.now(),
            )

        run = self._fetch_latest_run(repo, workflow)
        logger.debug("target=%s checker=github_actions latest_run=%s", company_id, run)

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

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.GITHUB_ACTIONS,
            status=CheckStatus.WARNING,
            error_code=None,
            detail=f"status={status}",
            checked_at=datetime.now(),
        )

    def _fetch_latest_run(self, repo: str, workflow: str) -> dict | None:
        return self._github.get_latest_workflow_run(repo, workflow)
