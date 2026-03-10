import json
import logging
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

from guardian.github_client import GitHubRepoClient
from guardian.models import CheckKind, CheckResult, ContentIncidentAnalysis, ErrorCode

logger = logging.getLogger(__name__)


class ContentIncidentAnalyzer:
    def __init__(self):
        self._github = GitHubRepoClient()

    def analyze(self, company, result: CheckResult) -> ContentIncidentAnalysis:
        logger.info(
            "target=%s analyzer start code=%s check=%s",
            result.company_id,
            result.error_code.value if result.error_code else "",
            result.check_kind.value.lower(),
        )
        if result.error_code in (ErrorCode.STALE_CONTENT, ErrorCode.DAILY_POST_MISSING):
            analysis = self._analyze_daily_issue(company, result)
        elif result.error_code == ErrorCode.DUPLICATE_CONTENT:
            analysis = self._analyze_duplicate_issue(company, result)
        elif result.error_code == ErrorCode.SERIAL_STALLED:
            analysis = self._analyze_serial_issue(company, result)
        else:
            analysis = ContentIncidentAnalysis(
                company_id=result.company_id,
                error_code=result.error_code,
                cause_code="UNKNOWN_CAUSE",
                cause_summary="content incident analyzer 対象外",
                recommended_fix="手動調査",
                diagnostics={},
            )
        logger.info(
            "target=%s analyzer result cause_code=%s summary=\"%s\"",
            result.company_id,
            analysis.cause_code,
            analysis.cause_summary,
        )
        logger.debug("target=%s analyzer diagnostics=%s", result.company_id, analysis.diagnostics)
        return analysis

    def _analyze_daily_issue(self, company, result: CheckResult) -> ContentIncidentAnalysis:
        repo = self._value(company, "repo")
        workflow = self._rule(company, result).get("workflow") or self._value(company, "workflow")
        deploy_workflow = self._rule(company, result).get("deploy_workflow")
        latest_run = self._github.get_latest_workflow_run(repo, workflow)
        recent_runs = self._github.list_workflow_runs(repo, workflow, per_page=5)
        latest_success = next((run for run in recent_runs if run.get("conclusion") == "success"), None)
        latest_commit = self._github.get_latest_commit(repo)
        expected_date = self._expected_date(result)
        repo_path = self._format_repo_path(self._rule(company, result), expected_date)
        repo_prefix = self._format_repo_prefix(self._rule(company, result), expected_date)
        repo_content_exists = self._repo_content_exists(repo, repo_path, repo_prefix)
        failure_summary = self._failure_summary(repo, latest_run)

        cause_code = "UNKNOWN_CAUSE"
        recommended_fix = "workflow / deploy / content source を手動確認"
        suggested_action = None

        if latest_run and latest_run.get("conclusion") == "failure":
            cause_code = "WORKFLOW_FAILED"
            recommended_fix = "workflow を 1 回 rerun"
            suggested_action = "rerun_failed_jobs"
        elif latest_run is None or self._is_run_stale(latest_run, expected_date):
            cause_code = "WORKFLOW_NOT_RUNNING"
            recommended_fix = "workflow_dispatch で 1 回再実行"
            suggested_action = "dispatch_workflow"
        elif repo_content_exists is False:
            cause_code = "CONTENT_NOT_GENERATED"
            recommended_fix = "生成ロジックまたは入力不足を確認し、必要なら workflow を再実行"
        elif repo_content_exists is True:
            cause_code = "CONTENT_NOT_DEPLOYED"
            recommended_fix = "deploy workflow を 1 回再実行"
            suggested_action = "dispatch_deploy"
        elif latest_success and latest_commit:
            cause_code = "SITE_CONFIG_MISMATCH"
            recommended_fix = "CompanyGuardian の latest post 判定設定を見直す"

        summary = self._join_non_empty(
            [
                f"latest_run={self._run_brief(latest_run)}" if latest_run else "latest_run=none",
                f"latest_success={latest_success.get('updated_at')}" if latest_success else "latest_success=none",
                f"latest_commit={self._commit_date(latest_commit)}" if latest_commit else "latest_commit=none",
                f"site_latest={result.context.get('latest_date', '') or 'unknown'}",
                f"repo_content_exists={repo_content_exists}" if (repo_path or repo_prefix) else "",
                failure_summary,
            ]
        )
        return ContentIncidentAnalysis(
            company_id=result.company_id,
            error_code=result.error_code,
            cause_code=cause_code,
            cause_summary=summary,
            recommended_fix=recommended_fix,
            diagnostics={
                "repo": repo,
                "workflow": workflow,
                "deploy_workflow": deploy_workflow,
                "latest_run": latest_run,
                "latest_success": latest_success,
                "latest_commit": latest_commit,
                "repo_content_exists": repo_content_exists,
                "repo_path": repo_path,
                "repo_prefix": repo_prefix,
                "failure_summary": failure_summary,
                "suggested_action": suggested_action,
            },
        )

    def _analyze_duplicate_issue(self, company, result: CheckResult) -> ContentIncidentAnalysis:
        repo = self._value(company, "repo")
        rule = self._rule(company, result)
        workflow = rule.get("workflow") or self._value(company, "workflow")
        deploy_workflow = rule.get("deploy_workflow")
        duplicate_fields = list(result.context.get("duplicate_fields", []) or [])
        latest_url = result.context.get("latest_url", "")
        previous_url = result.context.get("previous_url", "")
        latest_repo_path = self._site_url_to_repo_path(company, latest_url)
        previous_repo_path = self._site_url_to_repo_path(company, previous_url)
        latest_exists = self._github.path_exists(repo, latest_repo_path) if latest_repo_path else None
        previous_exists = self._github.path_exists(repo, previous_repo_path) if previous_repo_path else None

        cause_code = "UNKNOWN_CAUSE"
        recommended_fix = "publish / selection logic を手動確認"
        suggested_action = None

        if result.context.get("latest_date") == result.context.get("previous_date"):
            cause_code = "DATE_ROLLOVER_BROKEN"
            recommended_fix = "日付切り替え設定を修正"
        elif latest_exists is False and previous_exists is True:
            cause_code = "PUBLISH_REUSED"
            recommended_fix = "当日生成物を再取得して再 publish"
            suggested_action = "dispatch_deploy"
        elif "content_hash" in duplicate_fields and result.context.get("latest_content_hash"):
            cause_code = "OUTPUT_REUSED"
            recommended_fix = "publish 側の前回成果物再利用を止めて再 publish"
            suggested_action = "dispatch_deploy"
        elif "title" in duplicate_fields:
            cause_code = "SELECTION_LOGIC_BROKEN"
            recommended_fix = "作品選択ロジックを確認し、必要なら手動対応"

        summary = self._join_non_empty(
            [
                f"duplicate_fields={','.join(duplicate_fields) if duplicate_fields else 'none'}",
                f"latest_repo_exists={latest_exists}" if latest_repo_path else "",
                f"previous_repo_exists={previous_exists}" if previous_repo_path else "",
                f"latest_title={result.context.get('latest_title', '')}",
                f"previous_title={result.context.get('previous_title', '')}",
            ]
        )
        return ContentIncidentAnalysis(
            company_id=result.company_id,
            error_code=result.error_code,
            cause_code=cause_code,
            cause_summary=summary,
            recommended_fix=recommended_fix,
            diagnostics={
                "repo": repo,
                "workflow": workflow,
                "deploy_workflow": deploy_workflow,
                "latest_repo_path": latest_repo_path,
                "previous_repo_path": previous_repo_path,
                "latest_repo_exists": latest_exists,
                "previous_repo_exists": previous_exists,
                "suggested_action": suggested_action,
            },
        )

    def _analyze_serial_issue(self, company, result: CheckResult) -> ContentIncidentAnalysis:
        repo = self._value(company, "repo")
        rule = self._rule(company, result)
        workflow = rule.get("workflow") or self._value(company, "workflow")
        deploy_workflow = rule.get("deploy_workflow")
        latest_run = self._github.get_latest_workflow_run(repo, workflow)
        state_path = rule.get("repo_state_path")
        state_text = self._github.get_raw_text(repo, state_path) if state_path else None
        repo_state = self._safe_json(state_text)
        repo_progress = self._extract_json_path(repo_state, rule.get("repo_progress_path", "current_part"))
        repo_last_date = self._extract_json_path(repo_state, rule.get("repo_date_path", "last_processed_date"))
        failure_summary = self._failure_summary(repo, latest_run)

        cause_code = "UNKNOWN_CAUSE"
        recommended_fix = "state / chapter selection / publish を手動確認"
        suggested_action = None

        if latest_run and latest_run.get("conclusion") == "failure":
            cause_code = "GENERATION_FAILED"
            recommended_fix = "serial workflow を 1 回 rerun"
            suggested_action = "rerun_failed_jobs"
        elif repo_progress is not None and str(repo_progress) == str(result.context.get("progress_value")):
            cause_code = "SERIAL_STATE_STUCK"
            recommended_fix = "state 保存処理または publish workflow を再実行"
            if rule.get("allow_workflow_rerun_on_state_stuck", False):
                suggested_action = "dispatch_workflow"
        elif latest_run is None or self._is_run_stale(latest_run, self._today() - timedelta(days=1)):
            cause_code = "NEXT_CHAPTER_NOT_SELECTED"
            recommended_fix = "workflow_dispatch で選択処理を再実行"
            suggested_action = "dispatch_workflow"
        elif repo_last_date:
            cause_code = "PUBLISH_NOT_UPDATED"
            recommended_fix = "publish workflow を 1 回再実行"
            suggested_action = "dispatch_deploy"

        summary = self._join_non_empty(
            [
                f"latest_run={self._run_brief(latest_run)}" if latest_run else "latest_run=none",
                f"repo_progress={repo_progress}",
                f"repo_last_date={repo_last_date}",
                f"site_progress={result.context.get('display_progress_value')}",
                failure_summary,
            ]
        )
        return ContentIncidentAnalysis(
            company_id=result.company_id,
            error_code=result.error_code,
            cause_code=cause_code,
            cause_summary=summary,
            recommended_fix=recommended_fix,
            diagnostics={
                "repo": repo,
                "workflow": workflow,
                "deploy_workflow": deploy_workflow,
                "latest_run": latest_run,
                "repo_state": repo_state,
                "state_path": state_path,
                "suggested_action": suggested_action,
            },
        )

    def _rule(self, company, result: CheckResult) -> dict:
        if result.check_kind == CheckKind.LATEST_POST_FRESHNESS:
            return self._value(company, "freshness_rule") or {}
        if result.check_kind == CheckKind.DAILY_POST_PREVIOUS_DAY:
            return self._value(company, "daily_post_rule") or {}
        if result.check_kind == CheckKind.LATEST_POST_UNIQUENESS:
            return self._value(company, "uniqueness_rule") or {}
        if result.check_kind == CheckKind.SERIAL_PROGRESS:
            return self._value(company, "serial_rule") or {}
        return {}

    def _expected_date(self, result: CheckResult) -> date:
        if result.context.get("expected_date"):
            try:
                return date.fromisoformat(result.context["expected_date"])
            except Exception:
                pass
        return self._today() - timedelta(days=1)

    def _today(self) -> date:
        return date.today()

    def _format_repo_path(self, rule: dict, target_date: date) -> str | None:
        template = (rule or {}).get("repo_path_pattern")
        if not template:
            return None
        return template.format(
            yyyy=target_date.strftime("%Y"),
            mm=target_date.strftime("%m"),
            dd=target_date.strftime("%d"),
            date=target_date.isoformat(),
        ).lstrip("/")

    def _format_repo_prefix(self, rule: dict, target_date: date) -> str | None:
        template = (rule or {}).get("repo_path_prefix_pattern")
        if not template:
            return None
        return template.format(
            yyyy=target_date.strftime("%Y"),
            mm=target_date.strftime("%m"),
            dd=target_date.strftime("%d"),
            date=target_date.isoformat(),
        ).lstrip("/")

    def _repo_content_exists(self, repo: str, repo_path: str | None, repo_prefix: str | None):
        if repo_path:
            return self._github.path_exists(repo, repo_path)
        if repo_prefix:
            return self._github.path_prefix_exists(repo, repo_prefix)
        return None

    def _failure_summary(self, repo: str, run: dict | None) -> str:
        if not repo or not run or run.get("conclusion") != "failure":
            return ""
        jobs = self._github.get_run_jobs(repo, int(run.get("id", 0) or 0))
        failed_steps = []
        for job in jobs:
            for step in job.get("steps", []) or []:
                conclusion = step.get("conclusion")
                if conclusion and conclusion != "success":
                    failed_steps.append(f"{job.get('name')}::{step.get('name')}={conclusion}")
        return f"failure_reason={' | '.join(failed_steps[:3])}" if failed_steps else ""

    def _site_url_to_repo_path(self, company, url: str) -> str | None:
        if not url:
            return None
        site = self._value(company, "site") or ""
        site_path = urlparse(site).path.rstrip("/")
        parsed = urlparse(url)
        path = parsed.path
        if site_path and path.startswith(site_path):
            path = path[len(site_path) :]
        return path.lstrip("/")

    def _run_brief(self, run: dict | None) -> str:
        if not run:
            return ""
        return f"{run.get('status')}/{run.get('conclusion')}/{run.get('updated_at')}"

    def _commit_date(self, commit: dict | None) -> str:
        return (
            ((commit or {}).get("commit", {}) or {})
            .get("author", {})
            .get("date", "")
        )

    def _is_run_stale(self, run: dict, threshold_date: date) -> bool:
        updated_at = run.get("updated_at") if run else None
        if not updated_at:
            return True
        try:
            updated_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).date()
            return updated_date < threshold_date
        except Exception:
            return True

    def _safe_json(self, text: str | None) -> dict:
        if not text:
            return {}
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _extract_json_path(self, payload, path: str):
        if not payload or not path:
            return None
        current = payload
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def _join_non_empty(self, values: list[str]) -> str:
        return " / ".join([value for value in values if value])

    def _value(self, company, key: str):
        return company[key] if isinstance(company, dict) else getattr(company, key)
