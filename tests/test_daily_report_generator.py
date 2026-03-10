"""
DailyReportGenerator のテスト

担当クラス: DailyReportGenerator, DailyReport
責務: CheckResult リストから DailyReport を生成し、Markdown として保存する。
"""
import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime


def _make_result(status="OK", check_kind="SITE_HTTP",
                 error_code=None, company_id="co"):
    from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
    return CheckResult(
        company_id=company_id,
        check_kind=CheckKind[check_kind],
        status=CheckStatus[status],
        error_code=ErrorCode[error_code] if error_code else None,
        detail="detail",
        checked_at=datetime(2026, 3, 10, 6, 0, 0),
    )


class TestDailyReportGeneratorGenerate:

    def test_generate_returns_daily_report(self):
        """generate が DailyReport を返す"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [_make_result("OK")]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert report is not None

    def test_report_total_count_matches_results(self):
        """total_count が results の件数と一致する"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [
            _make_result("OK"),
            _make_result("OK"),
            _make_result("ERROR", error_code="SITE_DOWN"),
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert report.total_count == 3

    def test_report_ok_count(self):
        """ok_count が OK 件数と一致する"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [
            _make_result("OK"),
            _make_result("OK"),
            _make_result("ERROR", error_code="SITE_DOWN"),
            _make_result("WARNING"),
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert report.ok_count == 2

    def test_report_warning_count(self):
        """warning_count が WARNING 件数と一致する"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [
            _make_result("OK"),
            _make_result("WARNING"),
            _make_result("WARNING"),
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert report.warning_count == 2

    def test_report_error_count(self):
        """error_count が ERROR 件数と一致する"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [
            _make_result("ERROR", error_code="SITE_DOWN"),
            _make_result("ERROR", error_code="ACTION_FAILED"),
            _make_result("OK"),
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert report.error_count == 2

    def test_report_action_required_contains_errors_and_warnings(self):
        """action_required に ERROR と WARNING が含まれる"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [
            _make_result("OK"),
            _make_result("WARNING"),
            _make_result("ERROR", error_code="SITE_DOWN"),
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        statuses = [r.status.value for r in report.action_required]
        assert "WARNING" in statuses
        assert "ERROR" in statuses
        assert "OK" not in statuses

    def test_report_trigger_is_set(self):
        """report.trigger が TriggerKind と一致する"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [_make_result("OK")]
        report = gen.generate(results, TriggerKind.MANUAL)
        assert report.trigger == TriggerKind.MANUAL

    def test_report_executed_at_is_datetime(self):
        """report.executed_at が datetime 型"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [_make_result("OK")]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert isinstance(report.executed_at, datetime)

    def test_report_adsense_anomalies_populated(self):
        """adsense_pages チェックの ERROR が adsense_anomalies に入る"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [
            _make_result("ERROR", check_kind="ADSENSE_PAGES",
                         error_code="ADSENSE_PAGE_MISSING"),
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert len(report.adsense_anomalies) == 1

    def test_report_self_monitor_result_set(self):
        """self_status の CheckResult が self_monitor_result にセットされる"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        results = [
            _make_result("OK", check_kind="SELF_STATUS"),
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert report.self_monitor_result is not None
        assert report.self_monitor_result.check_kind.value == "SELF_STATUS"


class TestDailyReportGeneratorResolveFileName:

    def test_scheduled_file_name_is_date_only(self):
        """定期実行: YYYY-MM-DD.md"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        name = gen._resolve_file_name(TriggerKind.SCHEDULED)
        import re
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", name)

    def test_manual_file_name_includes_manual_suffix(self):
        """手動実行: YYYY-MM-DD_manual_XX.md"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        import re
        gen = DailyReportGenerator()
        with patch("guardian.daily_report_generator.glob.glob", return_value=[]):
            name = gen._resolve_file_name(TriggerKind.MANUAL)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_manual_\d{2}\.md", name)

    def test_manual_file_name_increments_counter(self):
        """手動実行が 2 回目なら _manual_02.md になる"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind
        gen = DailyReportGenerator()
        existing = ["reports/daily/2026-03-10_manual_01.md"]
        with patch("guardian.daily_report_generator.glob.glob",
                   return_value=existing):
            name = gen._resolve_file_name(TriggerKind.MANUAL)
        assert "_manual_02.md" in name


class TestDailyReportGeneratorSave:

    def test_save_returns_file_path(self):
        """save がファイルパスを返す"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import DailyReport, TriggerKind
        gen = DailyReportGenerator()
        report = MagicMock(spec=DailyReport)
        report.executed_at = datetime(2026, 3, 10, 6, 0, 0)
        report.trigger = TriggerKind.SCHEDULED
        report.total_count = 3
        report.ok_count = 3
        report.warning_count = 0
        report.error_count = 0
        report.action_required = []
        report.applied_measures = []
        report.new_countermeasures = []
        report.self_monitor_result = None
        report.adsense_anomalies = []
        report.summary = "All OK"
        m = mock_open()
        with patch("builtins.open", m):
            with patch("guardian.daily_report_generator.os.makedirs"):
                with patch.object(gen, "_resolve_file_name",
                                  return_value="2026-03-10.md"):
                    path = gen.save(report)
        assert "reports/daily/" in path
        assert "2026-03-10.md" in path

    def test_save_writes_markdown_content(self):
        """save が Markdown を書き出す"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import DailyReport, TriggerKind
        gen = DailyReportGenerator()
        report = MagicMock(spec=DailyReport)
        report.executed_at = datetime(2026, 3, 10, 6, 0, 0)
        report.trigger = TriggerKind.SCHEDULED
        report.total_count = 1
        report.ok_count = 1
        report.warning_count = 0
        report.error_count = 0
        report.action_required = []
        report.applied_measures = []
        report.new_countermeasures = []
        report.self_monitor_result = None
        report.adsense_anomalies = []
        report.summary = "OK"
        m = mock_open()
        with patch("builtins.open", m):
            with patch("guardian.daily_report_generator.os.makedirs"):
                with patch.object(gen, "_resolve_file_name",
                                  return_value="2026-03-10.md"):
                    gen.save(report)
        m().write.assert_called()
