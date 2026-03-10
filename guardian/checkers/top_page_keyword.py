import logging
import requests
from datetime import datetime
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

logger = logging.getLogger(__name__)


class TopPageKeywordChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        site = company["site"]
        keywords = company["required_keywords"] if isinstance(company, dict) else company.required_keywords
        logger.debug("target=%s checker=top_page_keyword site=%s keyword_count=%d", company_id, site, len(keywords or []))

        if not keywords:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.TOP_PAGE_KEYWORD,
                status=CheckStatus.WARNING,
                error_code=None,
                detail="required_keywords が未設定",
                checked_at=datetime.now(),
            )

        try:
            resp = requests.get(site, timeout=10)
            text = resp.text
        except Exception as e:
            logger.debug("target=%s checker=top_page_keyword exception=\"%s\"", company_id, e)
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.TOP_PAGE_KEYWORD,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SITE_DOWN,
                detail=str(e),
                checked_at=datetime.now(),
            )

        missing = [kw for kw in keywords if kw not in text]
        if missing:
            logger.debug("target=%s checker=top_page_keyword missing=%s", company_id, ",".join(missing))
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.TOP_PAGE_KEYWORD,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.KEYWORD_MISSING,
                detail=f"欠落キーワード: {', '.join(missing)}",
                checked_at=datetime.now(),
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.TOP_PAGE_KEYWORD,
            status=CheckStatus.OK,
            error_code=None,
            detail="全キーワード確認済",
            checked_at=datetime.now(),
        )
