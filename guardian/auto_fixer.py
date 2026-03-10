import os
import shutil
import logging
from guardian.models import AutoFixResult
from guardian.github_client import GitHubRepoClient

logger = logging.getLogger(__name__)

# このセッションで再試行済みの (repo, run_id) を記録
_retried_runs: set = set()

# 再試行対象の conclusion（failure のみ）
_RETRYABLE_CONCLUSIONS = {"failure"}


class AutoFixer:
    """低リスクな自動修正を実施するクラス。"""

    def __init__(self, github_client: GitHubRepoClient | None = None):
        self._github = github_client or GitHubRepoClient()

    def fix_readme_if_needed(self) -> AutoFixResult | None:
        """README.md が無く README.txt がある場合、コピーして修正する。

        Returns:
            AutoFixResult if fix was attempted, None if no fix needed.
        """
        readme_md = "README.md"
        readme_txt = "README.txt"

        if os.path.exists(readme_md):
            return None  # 修正不要

        if not os.path.exists(readme_txt):
            return None  # README.txt もないので対処不能

        try:
            shutil.copy2(readme_txt, readme_md)
            logger.info("[AUTO_FIX] README.txt → README.md コピー完了")
            return AutoFixResult(
                target_id="company-guardian",
                fix_kind="readme_copy",
                status="OK",
                message="README.txt を README.md にコピーして自己監視前提を修正",
                changed_files=[readme_md],
            )
        except Exception as e:
            logger.error(f"[AUTO_FIX] README コピー失敗: {e}")
            return AutoFixResult(
                target_id="company-guardian",
                fix_kind="readme_copy",
                status="FAIL",
                message=f"README.txt → README.md コピー失敗: {e}",
                changed_files=[],
            )

    def retry_github_actions_if_applicable(
        self, company_id: str, repo: str
    ) -> AutoFixResult | None:
        """github_actions failure の低リスク再試行（1 run につき 1 回限り）。

        再試行しない条件:
        - repo 未設定
        - GitHub 認証手段なし
        - 最新 run が取得できない
        - conclusion が failure 以外（cancelled, timed_out, action_required 等）
        - 同一 run_id を既に再試行済み

        Returns:
            AutoFixResult, or None if no applicable error found.
        """
        if not repo:
            return AutoFixResult(
                target_id=company_id,
                fix_kind="github_actions_retry",
                status="SKIP",
                message="repo 未設定のため再試行スキップ",
            )

        auth_status = self._github.get_auth_status()
        logger.info(
            "target=%s autofix start fix=github_actions_retry repo=%s auth_mode=%s",
            company_id,
            repo,
            auth_status.mode,
        )
        if auth_status.mode == "none":
            return AutoFixResult(
                target_id=company_id,
                fix_kind="github_actions_retry",
                status="SKIP",
                message="GitHub 認証手段なし (auth=none) のため再試行スキップ",
                context={"auth_mode": auth_status.mode},
            )

        run = self._fetch_latest_run(repo)
        if run is None:
            return AutoFixResult(
                target_id=company_id,
                fix_kind="github_actions_retry",
                status="SKIP",
                message="最新 run 取得失敗のためスキップ",
                context={"auth_mode": auth_status.mode},
            )

        conclusion = run.get("conclusion")
        run_id = run.get("id")

        if conclusion not in _RETRYABLE_CONCLUSIONS:
            return AutoFixResult(
                target_id=company_id,
                fix_kind="github_actions_retry",
                status="SKIP",
                message=f"conclusion={conclusion} は再試行対象外（failure のみ対象）",
                context={"auth_mode": auth_status.mode},
            )

        key = (repo, run_id)
        if key in _retried_runs:
            return AutoFixResult(
                target_id=company_id,
                fix_kind="github_actions_retry",
                status="SKIP",
                message=f"run_id={run_id} は既に再試行済みのためスキップ",
                context={"auth_mode": auth_status.mode},
            )

        try:
            ok, status_code = self._github.rerun_failed_jobs(repo, int(run_id))
            _retried_runs.add(key)

            if ok:
                logger.info(
                    "[AUTO_FIX] %s run_id=%s 再試行リクエスト送信 auth_mode=%s",
                    company_id,
                    run_id,
                    auth_status.mode,
                )
                return AutoFixResult(
                    target_id=company_id,
                    fix_kind="github_actions_retry",
                    status="WARN",
                    message=(
                        f"{company_id} workflow を 1 回再試行したが失敗継続かは未確定"
                        f" (run_id={run_id}, auth={auth_status.mode})"
                    ),
                    context={"auth_mode": auth_status.mode, "http_status": status_code},
                )
            else:
                return AutoFixResult(
                    target_id=company_id,
                    fix_kind="github_actions_retry",
                    status="FAIL",
                    message=f"run_id={run_id} 再試行 API 失敗: HTTP {status_code} (auth={auth_status.mode})",
                    context={"auth_mode": auth_status.mode, "http_status": status_code},
                )
        except Exception as e:
            return AutoFixResult(
                target_id=company_id,
                fix_kind="github_actions_retry",
                status="FAIL",
                message=f"run_id={run_id} 再試行例外: {e} (auth={auth_status.mode})",
                context={"auth_mode": auth_status.mode},
            )

    def _fetch_latest_run(self, repo: str) -> dict | None:
        return self._github.get_latest_workflow_run(repo)
