import logging
import requests
from datetime import datetime
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

logger = logging.getLogger(__name__)


class SiteHttpChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        site = company["site"]
        logger.debug("target=%s checker=site_http site=%s", company_id, site)
        try:
            resp = requests.get(site, timeout=10, allow_redirects=False)
            code = resp.status_code
            if 200 <= code < 300:
                status = CheckStatus.OK
                error_code = None
                detail = f"HTTP {code}"
            elif 300 <= code < 400:
                status = CheckStatus.WARNING
                error_code = None
                detail = f"HTTP {code} (redirect)"
            else:
                status = CheckStatus.ERROR
                error_code = ErrorCode.SITE_DOWN
                detail = f"HTTP {code}"
        except Exception as e:
            status = CheckStatus.ERROR
            error_code = ErrorCode.SITE_DOWN
            detail = str(e)
            logger.debug("target=%s checker=site_http exception=\"%s\"", company_id, e)

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.SITE_HTTP,
            status=status,
            error_code=error_code,
            detail=detail,
            checked_at=datetime.now(),
        )
