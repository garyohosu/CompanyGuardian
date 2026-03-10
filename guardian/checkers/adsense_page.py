import logging
import requests
from datetime import datetime
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

logger = logging.getLogger(__name__)


class AdSensePageChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        site = company["site"] if isinstance(company, dict) else company.site
        pages = company["required_adsense_pages"] if isinstance(company, dict) else company.required_adsense_pages
        marker = company["adsense_marker_keyword"] if isinstance(company, dict) else company.adsense_marker_keyword
        logger.debug("target=%s checker=adsense_pages site=%s page_count=%d", company_id, site, len(pages or []))

        if not pages:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.ADSENSE_PAGES,
                status=CheckStatus.WARNING,
                error_code=None,
                detail="required_adsense_pages 未設定",
                checked_at=datetime.now(),
            )

        missing_pages = []
        marker_missing = False
        last_text = ""

        for page_path in pages:
            url = (site or "").rstrip("/") + page_path
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code >= 400:
                    missing_pages.append(page_path)
                else:
                    last_text = resp.text
            except Exception:
                missing_pages.append(page_path)
                logger.debug("target=%s checker=adsense_pages missing_page=%s", company_id, page_path)

        if missing_pages:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.ADSENSE_PAGES,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.ADSENSE_PAGE_MISSING,
                detail=f"ページ欠落: {', '.join(missing_pages)}",
                checked_at=datetime.now(),
            )

        # マーカー確認（任意・WARNING のみ）
        if marker:
            # 全ページのテキストでマーカーを確認（簡易：最後のページのみ）
            all_texts = []
            for page_path in pages:
                url = (site or "").rstrip("/") + page_path
                try:
                    resp = requests.get(url, timeout=10)
                    all_texts.append(resp.text)
                except Exception:
                    pass
            combined = " ".join(all_texts)
            if marker not in combined:
                marker_missing = True

        if marker_missing:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.ADSENSE_PAGES,
                status=CheckStatus.WARNING,
                error_code=None,
                detail=f"AdSense マーカー '{marker}' が未確認",
                checked_at=datetime.now(),
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.ADSENSE_PAGES,
            status=CheckStatus.OK,
            error_code=None,
            detail="AdSense 必須ページ確認済",
            checked_at=datetime.now(),
        )
