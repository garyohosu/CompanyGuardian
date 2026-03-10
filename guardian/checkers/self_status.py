import os
from datetime import datetime, date, timedelta
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

_README_PATH = "README.md"

_REQUIRED_SECTIONS = [
    "## 目的",
    "## 実行環境",
    "## 定期実行",
    "## 監視対象",
    "## 実行方法",
    "## 日報",
    "## インシデント",
    "## 再発防止策",
    "## 会社の追加方法",
    "## 自己監視",
    "## 障害時対応",
    "## AdSense",
]


class SelfStatusChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]

        readme_ok = self._check_readme_sections(required=None)
        report_ok = self._check_prev_report_consistency()

        if not readme_ok or not report_ok:
            detail_parts = []
            if not readme_ok:
                detail_parts.append("README 必須セクション欠落")
            if not report_ok:
                detail_parts.append("前回日報整合不一致")
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.SELF_STATUS,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SELF_CHECK_FAILED,
                detail=", ".join(detail_parts),
                checked_at=datetime.now(),
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.SELF_STATUS,
            status=CheckStatus.OK,
            error_code=None,
            detail="自己監視正常",
            checked_at=datetime.now(),
        )

    def _check_readme_sections(self, required=None) -> bool:
        sections = required if required is not None else _REQUIRED_SECTIONS
        try:
            with open(_README_PATH, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return False

        lines = {line.strip() for line in content.splitlines()}
        return all(section in lines for section in sections)

    def _check_prev_report_consistency(self) -> bool:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo("Asia/Tokyo")
        except ImportError:
            from datetime import timezone
            tz = timezone.utc
        now = datetime.now(tz=tz)
        yesterday = (now - timedelta(days=1)).date()
        path = f"reports/daily/{yesterday}.md"
        return os.path.exists(path)
