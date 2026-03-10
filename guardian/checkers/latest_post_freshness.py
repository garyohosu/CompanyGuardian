import logging
from datetime import datetime, timedelta

from guardian.content_inspector import ContentInspector
from guardian.content_state import ContentStateStore
from guardian.models import CheckKind, CheckResult, CheckStatus, ErrorCode

logger = logging.getLogger(__name__)


class LatestPostFreshnessChecker:
    def __init__(self):
        self._inspector = ContentInspector()
        self._state_store = ContentStateStore()

    def check(self, company) -> CheckResult:
        company_id = company["id"] if isinstance(company, dict) else company.id
        rule = company["freshness_rule"] if isinstance(company, dict) else company.freshness_rule
        latest = next(iter(self._inspector.fetch_entries(company, rule, limit=1)), None)
        now = self._now(rule)
        logger.debug("target=%s checker=latest_post_freshness latest=%s", company_id, latest.published_on.isoformat() if latest and latest.published_on else "none")

        if latest is None or latest.published_on is None:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.LATEST_POST_FRESHNESS,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.STALE_CONTENT,
                detail=(rule or {}).get("missing_message", "最新公開日の取得に失敗"),
                checked_at=now,
                context={},
            )

        self._state_store.update_target(company_id, latest, now)
        max_age_days = int((rule or {}).get("max_age_days", 1))
        age_days = (now.date() - latest.published_on).days
        context = {
            "latest_date": latest.published_on.isoformat(),
            "latest_url": latest.url,
            "latest_title": latest.title,
            "observed_age_days": age_days,
        }

        if age_days > max_age_days:
            label = (rule or {}).get("label", "最新投稿")
            template = (rule or {}).get("stale_message_template", "{label}が {latest_date} で停止")
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.LATEST_POST_FRESHNESS,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.STALE_CONTENT,
                detail=template.format(label=label, latest_date=latest.published_on.isoformat()),
                checked_at=now,
                context=context,
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.LATEST_POST_FRESHNESS,
            status=CheckStatus.OK,
            error_code=None,
            detail=(rule or {}).get("ok_message", "最新投稿の鮮度は正常"),
            checked_at=now,
            context=context,
        )

    def _now(self, rule: dict) -> datetime:
        timezone_name = (rule or {}).get("timezone", "Asia/Tokyo")
        try:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(timezone_name)
            return datetime.now(tz=tz).replace(tzinfo=None)
        except Exception:
            return datetime.now()
