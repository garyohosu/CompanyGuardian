"""
IncidentRecorder のテスト

担当クラス: IncidentRecorder, Incident
責務: ERROR の CheckResult からインシデントを生成し Markdown として保存する。
"""
import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime


def _make_error_result(company_id="test-co", check_kind="SITE_HTTP",
                       error_code="SITE_DOWN", detail="HTTP 503"):
    from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
    return CheckResult(
        company_id=company_id,
        check_kind=CheckKind[check_kind],
        status=CheckStatus.ERROR,
        error_code=ErrorCode[error_code],
        detail=detail,
        checked_at=datetime(2026, 3, 10, 6, 0, 0),
    )


def _make_ok_result(company_id="test-co"):
    from guardian.models import CheckResult, CheckStatus, CheckKind
    return CheckResult(
        company_id=company_id,
        check_kind=CheckKind.SITE_HTTP,
        status=CheckStatus.OK,
        error_code=None,
        detail="HTTP 200",
        checked_at=datetime(2026, 3, 10, 6, 0, 0),
    )


def _make_company():
    from tests.conftest import make_company
    return make_company(id="test-co", name="Test Company")


class TestIncidentRecorderCreate:

    def test_create_returns_incident_for_error_results(self):
        """ERROR 結果を渡すと Incident が返る"""
        from guardian.incident_recorder import IncidentRecorder
        recorder = IncidentRecorder()
        company = _make_company()
        results = [_make_error_result()]
        incident = recorder.create(results, company)
        assert incident is not None

    def test_incident_has_target_name(self):
        """Incident の target_name が Company の name と一致する"""
        from guardian.incident_recorder import IncidentRecorder
        recorder = IncidentRecorder()
        company = _make_company()
        results = [_make_error_result()]
        incident = recorder.create(results, company)
        assert incident.target_name == "Test Company"

    def test_incident_error_codes_match_results(self):
        """Incident の error_codes に CheckResult の error_code が含まれる"""
        from guardian.incident_recorder import IncidentRecorder
        recorder = IncidentRecorder()
        company = _make_company()
        results = [_make_error_result(error_code="SITE_DOWN")]
        incident = recorder.create(results, company)
        assert any(ec.value == "SITE_DOWN" for ec in incident.error_codes)

    def test_incident_has_incident_date(self):
        """Incident の incident_date が設定されている"""
        from guardian.incident_recorder import IncidentRecorder
        from datetime import date
        recorder = IncidentRecorder()
        company = _make_company()
        results = [_make_error_result()]
        incident = recorder.create(results, company)
        assert isinstance(incident.incident_date, date)

    def test_multiple_errors_aggregated_into_one_incident(self):
        """同一対象の複数 ERROR は 1 Incident に集約される"""
        from guardian.incident_recorder import IncidentRecorder
        recorder = IncidentRecorder()
        company = _make_company()
        results = [
            _make_error_result(check_kind="SITE_HTTP", error_code="SITE_DOWN"),
            _make_error_result(check_kind="GITHUB_ACTIONS", error_code="ACTION_FAILED"),
        ]
        incident = recorder.create(results, company)
        assert len(incident.error_codes) == 2

    def test_create_returns_none_when_no_errors(self):
        """ERROR がない場合は None を返す（incident 不要）"""
        from guardian.incident_recorder import IncidentRecorder
        recorder = IncidentRecorder()
        company = _make_company()
        results = [_make_ok_result()]
        incident = recorder.create(results, company)
        assert incident is None

    def test_warning_only_does_not_create_incident(self):
        """WARNING のみの結果では incident を作らない"""
        from guardian.incident_recorder import IncidentRecorder
        from guardian.models import CheckResult, CheckStatus, CheckKind
        recorder = IncidentRecorder()
        company = _make_company()
        warning_result = CheckResult(
            company_id="test-co",
            check_kind=CheckKind.GITHUB_ACTIONS,
            status=CheckStatus.WARNING,
            error_code=None,
            detail="in_progress",
            checked_at=datetime.now(),
        )
        incident = recorder.create([warning_result], company)
        assert incident is None


class TestIncidentRecorderSave:

    def test_save_returns_file_path(self):
        """save が保存先ファイルパスを返す"""
        from guardian.incident_recorder import IncidentRecorder
        from guardian.models import Incident, ErrorCode
        from datetime import date
        recorder = IncidentRecorder()
        incident = MagicMock(spec=Incident)
        incident.incident_date = date(2026, 3, 10)
        incident.target_name = "Test Company"
        incident.error_codes = [ErrorCode.SITE_DOWN]
        with patch("builtins.open", mock_open()):
            with patch("guardian.incident_recorder.os.makedirs"):
                path = recorder.save(incident)
        assert "incidents/" in path
        assert "2026-03-10" in path

    def test_save_writes_markdown_file(self):
        """save が Markdown ファイルを書き出す"""
        from guardian.incident_recorder import IncidentRecorder
        from guardian.models import Incident, ErrorCode
        from datetime import date
        recorder = IncidentRecorder()
        incident = MagicMock(spec=Incident)
        incident.incident_date = date(2026, 3, 10)
        incident.target_name = "Test Company"
        incident.error_codes = [ErrorCode.SITE_DOWN]
        incident.phenomenon = "Site returned 503"
        incident.impact = "公開停止"
        incident.cause = "不明"
        incident.quick_fix = "再確認"
        incident.permanent_fix_candidates = ""
        incident.result = ""
        incident.related_countermeasure = ""
        m = mock_open()
        with patch("builtins.open", m):
            with patch("guardian.incident_recorder.os.makedirs"):
                recorder.save(incident)
        m().write.assert_called()

    def test_save_file_path_follows_naming_convention(self):
        """ファイル名が incidents/YYYY-MM-DD-<target>-<slug>.md の形式"""
        import re
        from guardian.incident_recorder import IncidentRecorder
        from guardian.models import Incident, ErrorCode
        from datetime import date
        recorder = IncidentRecorder()
        incident = MagicMock(spec=Incident)
        incident.incident_date = date(2026, 3, 10)
        incident.target_name = "Auto AI Blog"
        incident.error_codes = [ErrorCode.SITE_DOWN]
        with patch("builtins.open", mock_open()):
            with patch("guardian.incident_recorder.os.makedirs"):
                path = recorder.save(incident)
        assert re.search(r"incidents/2026-03-10-.+\.md", path)
