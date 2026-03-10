import logging
from datetime import datetime
from guardian.models import (
    CheckResult, CheckStatus, CheckKind, ErrorCode, TriggerKind,
)
from guardian.config_loader import ConfigLoader
from guardian.checkers.site_http import SiteHttpChecker
from guardian.checkers.top_page_keyword import TopPageKeywordChecker
from guardian.checkers.link_health import LinkHealthChecker
from guardian.checkers.github_actions import GithubActionsChecker
from guardian.checkers.artifact import ArtifactChecker
from guardian.checkers.daily_post import DailyPostChecker
from guardian.checkers.adsense_page import AdSensePageChecker
from guardian.checkers.config_valid import ConfigValidChecker
from guardian.checkers.self_status import SelfStatusChecker
from guardian.incident_recorder import IncidentRecorder
from guardian.countermeasure_manager import CountermeasureManager
from guardian.daily_report_generator import DailyReportGenerator
from guardian.git_pusher import GitPusher
from guardian.auto_fixer import AutoFixer

logger = logging.getLogger(__name__)

CHECKER_REGISTRY = {
    "site_http": SiteHttpChecker,
    "top_page_keyword": TopPageKeywordChecker,
    "link_health": LinkHealthChecker,
    "github_actions": GithubActionsChecker,
    "artifact": ArtifactChecker,
    "daily_post_previous_day": DailyPostChecker,
    "adsense_pages": AdSensePageChecker,
    "config_valid": ConfigValidChecker,
    "self_status": SelfStatusChecker,
}


class CompanyGuardianRunner:

    def __init__(self):
        self._incident_recorder = IncidentRecorder()
        self._cm_manager = CountermeasureManager()
        self._report_generator = DailyReportGenerator()
        self._git_pusher = GitPusher()
        self._auto_fixer = AutoFixer()
        self._companies_by_id = {}
        self._trigger = TriggerKind.SCHEDULED

    def run(self, trigger: TriggerKind) -> None:
        self._trigger = trigger
        companies = self._load_config()
        enabled = [c for c in companies if c["enabled"]]
        self._companies_by_id = {c["id"]: c for c in companies}

        # 1. pre-check autofix: README 問題など実行継続性に関わる修正
        autofix_results = self._run_pre_check_fixes()

        # 2. 全チェック実行
        results = self._check_all(enabled)

        # 3. 異常処理: incident / countermeasure 生成
        output_files = []
        generated_files = self._handle_anomalies(results)
        if isinstance(generated_files, (list, tuple, set)):
            for path in generated_files:
                self._append_output_file(output_files, path)

        # 4. post-check autofix: GitHub Actions 再試行など
        post_fixes = self._run_post_check_fixes(results)
        autofix_results.extend(post_fixes)

        # autofix で変更したファイルも push 対象へ
        for fix in autofix_results:
            for path in fix.changed_files:
                self._append_output_file(output_files, path)

        # 5. 日報生成（autofix 結果を含む）
        report = self._generate_report(results, trigger, autofix_results)
        self._append_output_file(output_files, getattr(report, "file_path", ""))

        # 6. git push
        self._push_outputs(output_files)

    def _run_pre_check_fixes(self) -> list:
        """チェック前に実行する低リスク自動修正。README コピーなど。"""
        results = []
        fix = self._auto_fixer.fix_readme_if_needed()
        if fix is not None:
            results.append(fix)
            logger.info(f"[AUTO_FIX][{fix.status}] {fix.message}")
        return results

    def _run_post_check_fixes(self, check_results: list) -> list:
        """チェック後に実行する低リスク自動修正。GitHub Actions 再試行など。"""
        from guardian.models import CheckKind, CheckStatus, ErrorCode
        results = []

        for r in check_results:
            if (
                r.check_kind == CheckKind.GITHUB_ACTIONS
                and r.status == CheckStatus.ERROR
                and r.error_code == ErrorCode.ACTION_FAILED
                and "conclusion=failure" in (r.detail or "")
            ):
                company = self._companies_by_id.get(r.company_id, {})
                repo = company.get("repo") if isinstance(company, dict) else getattr(company, "repo", None)
                fix = self._auto_fixer.retry_github_actions_if_applicable(
                    r.company_id, repo or ""
                )
                if fix is not None:
                    results.append(fix)
                    logger.info(f"[AUTO_FIX][{fix.status}] {fix.message}")

        return results

    def _load_config(self) -> list:
        loader = ConfigLoader()
        return loader.load("companies/companies.yaml")

    def _check_all(self, companies: list) -> list:
        results = []
        for company in companies:
            checks = company["checks"] if isinstance(company, dict) else company.checks
            for ck in checks:
                kind_str = str(ck).lower()
                # report_generated は trigger が必要なため registry 外で処理
                if kind_str == "report_generated":
                    from guardian.checkers.report_generated import ReportGeneratedChecker
                    checker = ReportGeneratedChecker(trigger=self._trigger)
                else:
                    factory = CHECKER_REGISTRY.get(kind_str)
                    if factory is None:
                        results.append(CheckResult(
                            company_id=company["id"] if isinstance(company, dict) else company.id,
                            check_kind=CheckKind.UNKNOWN,
                            status=CheckStatus.WARNING,
                            error_code=None,
                            detail=f"未知の check_kind: {kind_str}",
                            checked_at=datetime.now(),
                        ))
                        continue
                    checker = factory()
                try:
                    result = checker.check(company)
                    results.append(result)
                except Exception as e:
                    logger.error(f"チェック例外 {company['id']} / {kind_str}: {e}")
                    results.append(CheckResult(
                        company_id=company["id"] if isinstance(company, dict) else company.id,
                        check_kind=CheckKind.UNKNOWN,
                        status=CheckStatus.ERROR,
                        error_code=ErrorCode.UNKNOWN_ERROR,
                        detail=str(e),
                        checked_at=datetime.now(),
                    ))
        return results

    def _handle_anomalies(self, results: list) -> list:
        from collections import defaultdict
        by_company = defaultdict(list)
        output_files = []
        for r in results:
            by_company[r.company_id].append(r)

        for company_id, company_results in by_company.items():
            company = self._companies_by_id.get(
                company_id, {"id": company_id, "name": company_id}
            )
            incident = self._incident_recorder.create(company_results, company)
            if incident is None:
                continue
            self._append_output_file(output_files, self._incident_recorder.save(incident))
            if self._cm_manager.should_create(incident):
                cm = self._cm_manager.create(incident)
                self._append_output_file(output_files, self._cm_manager.save(cm))
        return output_files

    def _generate_report(self, results: list, trigger: TriggerKind, autofix_results: list = None):
        report = self._report_generator.generate(results, trigger, autofix_results or [])
        self._report_generator.save(report)
        return report

    def _push_outputs(self, files=None) -> None:
        if files is None:
            files = []
        elif isinstance(files, str):
            files = [files] if files else []
        else:
            files = [path for path in files if isinstance(path, str) and path]
        try:
            self._git_pusher.push_outputs(files)
        except Exception as e:
            logger.error(f"push 失敗: {e}")

    def _append_output_file(self, files: list, path: str) -> None:
        if isinstance(path, str) and path and path not in files:
            files.append(path)
