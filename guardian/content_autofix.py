import os
import logging

from guardian.checkers.daily_post import DailyPostChecker
from guardian.checkers.latest_post_freshness import LatestPostFreshnessChecker
from guardian.checkers.latest_post_uniqueness import LatestPostUniquenessChecker
from guardian.checkers.serial_progress import SerialProgressChecker
from guardian.github_client import GitHubRepoClient
from guardian.models import AutoFixResult, CheckKind, CheckResult, CheckStatus, ContentIncidentAnalysis

_attempted_actions: set = set()
logger = logging.getLogger(__name__)


class ContentAutoFixer:
    def __init__(self):
        self._github = GitHubRepoClient()

    def apply(
        self,
        company,
        result: CheckResult,
        analysis: ContentIncidentAnalysis,
    ) -> AutoFixResult:
        company_id = result.company_id
        repo = analysis.diagnostics.get("repo", "")
        workflow = analysis.diagnostics.get("workflow") or (
            company["workflow"] if isinstance(company, dict) else company.workflow
        )
        deploy_workflow = analysis.diagnostics.get("deploy_workflow")
        action = analysis.diagnostics.get("suggested_action")
        logger.info(
            "target=%s autofix start fix=%s cause_code=%s",
            company_id,
            action or "none",
            analysis.cause_code,
        )

        if not action:
            result_fix = AutoFixResult(
                target_id=company_id,
                fix_kind="content_autofix",
                status="SKIP",
                message=f"{company_id} は高リスクまたは自動修正対象外のため原因解析のみ実施",
                context={"cause_code": analysis.cause_code},
            )
            logger.info(
                "target=%s autofix=content_autofix result=%s message=\"%s\"",
                company_id,
                result_fix.status,
                result_fix.message,
            )
            return result_fix

        if not os.environ.get("GITHUB_TOKEN", ""):
            result_fix = AutoFixResult(
                target_id=company_id,
                fix_kind="content_autofix",
                status="SKIP",
                message=f"{company_id} は GITHUB_TOKEN 未設定のため自動修正スキップ",
                context={"cause_code": analysis.cause_code, "action": action},
            )
            logger.info(
                "target=%s autofix=content_autofix result=%s message=\"%s\"",
                company_id,
                result_fix.status,
                result_fix.message,
            )
            return result_fix

        if action == "rerun_failed_jobs":
            run = analysis.diagnostics.get("latest_run") or {}
            run_id = run.get("id")
            key = (repo, action, run_id)
            if not run_id:
                return self._skip(company_id, analysis, action, "rerun 対象 run_id が取得できない")
            if key in _attempted_actions:
                return self._skip(company_id, analysis, action, "同一 run は既に再試行済み")
            ok, status_code = self._github.rerun_failed_jobs(repo, int(run_id))
            _attempted_actions.add(key)
            if ok:
                result_fix = AutoFixResult(
                    target_id=company_id,
                    fix_kind="content_autofix",
                    status="OK",
                    message=f"{company_id} workflow を 1 回再実行",
                    context={"action": action, "cause_code": analysis.cause_code, "http_status": status_code},
                )
                logger.info(
                    "target=%s autofix=content_autofix result=%s message=\"%s\"",
                    company_id,
                    result_fix.status,
                    result_fix.message,
                )
                return result_fix
            return self._fail(company_id, analysis, action, f"rerun API 失敗: HTTP {status_code}")

        if action in {"dispatch_workflow", "dispatch_deploy"}:
            chosen_workflow = deploy_workflow if action == "dispatch_deploy" and deploy_workflow else workflow
            key = (repo, action, chosen_workflow)
            if not chosen_workflow:
                return self._skip(company_id, analysis, action, "dispatch 対象 workflow 未設定")
            if key in _attempted_actions:
                return self._skip(company_id, analysis, action, "同一 workflow は既に dispatch 済み")
            ok, status_code = self._github.dispatch_workflow(repo, chosen_workflow)
            _attempted_actions.add(key)
            if ok:
                label = "deploy workflow を 1 回再実行" if action == "dispatch_deploy" else "workflow_dispatch を 1 回実行"
                result_fix = AutoFixResult(
                    target_id=company_id,
                    fix_kind="content_autofix",
                    status="OK",
                    message=f"{company_id} {label}",
                    context={"action": action, "cause_code": analysis.cause_code, "http_status": status_code},
                )
                logger.info(
                    "target=%s autofix=content_autofix result=%s message=\"%s\"",
                    company_id,
                    result_fix.status,
                    result_fix.message,
                )
                return result_fix
            return self._fail(company_id, analysis, action, f"workflow dispatch 失敗: HTTP {status_code}")

        return self._skip(company_id, analysis, action, "未対応の自動修正 action")

    def verify(self, company, result: CheckResult) -> CheckResult | None:
        checker_cls = {
            CheckKind.LATEST_POST_FRESHNESS: LatestPostFreshnessChecker,
            CheckKind.DAILY_POST_PREVIOUS_DAY: DailyPostChecker,
            CheckKind.LATEST_POST_UNIQUENESS: LatestPostUniquenessChecker,
            CheckKind.SERIAL_PROGRESS: SerialProgressChecker,
        }.get(result.check_kind)
        if checker_cls is None:
            return None
        logger.info(
            "target=%s verify start check=%s",
            result.company_id,
            result.check_kind.value.lower(),
        )
        rechecked = checker_cls().check(company)
        logger.info(
            "target=%s verify result=%s code=%s message=\"%s\"",
            result.company_id,
            rechecked.status.value,
            rechecked.error_code.value if rechecked.error_code else "",
            rechecked.detail,
        )
        return rechecked

    def build_verification_result(
        self,
        company_id: str,
        original: CheckResult,
        rechecked: CheckResult | None,
    ) -> AutoFixResult | None:
        if rechecked is None:
            return None
        if rechecked.status == CheckStatus.OK:
            result_fix = AutoFixResult(
                target_id=company_id,
                fix_kind="content_autofix_verify",
                status="OK",
                message=f"{company_id} 再確認で {original.error_code.value if original.error_code else original.check_kind.value} 解消を確認",
            )
            logger.info(
                "target=%s autofix=%s result=%s message=\"%s\"",
                company_id,
                result_fix.fix_kind,
                result_fix.status,
                result_fix.message,
            )
            return result_fix
        result_fix = AutoFixResult(
            target_id=company_id,
            fix_kind="content_autofix_verify",
            status="FAIL",
            message=f"{company_id} 再確認後も未解決: {rechecked.detail}",
        )
        logger.warning(
            "target=%s autofix=%s result=%s message=\"%s\"",
            company_id,
            result_fix.fix_kind,
            result_fix.status,
            result_fix.message,
        )
        return result_fix

    def _skip(self, company_id: str, analysis: ContentIncidentAnalysis, action: str, reason: str) -> AutoFixResult:
        result_fix = AutoFixResult(
            target_id=company_id,
            fix_kind="content_autofix",
            status="SKIP",
            message=f"{company_id} は {reason}",
            context={"cause_code": analysis.cause_code, "action": action},
        )
        logger.info(
            "target=%s autofix=%s result=%s message=\"%s\"",
            company_id,
            action or "content_autofix",
            result_fix.status,
            result_fix.message,
        )
        return result_fix

    def _fail(self, company_id: str, analysis: ContentIncidentAnalysis, action: str, reason: str) -> AutoFixResult:
        result_fix = AutoFixResult(
            target_id=company_id,
            fix_kind="content_autofix",
            status="FAIL",
            message=f"{company_id} 自動修正失敗: {reason}",
            context={"cause_code": analysis.cause_code, "action": action},
        )
        logger.warning(
            "target=%s autofix=%s result=%s message=\"%s\"",
            company_id,
            action or "content_autofix",
            result_fix.status,
            result_fix.message,
        )
        return result_fix
