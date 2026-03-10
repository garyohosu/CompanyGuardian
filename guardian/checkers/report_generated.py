import os
from datetime import datetime, date, timedelta
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode, TriggerKind


class ReportGeneratedChecker:

    def __init__(self, trigger: TriggerKind = TriggerKind.SCHEDULED):
        self.trigger = trigger

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        target_date = self._resolve_target_date(self.trigger)
        path = f"reports/daily/{target_date}.md"

        if os.path.exists(path):
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.REPORT_GENERATED,
                status=CheckStatus.OK,
                error_code=None,
                detail=f"日報確認済: {path}",
                checked_at=datetime.now(),
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.REPORT_GENERATED,
            status=CheckStatus.ERROR,
            error_code=ErrorCode.REPORT_MISSING,
            detail=f"日報なし: {path}",
            checked_at=datetime.now(),
        )

    def _resolve_target_date(self, trigger: TriggerKind) -> date:
        # 定期・手動ともに前日（JST）の定期日報を対象
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo("Asia/Tokyo")
        except ImportError:
            from datetime import timezone
            tz = timezone.utc
        now = datetime.now(tz=tz)
        return (now - timedelta(days=1)).date()
