"""
CheckResult / CheckStatus / ErrorCode のテスト

担当クラス: CheckResult, CheckStatus, ErrorCode
"""
import pytest
from datetime import datetime


class TestCheckResult:

    def test_check_result_has_required_fields(self):
        """CheckResult が必須フィールドをすべて持つ"""
        from guardian.models import CheckResult, CheckStatus, CheckKind
        result = CheckResult(
            company_id="test-co",
            check_kind=CheckKind.SITE_HTTP,
            status=CheckStatus.OK,
            error_code=None,
            detail="HTTP 200",
            checked_at=datetime(2026, 3, 10, 6, 0, 0),
        )
        assert result.company_id == "test-co"
        assert result.check_kind == CheckKind.SITE_HTTP
        assert result.status == CheckStatus.OK
        assert result.error_code is None
        assert result.detail == "HTTP 200"
        assert isinstance(result.checked_at, datetime)

    def test_check_status_ok_warning_error_exist(self):
        """CheckStatus に OK / WARNING / ERROR が存在する"""
        from guardian.models import CheckStatus
        assert CheckStatus.OK
        assert CheckStatus.WARNING
        assert CheckStatus.ERROR

    def test_error_code_all_codes_exist(self):
        """ErrorCode に仕様の全コードが存在する"""
        from guardian.models import ErrorCode
        expected = [
            "ACTION_FAILED", "SITE_DOWN", "SITE_DEGRADED",
            "ARTIFACT_MISSING", "KEYWORD_MISSING", "LINK_BROKEN",
            "DAILY_POST_MISSING", "ADSENSE_PAGE_MISSING", "CONFIG_INVALID",
            "SELF_CHECK_FAILED", "REPORT_MISSING", "UNKNOWN_ERROR",
        ]
        actual = [e.value for e in ErrorCode]
        for code in expected:
            assert code in actual, f"{code} が ErrorCode に存在しない"

    def test_check_kind_all_kinds_exist(self):
        """CheckKind に仕様の全種別が存在する"""
        from guardian.models import CheckKind
        expected = [
            "SITE_HTTP", "TOP_PAGE_KEYWORD", "LINK_HEALTH",
            "GITHUB_ACTIONS", "ARTIFACT", "DAILY_POST_PREVIOUS_DAY",
            "ADSENSE_PAGES", "REPORT_GENERATED", "CONFIG_VALID", "SELF_STATUS",
        ]
        actual = [k.value for k in CheckKind]
        for kind in expected:
            assert kind in actual, f"{kind} が CheckKind に存在しない"

    def test_check_result_is_error_when_status_error(self):
        """status が ERROR の CheckResult は is_error プロパティが True"""
        from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
        result = CheckResult(
            company_id="test-co",
            check_kind=CheckKind.SITE_HTTP,
            status=CheckStatus.ERROR,
            error_code=ErrorCode.SITE_DOWN,
            detail="HTTP 503",
            checked_at=datetime.now(),
        )
        assert result.is_error is True
        assert result.is_warning is False
        assert result.is_ok is False

    def test_check_result_is_warning_when_status_warning(self):
        """status が WARNING の CheckResult は is_warning プロパティが True"""
        from guardian.models import CheckResult, CheckStatus, CheckKind
        result = CheckResult(
            company_id="test-co",
            check_kind=CheckKind.GITHUB_ACTIONS,
            status=CheckStatus.WARNING,
            error_code=None,
            detail="in_progress",
            checked_at=datetime.now(),
        )
        assert result.is_warning is True
        assert result.is_error is False

    def test_check_result_is_ok_when_status_ok(self):
        """status が OK の CheckResult は is_ok プロパティが True"""
        from guardian.models import CheckResult, CheckStatus, CheckKind
        result = CheckResult(
            company_id="test-co",
            check_kind=CheckKind.SITE_HTTP,
            status=CheckStatus.OK,
            error_code=None,
            detail="HTTP 200",
            checked_at=datetime.now(),
        )
        assert result.is_ok is True
