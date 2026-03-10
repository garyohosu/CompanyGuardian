import logging
from datetime import datetime

from guardian.content_inspector import ContentInspector
from guardian.content_state import ContentStateStore
from guardian.models import CheckKind, CheckResult, CheckStatus, ErrorCode

logger = logging.getLogger(__name__)


class SerialProgressChecker:
    def __init__(self):
        self._inspector = ContentInspector()
        self._state_store = ContentStateStore()

    def check(self, company) -> CheckResult:
        company_id = company["id"] if isinstance(company, dict) else company.id
        rule = company["serial_rule"] if isinstance(company, dict) else company.serial_rule
        now = self._now(rule)
        latest = self._inspector.fetch_serial_entry(company, rule)
        logger.debug("target=%s checker=serial_progress latest_progress=%s", company_id, latest.progress_value if latest else None)

        if latest is None or latest.progress_value is None:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.SERIAL_PROGRESS,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SERIAL_STALLED,
                detail=(rule or {}).get("missing_message", "連載 progress の取得に失敗"),
                checked_at=now,
                context={},
            )

        state = self._state_store.get_target_state(company_id)
        display_progress = latest.progress_value + int((rule or {}).get("progress_display_offset", 0))
        stagnant_days = int((rule or {}).get("stagnant_days", 2))
        expected_min = (rule or {}).get("expected_min_progress_value")
        stalled = False
        reason = ""

        if expected_min is not None and latest.progress_value < int(expected_min):
            stalled = True
            reason = "expected_min_progress_value"

        latest_age_days = None
        if latest.published_on is not None:
            latest_age_days = (now.date() - latest.published_on).days
            if latest_age_days > stagnant_days:
                stalled = True
                reason = reason or "published_on_stale"

        previous_progress = state.get("last_seen_progress_value")
        last_changed_at = state.get("last_progress_changed_at") or state.get("last_checked_at")
        unchanged_days = self._days_since(last_changed_at, now)
        if previous_progress == latest.progress_value and unchanged_days is not None and unchanged_days >= stagnant_days:
            stalled = True
            reason = reason or "progress_unchanged"
        logger.debug("target=%s checker=serial_progress previous_progress=%s unchanged_days=%s reason=%s", company_id, previous_progress, unchanged_days, reason)

        self._state_store.update_target(company_id, latest, now)

        context = {
            "progress_value": latest.progress_value,
            "display_progress_value": display_progress,
            "latest_date": latest.published_on.isoformat() if latest.published_on else "",
            "latest_url": latest.url,
            "stagnant_days": stagnant_days,
            "unchanged_days": unchanged_days,
            "reason": reason,
        }

        if stalled:
            template = (rule or {}).get(
                "stalled_message_template",
                "{label}第{display_progress_value}章から進行停止",
            )
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.SERIAL_PROGRESS,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SERIAL_STALLED,
                detail=template.format(
                    label=(rule or {}).get("label", ""),
                    display_progress_value=display_progress,
                    progress_value=latest.progress_value,
                ),
                checked_at=now,
                context=context,
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.SERIAL_PROGRESS,
            status=CheckStatus.OK,
            error_code=None,
            detail=(rule or {}).get("ok_message", "連載 progress は前進中"),
            checked_at=now,
            context=context,
        )

    def _days_since(self, iso_text: str | None, now: datetime) -> int | None:
        if not iso_text:
            return None
        try:
            value = datetime.fromisoformat(iso_text)
            return (now - value).days
        except Exception:
            return None

    def _now(self, rule: dict) -> datetime:
        timezone_name = (rule or {}).get("timezone", "Asia/Tokyo")
        try:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(timezone_name)
            return datetime.now(tz=tz).replace(tzinfo=None)
        except Exception:
            return datetime.now()
