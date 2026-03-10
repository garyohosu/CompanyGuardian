import logging
from datetime import datetime

from guardian.content_inspector import ContentInspector
from guardian.content_state import ContentStateStore
from guardian.models import CheckKind, CheckResult, CheckStatus, ErrorCode

logger = logging.getLogger(__name__)


class LatestPostUniquenessChecker:
    def __init__(self):
        self._inspector = ContentInspector()
        self._state_store = ContentStateStore()

    def check(self, company) -> CheckResult:
        company_id = company["id"] if isinstance(company, dict) else company.id
        rule = company["uniqueness_rule"] if isinstance(company, dict) else company.uniqueness_rule
        now = datetime.now()
        entries = self._inspector.fetch_entries(company, rule, limit=2)
        logger.debug("target=%s checker=latest_post_uniqueness fetched_entries=%d", company_id, len(entries))

        if not entries:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.LATEST_POST_UNIQUENESS,
                status=CheckStatus.WARNING,
                error_code=None,
                detail=(rule or {}).get("missing_message", "重複判定に必要な投稿を取得できない"),
                checked_at=now,
                context={},
            )

        self._state_store.update_target(company_id, entries[0], now)

        if len(entries) < 2:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.LATEST_POST_UNIQUENESS,
                status=CheckStatus.WARNING,
                error_code=None,
                detail=(rule or {}).get("insufficient_message", "比較対象が 2 件未満のため重複判定保留"),
                checked_at=now,
                context={},
            )

        latest, previous = entries[0], entries[1]
        duplicate_fields = self._duplicate_fields(latest, previous, rule)
        logger.debug("target=%s checker=latest_post_uniqueness duplicate_fields=%s", company_id, ",".join(duplicate_fields) if duplicate_fields else "none")
        context = {
            "latest_date": latest.published_on.isoformat() if latest.published_on else "",
            "previous_date": previous.published_on.isoformat() if previous.published_on else "",
            "latest_url": latest.url,
            "previous_url": previous.url,
            "latest_title": latest.title,
            "previous_title": previous.title,
            "latest_content_hash": latest.content_hash,
            "previous_content_hash": previous.content_hash,
            "duplicate_fields": duplicate_fields,
        }

        if duplicate_fields:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.LATEST_POST_UNIQUENESS,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.DUPLICATE_CONTENT,
                detail=self._detail(latest, previous, rule),
                checked_at=now,
                context=context,
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.LATEST_POST_UNIQUENESS,
            status=CheckStatus.OK,
            error_code=None,
            detail=(rule or {}).get("ok_message", "最新 2 件の重複なし"),
            checked_at=now,
            context=context,
        )

    def _duplicate_fields(self, latest, previous, rule: dict) -> list[str]:
        compare_fields = list((rule or {}).get("compare_fields", []) or ["title", "content_hash"])
        matches = []
        for field_name in compare_fields:
            latest_value = getattr(latest, field_name, None)
            previous_value = getattr(previous, field_name, None)
            if latest_value and previous_value and latest_value == previous_value:
                matches.append(field_name)
        return matches

    def _detail(self, latest, previous, rule: dict) -> str:
        template = (rule or {}).get(
            "duplicate_message_template",
            "{previous_date} と {latest_date} の投稿内容が重複",
        )
        return template.format(
            latest_date=latest.published_on.isoformat() if latest.published_on else "",
            previous_date=previous.published_on.isoformat() if previous.published_on else "",
        )
