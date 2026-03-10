import logging
from datetime import datetime, date, timedelta
from guardian.content_inspector import ContentInspector
from guardian.content_state import ContentStateStore
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

logger = logging.getLogger(__name__)


class DailyPostChecker:
    def __init__(self):
        self._inspector = ContentInspector()
        self._state_store = ContentStateStore()

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        strategies = company["daily_post_strategy"] if isinstance(company, dict) else company.daily_post_strategy
        locator = company["daily_post_locator"] if isinstance(company, dict) else company.daily_post_locator
        rule = company["daily_post_rule"] if isinstance(company, dict) else getattr(company, "daily_post_rule", {})
        logger.debug("target=%s checker=daily_post_previous_day strategy_count=%d rule=%s", company_id, len(strategies or []), "yes" if rule else "no")

        if rule:
            return self._check_with_rule(company, rule)

        if not strategies:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.DAILY_POST_PREVIOUS_DAY,
                status=CheckStatus.WARNING,
                error_code=None,
                detail="daily_post_strategy 未設定",
                checked_at=datetime.now(),
            )

        yesterday = self._resolve_previous_day_jst()

        for strategy in strategies:
            result = self._check_strategy(strategy, locator, yesterday, company_id)
            if result.status == CheckStatus.OK:
                return result

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.DAILY_POST_PREVIOUS_DAY,
            status=CheckStatus.ERROR,
            error_code=ErrorCode.DAILY_POST_MISSING,
            detail=f"前日({yesterday})投稿が確認できない",
            checked_at=datetime.now(),
        )

    def _check_with_rule(self, company, rule: dict) -> CheckResult:
        company_id = company["id"] if isinstance(company, dict) else company.id
        yesterday = self._resolve_previous_day(rule)
        now = datetime.now()
        entries = self._inspector.fetch_entries(company, rule, limit=int((rule or {}).get("entry_limit", 5)))
        logger.debug("target=%s checker=daily_post_previous_day expected_date=%s fetched_entries=%d", company_id, yesterday.isoformat(), len(entries))
        latest = entries[0] if entries else None
        if latest is not None:
            self._state_store.update_target(company_id, latest, now)

        for entry in entries:
            if entry.published_on == yesterday:
                return CheckResult(
                    company_id=company_id,
                    check_kind=CheckKind.DAILY_POST_PREVIOUS_DAY,
                    status=CheckStatus.OK,
                    error_code=None,
                    detail=(rule or {}).get("ok_message", "前日投稿確認済"),
                    checked_at=now,
                    context={
                        "latest_date": latest.published_on.isoformat() if latest and latest.published_on else "",
                        "latest_url": latest.url if latest else "",
                    },
                )

        label = (rule or {}).get("label", "前日投稿")
        template = (rule or {}).get(
            "missing_message_template",
            "{label}が {expected_date} 分で欠落",
        )
        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.DAILY_POST_PREVIOUS_DAY,
            status=CheckStatus.ERROR,
            error_code=ErrorCode.DAILY_POST_MISSING,
            detail=template.format(label=label, expected_date=yesterday.isoformat()),
            checked_at=now,
            context={
                "expected_date": yesterday.isoformat(),
                "latest_date": latest.published_on.isoformat() if latest and latest.published_on else "",
                "latest_url": latest.url if latest else "",
                "latest_title": latest.title if latest else "",
            },
        )

    def _resolve_previous_day_jst(self) -> date:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo("Asia/Tokyo")
        except ImportError:
            from datetime import timezone
            tz = timezone.utc
        now = datetime.now(tz=tz)
        return (now - timedelta(days=1)).date()

    def _resolve_previous_day(self, rule: dict) -> date:
        timezone_name = (rule or {}).get("timezone", "Asia/Tokyo")
        try:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(timezone_name)
        except Exception:
            from datetime import timezone

            tz = timezone.utc
        now = datetime.now(tz=tz)
        return (now - timedelta(days=1)).date()

    def _check_strategy(self, strategy, locator, yesterday: date, company_id: str) -> CheckResult:
        strategy_str = str(strategy)
        if strategy_str == "feed_xml":
            return self._check_feed_xml(locator, yesterday, company_id)
        elif strategy_str == "site_path_pattern":
            return self._check_site_path_pattern(locator, yesterday, company_id)
        elif strategy_str == "sitemap_xml":
            return self._check_sitemap_xml(locator, yesterday, company_id)
        elif strategy_str == "index_page_keyword":
            return self._check_index_page_keyword(locator, yesterday, company_id)
        else:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.DAILY_POST_PREVIOUS_DAY,
                status=CheckStatus.WARNING,
                error_code=None,
                detail=f"未知の戦略: {strategy_str}",
                checked_at=datetime.now(),
            )

    def _check_feed_xml(self, locator, yesterday: date, company_id: str) -> CheckResult:
        import requests
        if not locator:
            return self._ng(company_id, "feed_xml locator 未設定")
        feed_url = locator.get("feed_url") if isinstance(locator, dict) else locator.feed_url
        if not feed_url:
            return self._ng(company_id, "feed_url 未設定")
        try:
            resp = requests.get(feed_url, timeout=10)
            text = resp.text
            date_str = yesterday.strftime("%Y-%m-%d")
            if date_str in text:
                return self._ok(company_id)
        except Exception:
            pass
        return self._ng(company_id, "feed_xml で前日エントリ未確認")

    def _check_site_path_pattern(self, locator, yesterday: date, company_id: str) -> CheckResult:
        import requests
        if not locator:
            return self._ng(company_id, "site_path_pattern locator 未設定")
        pattern = locator.get("path_pattern") if isinstance(locator, dict) else getattr(locator, "path_pattern", None)
        if not pattern:
            return self._ng(company_id, "path_pattern 未設定")
        path = pattern.replace("{yyyy}", yesterday.strftime("%Y"))\
                      .replace("{mm}", yesterday.strftime("%m"))\
                      .replace("{dd}", yesterday.strftime("%d"))
        try:
            resp = requests.get(path, timeout=10)
            if resp.status_code < 400:
                return self._ok(company_id)
        except Exception:
            pass
        return self._ng(company_id, f"site_path_pattern {path} 未確認")

    def _check_sitemap_xml(self, locator, yesterday: date, company_id: str) -> CheckResult:
        import requests
        if not locator:
            return self._ng(company_id, "sitemap_xml locator 未設定")
        sitemap_url = locator.get("sitemap_url") if isinstance(locator, dict) else getattr(locator, "sitemap_url", None)
        if not sitemap_url:
            return self._ng(company_id, "sitemap_url 未設定")
        try:
            resp = requests.get(sitemap_url, timeout=10)
            date_str = yesterday.strftime("%Y-%m-%d")
            if date_str in resp.text:
                return self._ok(company_id)
        except Exception:
            pass
        return self._ng(company_id, "sitemap_xml で前日エントリ未確認")

    def _check_index_page_keyword(self, locator, yesterday: date, company_id: str) -> CheckResult:
        import requests
        if not locator:
            return self._ng(company_id, "index_page_keyword locator 未設定")
        index_url = locator.get("index_url") if isinstance(locator, dict) else getattr(locator, "index_url", None)
        keyword_pattern = locator.get("keyword_pattern") if isinstance(locator, dict) else getattr(locator, "keyword_pattern", None)
        if not index_url:
            return self._ng(company_id, "index_url 未設定")
        try:
            resp = requests.get(index_url, timeout=10)
            date_str = yesterday.strftime("%Y-%m-%d")
            if date_str in resp.text or (keyword_pattern and keyword_pattern in resp.text):
                return self._ok(company_id)
        except Exception:
            pass
        return self._ng(company_id, "index_page_keyword で前日キーワード未確認")

    def _ok(self, company_id: str) -> CheckResult:
        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.DAILY_POST_PREVIOUS_DAY,
            status=CheckStatus.OK,
            error_code=None,
            detail="前日投稿確認済",
            checked_at=datetime.now(),
        )

    def _ng(self, company_id: str, detail: str) -> CheckResult:
        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.DAILY_POST_PREVIOUS_DAY,
            status=CheckStatus.ERROR,
            error_code=ErrorCode.DAILY_POST_MISSING,
            detail=detail,
            checked_at=datetime.now(),
        )
