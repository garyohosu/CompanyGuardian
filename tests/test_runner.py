"""
CompanyGuardianRunner のテスト

担当クラス: CompanyGuardianRunner
責務: 全体オーケストレーション（設定読込 → チェック → 異常処理 → 日報 → push）
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def _make_company(id_="test-co", kind="virtual_company", enabled=True):
    from tests.conftest import make_company
    return make_company(id=id_, kind=kind, enabled=enabled)


def _make_ok_result(company_id="test-co", check_kind="SITE_HTTP"):
    from guardian.models import CheckResult, CheckStatus, CheckKind
    return CheckResult(
        company_id=company_id,
        check_kind=CheckKind[check_kind],
        status=CheckStatus.OK,
        error_code=None,
        detail="OK",
        checked_at=datetime(2026, 3, 10, 6, 0, 0),
    )


def _make_error_result(company_id="test-co"):
    from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
    return CheckResult(
        company_id=company_id,
        check_kind=CheckKind.SITE_HTTP,
        status=CheckStatus.ERROR,
        error_code=ErrorCode.SITE_DOWN,
        detail="HTTP 503",
        checked_at=datetime(2026, 3, 10, 6, 0, 0),
    )


class TestCompanyGuardianRunnerRun:

    def _make_runner(self):
        from guardian.runner import CompanyGuardianRunner
        return CompanyGuardianRunner()

    def test_run_calls_load_config(self):
        """run は _load_config を呼ぶ"""
        runner = self._make_runner()
        from guardian.models import TriggerKind
        with patch.object(runner, "_load_config", return_value=[]) as mock_load:
            with patch.object(runner, "_check_all", return_value=[]):
                with patch.object(runner, "_handle_anomalies"):
                    with patch.object(runner, "_generate_report", return_value=MagicMock()):
                        with patch.object(runner, "_push_outputs"):
                            runner.run(TriggerKind.SCHEDULED)
        mock_load.assert_called_once()

    def test_run_calls_check_all_with_companies(self):
        """run は _check_all に companies を渡す"""
        runner = self._make_runner()
        from guardian.models import TriggerKind
        companies = [_make_company()]
        with patch.object(runner, "_load_config", return_value=companies):
            with patch.object(runner, "_check_all", return_value=[]) as mock_check:
                with patch.object(runner, "_handle_anomalies"):
                    with patch.object(runner, "_generate_report", return_value=MagicMock()):
                        with patch.object(runner, "_push_outputs"):
                            runner.run(TriggerKind.SCHEDULED)
        mock_check.assert_called_once_with(companies)

    def test_run_calls_handle_anomalies(self):
        """run は _handle_anomalies を呼ぶ"""
        runner = self._make_runner()
        from guardian.models import TriggerKind
        results = [_make_error_result()]
        with patch.object(runner, "_load_config", return_value=[_make_company()]):
            with patch.object(runner, "_check_all", return_value=results):
                with patch.object(runner, "_handle_anomalies") as mock_handle:
                    with patch.object(runner, "_generate_report", return_value=MagicMock()):
                        with patch.object(runner, "_push_outputs"):
                            runner.run(TriggerKind.SCHEDULED)
        mock_handle.assert_called_once_with(results)

    def test_run_calls_generate_report(self):
        """run は _generate_report を呼ぶ"""
        runner = self._make_runner()
        from guardian.models import TriggerKind
        with patch.object(runner, "_load_config", return_value=[]):
            with patch.object(runner, "_check_all", return_value=[]):
                with patch.object(runner, "_handle_anomalies"):
                    with patch.object(runner, "_generate_report",
                                      return_value=MagicMock()) as mock_report:
                        with patch.object(runner, "_push_outputs"):
                            runner.run(TriggerKind.SCHEDULED)
        mock_report.assert_called_once()

    def test_run_calls_push_outputs(self):
        """run は _push_outputs を呼ぶ"""
        runner = self._make_runner()
        from guardian.models import TriggerKind
        with patch.object(runner, "_load_config", return_value=[]):
            with patch.object(runner, "_check_all", return_value=[]):
                with patch.object(runner, "_handle_anomalies"):
                    with patch.object(runner, "_generate_report", return_value=MagicMock()):
                        with patch.object(runner, "_push_outputs") as mock_push:
                            runner.run(TriggerKind.SCHEDULED)
        mock_push.assert_called_once()

    def test_run_skips_disabled_companies(self):
        """enabled=False の Company はチェックしない"""
        runner = self._make_runner()
        from guardian.models import TriggerKind
        enabled = _make_company(id_="enabled-co", enabled=True)
        disabled = _make_company(id_="disabled-co", enabled=False)
        with patch.object(runner, "_load_config", return_value=[enabled, disabled]):
            with patch.object(runner, "_check_all", return_value=[]) as mock_check:
                with patch.object(runner, "_handle_anomalies"):
                    with patch.object(runner, "_generate_report", return_value=MagicMock()):
                        with patch.object(runner, "_push_outputs"):
                            runner.run(TriggerKind.SCHEDULED)
        # _check_all に渡される companies には disabled が含まれない
        called_companies = mock_check.call_args[0][0]
        ids = [c["id"] for c in called_companies]
        assert "enabled-co" in ids
        assert "disabled-co" not in ids

    def test_run_continues_after_single_check_failure(self):
        """1 社でチェック例外が起きても残りを継続する"""
        runner = self._make_runner()
        from guardian.models import TriggerKind
        companies = [
            _make_company(id_="co-1"),
            _make_company(id_="co-2"),
        ]
        call_count = {"n": 0}

        def side_effect(company):
            call_count["n"] += 1
            if company["id"] == "co-1":
                raise RuntimeError("unexpected error")
            return [_make_ok_result(company_id="co-2")]

        with patch.object(runner, "_load_config", return_value=companies):
            with patch.object(runner, "_check_all",
                              side_effect=lambda cos: [
                                  r for c in cos
                                  for r in ([] if c["id"] == "co-1"
                                            else [_make_ok_result(c["id"])])
                              ]):
                with patch.object(runner, "_handle_anomalies"):
                    with patch.object(runner, "_generate_report", return_value=MagicMock()):
                        with patch.object(runner, "_push_outputs"):
                            # 例外なく run が完了することを確認
                            runner.run(TriggerKind.SCHEDULED)


class TestCompanyGuardianRunnerCheckAll:

    def _make_runner(self):
        from guardian.runner import CompanyGuardianRunner
        return CompanyGuardianRunner()

    def test_check_all_returns_list_of_results(self):
        """_check_all が CheckResult のリストを返す"""
        runner = self._make_runner()
        companies = [_make_company()]
        ok_result = _make_ok_result()
        mock_checker = MagicMock()
        mock_checker.check.return_value = ok_result
        with patch("guardian.runner.CHECKER_REGISTRY",
                   {"site_http": lambda: mock_checker}):
            results = runner._check_all(companies)
        assert isinstance(results, list)

    def test_check_all_unknown_check_kind_skips_with_warning(self):
        """未知の check_kind はスキップして WARNING を記録する"""
        runner = self._make_runner()
        company = _make_company()
        company["checks"] = ["unknown_kind"]
        results = runner._check_all([company])
        warning_results = [r for r in results if r.status.value == "WARNING"]
        assert len(warning_results) >= 1


class TestCompanyGuardianRunnerHandleAnomalies:

    def _make_runner(self):
        from guardian.runner import CompanyGuardianRunner
        return CompanyGuardianRunner()

    def test_handle_anomalies_creates_incident_for_error(self):
        """ERROR 結果に対して incident が作成される"""
        runner = self._make_runner()
        results = [_make_error_result()]
        mock_recorder = MagicMock()
        mock_incident = MagicMock()
        mock_recorder.create.return_value = mock_incident
        mock_recorder.save.return_value = "incidents/xxx.md"
        runner._incident_recorder = mock_recorder
        runner._cm_manager = MagicMock()
        runner._cm_manager.should_create.return_value = False
        paths = runner._handle_anomalies(results)
        mock_recorder.create.assert_called()
        assert paths == ["incidents/xxx.md"]

    def test_handle_anomalies_no_incident_for_ok_only(self):
        """OK のみの場合 incident は作成しない"""
        runner = self._make_runner()
        results = [_make_ok_result()]
        mock_recorder = MagicMock()
        mock_recorder.create.return_value = None
        runner._incident_recorder = mock_recorder
        runner._cm_manager = MagicMock()
        paths = runner._handle_anomalies(results)
        # create が None を返したので save は呼ばれない
        mock_recorder.save.assert_not_called()
        assert paths == []

    def test_handle_anomalies_creates_countermeasure_when_needed(self):
        """should_create が True なら countermeasure を作成する"""
        runner = self._make_runner()
        results = [_make_error_result()]
        mock_recorder = MagicMock()
        mock_incident = MagicMock()
        mock_recorder.create.return_value = mock_incident
        mock_recorder.save.return_value = "incidents/xxx.md"
        runner._incident_recorder = mock_recorder
        mock_cm_mgr = MagicMock()
        mock_cm_mgr.should_create.return_value = True
        mock_cm = MagicMock()
        mock_cm_mgr.create.return_value = mock_cm
        mock_cm_mgr.save.return_value = "countermeasures/CM-001.md"
        runner._cm_manager = mock_cm_mgr
        paths = runner._handle_anomalies(results)
        mock_cm_mgr.create.assert_called_with(mock_incident)
        mock_cm_mgr.save.assert_called_with(mock_cm)
        assert paths == ["incidents/xxx.md", "countermeasures/CM-001.md"]

    def test_run_pushes_incident_countermeasure_and_report(self):
        """run は incident / countermeasure / report をまとめて push する"""
        runner = self._make_runner()
        from guardian.models import TriggerKind
        report = MagicMock(file_path="reports/daily/2026-03-10.md")
        with patch.object(runner, "_load_config", return_value=[]):
            with patch.object(runner, "_check_all", return_value=[]):
                with patch.object(runner, "_handle_anomalies",
                                  return_value=["incidents/x.md", "countermeasures/y.md"]):
                    with patch.object(runner, "_run_pre_check_fixes", return_value=[]):
                        with patch.object(runner, "_run_post_check_fixes", return_value=[]):
                            with patch.object(runner, "_generate_report", return_value=report):
                                with patch.object(runner, "_push_outputs") as mock_push:
                                    runner.run(TriggerKind.SCHEDULED)
        mock_push.assert_called_once_with([
            "incidents/x.md",
            "countermeasures/y.md",
            "reports/daily/2026-03-10.md",
        ])


class TestAutoFixIntegration:

    def _make_runner(self):
        from guardian.runner import CompanyGuardianRunner
        return CompanyGuardianRunner()

    def test_readme_autofix_included_in_push(self):
        """README 自動コピー時、README.md が push 対象に含まれる"""
        from guardian.runner import CompanyGuardianRunner
        from guardian.models import TriggerKind, AutoFixResult
        runner = self._make_runner()
        readme_fix = AutoFixResult(
            target_id="company-guardian",
            fix_kind="readme_copy",
            status="OK",
            message="README.txt を README.md にコピー",
            changed_files=["README.md"],
        )
        report = MagicMock(file_path="reports/daily/2026-03-10.md")
        with patch.object(runner, "_load_config", return_value=[]):
            with patch.object(runner, "_check_all", return_value=[]):
                with patch.object(runner, "_handle_anomalies", return_value=[]):
                    with patch.object(runner, "_run_pre_check_fixes",
                                      return_value=[readme_fix]):
                        with patch.object(runner, "_run_post_check_fixes", return_value=[]):
                            with patch.object(runner, "_generate_report", return_value=report):
                                with patch.object(runner, "_push_outputs") as mock_push:
                                    runner.run(TriggerKind.SCHEDULED)
        pushed_files = mock_push.call_args[0][0]
        assert "README.md" in pushed_files

    def test_applied_measures_not_empty_in_report(self):
        """日報の applied_measures が空欄にならない（自動修正なしなら理由が入る）"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        report = gen.generate([], TriggerKind.SCHEDULED, autofix_results=[])
        assert len(report.applied_measures) >= 1
        assert any("自動修正対象なし" in m for m in report.applied_measures)

    def test_applied_measures_contains_autofix_result(self):
        """autofix_results がある場合、applied_measures に AUTO_FIX ログが入る"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind, AutoFixResult
        gen = DailyReportGenerator()
        fix = AutoFixResult(
            target_id="company-guardian",
            fix_kind="readme_copy",
            status="OK",
            message="README.txt を README.md にコピーして自己監視前提を修正",
        )
        report = gen.generate([], TriggerKind.SCHEDULED, autofix_results=[fix])
        assert any("[AUTO_FIX][OK]" in m for m in report.applied_measures)

    def test_github_actions_retry_post_check_fix(self):
        """github_actions ERROR (failure) が検出された場合 _run_post_check_fixes が再試行を試みる"""
        from guardian.runner import CompanyGuardianRunner
        from guardian.models import (
            CheckResult, CheckStatus, CheckKind, ErrorCode, TriggerKind
        )
        from datetime import datetime
        runner = self._make_runner()
        runner._companies_by_id = {
            "test-co": {"id": "test-co", "repo": "org/test-co"}
        }
        error_result = CheckResult(
            company_id="test-co",
            check_kind=CheckKind.GITHUB_ACTIONS,
            status=CheckStatus.ERROR,
            error_code=ErrorCode.ACTION_FAILED,
            detail="conclusion=failure",
            checked_at=datetime.now(),
        )
        skip_fix = MagicMock()
        skip_fix.status = "SKIP"
        skip_fix.message = "GITHUB_TOKEN 未設定のため再試行スキップ"
        with patch.object(runner._auto_fixer,
                          "retry_github_actions_if_applicable",
                          return_value=skip_fix) as mock_retry:
            fixes = runner._run_post_check_fixes([error_result])
        mock_retry.assert_called_once_with("test-co", "org/test-co")
        assert len(fixes) == 1
