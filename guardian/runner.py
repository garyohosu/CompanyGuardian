import logging
import os
from datetime import datetime
from guardian.models import (
    CheckResult, CheckStatus, CheckKind, ErrorCode, TriggerKind,
)
from guardian.logging_utils import setup_logging, get_log_path
from guardian.config_loader import ConfigLoader
from guardian.checkers.site_http import SiteHttpChecker
from guardian.checkers.top_page_keyword import TopPageKeywordChecker
from guardian.checkers.link_health import LinkHealthChecker
from guardian.checkers.github_actions import GithubActionsChecker
from guardian.checkers.artifact import ArtifactChecker
from guardian.checkers.daily_post import DailyPostChecker
from guardian.checkers.latest_post_freshness import LatestPostFreshnessChecker
from guardian.checkers.latest_post_uniqueness import LatestPostUniquenessChecker
from guardian.checkers.serial_progress import SerialProgressChecker
from guardian.checkers.adsense_page import AdSensePageChecker
from guardian.checkers.config_valid import ConfigValidChecker
from guardian.checkers.self_status import SelfStatusChecker
from guardian.incident_recorder import IncidentRecorder
from guardian.countermeasure_manager import CountermeasureManager
from guardian.daily_report_generator import DailyReportGenerator
from guardian.git_pusher import GitPusher
from guardian.auto_fixer import AutoFixer
from guardian.content_incident_analyzer import ContentIncidentAnalyzer
from guardian.content_autofix import ContentAutoFixer
from guardian.github_client import GitHubRepoClient

logger = logging.getLogger(__name__)
STATE_FILE_PATH = "state/content_monitoring_state.json"

CHECKER_REGISTRY = {
    "site_http": SiteHttpChecker,
    "top_page_keyword": TopPageKeywordChecker,
    "link_health": LinkHealthChecker,
    "github_actions": GithubActionsChecker,
    "artifact": ArtifactChecker,
    "daily_post_previous_day": DailyPostChecker,
    "latest_post_freshness": LatestPostFreshnessChecker,
    "latest_post_uniqueness": LatestPostUniquenessChecker,
    "serial_progress": SerialProgressChecker,
    "adsense_pages": AdSensePageChecker,
    "config_valid": ConfigValidChecker,
    "self_status": SelfStatusChecker,
}


class CompanyGuardianRunner:

    def __init__(self):
        setup_logging()
        self._github = GitHubRepoClient()
        self._incident_recorder = IncidentRecorder()
        self._cm_manager = CountermeasureManager()
        self._report_generator = DailyReportGenerator()
        self._git_pusher = GitPusher()
        self._auto_fixer = AutoFixer(self._github)
        self._content_analyzer = ContentIncidentAnalyzer(self._github)
        self._content_autofixer = ContentAutoFixer(self._github)
        self._companies_by_id = {}
        self._trigger = TriggerKind.SCHEDULED

    def run(self, trigger: TriggerKind) -> None:
        self._trigger = trigger
        companies = self._load_config()
        enabled = [c for c in companies if c["enabled"]]
        self._companies_by_id = {c["id"]: c for c in companies}
        logger.info(
            "CompanyGuardian started trigger=%s targets=%d log_path=%s",
            trigger.value.lower(),
            len(enabled),
            get_log_path(),
        )
        logger.info(
            "config loaded total_targets=%d enabled_targets=%d",
            len(companies),
            len(enabled),
        )
        logger.info(
            "state file=%s exists=%s",
            STATE_FILE_PATH,
            "yes" if os.path.exists(STATE_FILE_PATH) else "no",
        )
        self._github.log_auth_mode(logger)

        # 1. pre-check autofix: README 問題など実行継続性に関わる修正
        autofix_results = self._run_pre_check_fixes()

        # 2. 全チェック実行
        results = self._check_all(enabled)
        logger.info(
            "check phase completed results=%d ok=%d warning=%d error=%d",
            len(results),
            len([r for r in results if r.status == CheckStatus.OK]),
            len([r for r in results if r.status == CheckStatus.WARNING]),
            len([r for r in results if r.status == CheckStatus.ERROR]),
        )

        output_files = []
        if self._should_include_state_file(results):
            self._append_output_file(
                output_files,
                STATE_FILE_PATH if os.path.exists(STATE_FILE_PATH) else "",
            )

        # 3. 致命的 content defect を解析・修正・検証
        content_contexts, content_fixes = self._process_content_defects(results)
        autofix_results.extend(content_fixes)

        # 4. 異常処理: incident / countermeasure 生成
        if content_contexts:
            generated_files = self._handle_anomalies(results, content_contexts)
        else:
            generated_files = self._handle_anomalies(results)
        if isinstance(generated_files, (list, tuple, set)):
            for path in generated_files:
                self._append_output_file(output_files, path)

        # 5. post-check autofix: GitHub Actions 再試行など
        post_fixes = self._run_post_check_fixes(results)
        autofix_results.extend(post_fixes)

        # autofix で変更したファイルも push 対象へ
        for fix in autofix_results:
            for path in fix.changed_files:
                self._append_output_file(output_files, path)

        # 6. 日報生成（autofix 結果を含む）
        report = self._generate_report(results, trigger, autofix_results)
        self._append_output_file(output_files, getattr(report, "file_path", ""))

        # 7. git push
        push_ok = self._push_outputs(output_files)
        ok_count, warning_count, error_count = self._result_counts(results)
        autofix_ok, autofix_fail, autofix_skip = self._autofix_counts(autofix_results)
        logger.info(
            "CompanyGuardian finished ok=%d warning=%d error=%d autofix_ok=%d autofix_fail=%d autofix_skip=%d push=%s",
            ok_count,
            warning_count,
            error_count,
            autofix_ok,
            autofix_fail,
            autofix_skip,
            "ok" if push_ok else "fail",
        )

    def _run_pre_check_fixes(self) -> list:
        """チェック前に実行する低リスク自動修正。README コピーなど。"""
        results = []
        fix = self._auto_fixer.fix_readme_if_needed()
        if fix is not None:
            results.append(fix)
            logger.info("target=%s autofix=%s result=%s message=\"%s\"", fix.target_id, fix.fix_kind, fix.status, fix.message)
        else:
            logger.info("precheck autofix result=SKIP message=\"no pre-check fix required\"")
        return results

    def _run_post_check_fixes(self, check_results: list) -> list:
        """チェック後に実行する低リスク自動修正。GitHub Actions 再試行など。"""
        from guardian.models import CheckKind, CheckStatus, ErrorCode
        results = []
        content_defect_companies = {
            r.company_id
            for r in check_results
            if r.error_code in {
                ErrorCode.STALE_CONTENT,
                ErrorCode.DAILY_POST_MISSING,
                ErrorCode.DUPLICATE_CONTENT,
                ErrorCode.SERIAL_STALLED,
            }
        }

        for r in check_results:
            if (
                r.check_kind == CheckKind.GITHUB_ACTIONS
                and r.status == CheckStatus.ERROR
                and r.error_code == ErrorCode.ACTION_FAILED
                and "conclusion=failure" in (r.detail or "")
                and r.company_id not in content_defect_companies
            ):
                company = self._companies_by_id.get(r.company_id, {})
                repo = company.get("repo") if isinstance(company, dict) else getattr(company, "repo", None)
                logger.info(
                    "target=%s autofix start fix=github_actions_retry repo=%s",
                    r.company_id,
                    repo or "",
                )
                fix = self._auto_fixer.retry_github_actions_if_applicable(
                    r.company_id, repo or ""
                )
                if fix is not None:
                    results.append(fix)
                    self._log_autofix_result(fix)

        return results

    def _load_config(self) -> list:
        loader = ConfigLoader()
        return loader.load("companies/companies.yaml")

    def _process_content_defects(self, results: list) -> tuple[dict, list]:
        critical_codes = {
            ErrorCode.STALE_CONTENT,
            ErrorCode.DAILY_POST_MISSING,
            ErrorCode.DUPLICATE_CONTENT,
            ErrorCode.SERIAL_STALLED,
        }
        contexts = {}
        autofix_results = []

        for result in results:
            if result.error_code not in critical_codes or result.status != CheckStatus.ERROR:
                continue
            company = self._companies_by_id.get(result.company_id)
            if company is None:
                continue

            existing = contexts.get(result.company_id)
            if existing is not None:
                existing_result = existing.get("result")
                if self._content_priority(existing_result) <= self._content_priority(result):
                    continue

            logger.info(
                "target=%s analyze start check=%s code=%s",
                result.company_id,
                result.check_kind.value.lower(),
                result.error_code.value if result.error_code else "",
            )
            analysis = self._content_analyzer.analyze(company, result)
            fix = self._content_autofixer.apply(company, result, analysis)
            verification = None
            verification_fix = None
            if fix is not None:
                autofix_results.append(fix)
                if fix.status == "OK":
                    verification = self._content_autofixer.verify(company, result)
                    verification_fix = self._content_autofixer.build_verification_result(
                        result.company_id,
                        result,
                        verification,
                    )
                    if verification_fix is not None:
                        autofix_results.append(verification_fix)

            contexts[result.company_id] = {
                "result": result,
                "analysis": analysis,
                "fix": fix,
                "verification": verification,
                "verification_fix": verification_fix,
            }

        return contexts, autofix_results

    def _content_priority(self, result: CheckResult | None) -> int:
        priorities = {
            ErrorCode.STALE_CONTENT: 0,
            ErrorCode.DUPLICATE_CONTENT: 0,
            ErrorCode.SERIAL_STALLED: 0,
            ErrorCode.DAILY_POST_MISSING: 1,
        }
        if result is None:
            return 999
        return priorities.get(result.error_code, 999)

    def _check_all(self, companies: list) -> list:
        results = []
        for company in companies:
            company_id = company["id"] if isinstance(company, dict) else company.id
            kind = company["kind"] if isinstance(company, dict) else company.kind
            kind_value = kind.value if hasattr(kind, "value") else str(kind)
            checks = company["checks"] if isinstance(company, dict) else company.checks
            logger.info(
                "target=%s kind=%s checks=%s",
                company_id,
                kind_value,
                ",".join(str(ck).lower() for ck in checks),
            )
            for ck in checks:
                kind_str = str(ck).lower()
                logger.info("target=%s check=%s start", company_id, kind_str)
                # report_generated は trigger が必要なため registry 外で処理
                if kind_str == "report_generated":
                    from guardian.checkers.report_generated import ReportGeneratedChecker
                    checker = ReportGeneratedChecker(trigger=self._trigger)
                else:
                    factory = CHECKER_REGISTRY.get(kind_str)
                    if factory is None:
                        unknown_result = CheckResult(
                            company_id=company_id,
                            check_kind=CheckKind.UNKNOWN,
                            status=CheckStatus.WARNING,
                            error_code=None,
                            detail=f"未知の check_kind: {kind_str}",
                            checked_at=datetime.now(),
                        )
                        results.append(unknown_result)
                        self._log_check_result(company_id, kind_str, unknown_result)
                        continue
                    checker = factory()
                try:
                    result = checker.check(company)
                    results.append(result)
                    self._log_check_result(company_id, kind_str, result)
                except Exception as e:
                    logger.error(
                        "target=%s check=%s exception message=\"%s\"",
                        company_id,
                        kind_str,
                        e,
                        exc_info=True,
                    )
                    error_result = CheckResult(
                        company_id=company_id,
                        check_kind=CheckKind.UNKNOWN,
                        status=CheckStatus.ERROR,
                        error_code=ErrorCode.UNKNOWN_ERROR,
                        detail=str(e),
                        checked_at=datetime.now(),
                    )
                    results.append(error_result)
                    self._log_check_result(company_id, kind_str, error_result)
        return results

    def _handle_anomalies(self, results: list, content_contexts: dict | None = None) -> list:
        from collections import defaultdict
        by_company = defaultdict(list)
        output_files = []
        content_contexts = content_contexts or {}
        for r in results:
            by_company[r.company_id].append(r)

        for company_id, company_results in by_company.items():
            company = self._companies_by_id.get(
                company_id, {"id": company_id, "name": company_id}
            )
            incident = self._incident_recorder.create(
                company_results,
                company,
                content_context=content_contexts.get(company_id),
            )
            if incident is None:
                continue
            incident_path = self._incident_recorder.save(incident)
            self._append_output_file(output_files, incident_path)
            if self._cm_manager.should_create(incident):
                cm = self._cm_manager.create(incident)
                self._append_output_file(output_files, self._cm_manager.save(cm))
                incident.related_countermeasure = cm.cm_id
                self._incident_recorder.save(incident)
        return output_files

    def _generate_report(self, results: list, trigger: TriggerKind, autofix_results: list = None):
        report = self._report_generator.generate(results, trigger, autofix_results or [])
        self._report_generator.save(report)
        return report

    def _push_outputs(self, files=None) -> bool:
        if files is None:
            files = []
        elif isinstance(files, str):
            files = [files] if files else []
        else:
            files = [path for path in files if isinstance(path, str) and path]
        logger.info(
            "push files=%d targets=%s",
            len(files),
            ",".join(files) if files else "none",
        )
        try:
            return self._git_pusher.push_outputs(files)
        except Exception as e:
            logger.error("push failed message=\"%s\"", e, exc_info=True)
            return False

    def _append_output_file(self, files: list, path: str) -> None:
        if isinstance(path, str) and path and path not in files:
            files.append(path)

    def _should_include_state_file(self, results: list) -> bool:
        content_check_kinds = {
            CheckKind.DAILY_POST_PREVIOUS_DAY,
            CheckKind.LATEST_POST_FRESHNESS,
            CheckKind.LATEST_POST_UNIQUENESS,
            CheckKind.SERIAL_PROGRESS,
        }
        return any(result.check_kind in content_check_kinds for result in results)

    def _log_check_result(
        self,
        company_id: str,
        kind_str: str,
        result: CheckResult,
        prefix: str = "check",
    ) -> None:
        log_fn = {
            CheckStatus.OK: logger.info,
            CheckStatus.WARNING: logger.warning,
            CheckStatus.ERROR: logger.error,
        }.get(result.status, logger.info)
        code_part = f" code={result.error_code.value}" if result.error_code else ""
        log_fn(
            "target=%s %s=%s result=%s%s message=\"%s\"",
            company_id,
            prefix,
            kind_str,
            result.status.value,
            code_part,
            result.detail,
        )

    def _log_autofix_result(self, fix) -> None:
        log_fn = {
            "OK": logger.info,
            "WARN": logger.warning,
            "FAIL": logger.warning,
            "SKIP": logger.info,
        }.get(fix.status, logger.info)
        log_fn(
            "target=%s autofix=%s result=%s message=\"%s\"",
            fix.target_id,
            fix.fix_kind,
            fix.status,
            fix.message,
        )

    def _result_counts(self, results: list) -> tuple[int, int, int]:
        ok_count = len([r for r in results if r.status == CheckStatus.OK])
        warning_count = len([r for r in results if r.status == CheckStatus.WARNING])
        error_count = len([r for r in results if r.status == CheckStatus.ERROR])
        return ok_count, warning_count, error_count

    def _autofix_counts(self, fixes: list) -> tuple[int, int, int]:
        ok_count = len([f for f in fixes if f.status == "OK"])
        fail_count = len([f for f in fixes if f.status in {"FAIL", "WARN"}])
        skip_count = len([f for f in fixes if f.status == "SKIP"])
        return ok_count, fail_count, skip_count
