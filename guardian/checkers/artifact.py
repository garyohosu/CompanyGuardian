import logging
import requests
from datetime import datetime
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

logger = logging.getLogger(__name__)


class ArtifactChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        site = company["site"] if isinstance(company, dict) else company.site
        artifacts = company["required_artifacts"] if isinstance(company, dict) else company.required_artifacts
        logger.debug("target=%s checker=artifact site=%s artifact_count=%d", company_id, site, len(artifacts or []))

        if not artifacts:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.ARTIFACT,
                status=CheckStatus.WARNING,
                error_code=None,
                detail="required_artifacts 未設定",
                checked_at=datetime.now(),
            )

        normalized = self._normalize_paths(artifacts)
        missing = []
        has_unsupported = False

        for artifact in normalized:
            atype, apath = artifact
            if atype == "site_path":
                url = (site or "").rstrip("/") + apath
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code >= 400:
                        missing.append(apath)
                except Exception:
                    missing.append(apath)
                    logger.debug("target=%s checker=artifact missing_path=%s", company_id, apath)
            else:
                has_unsupported = True

        if missing:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.ARTIFACT,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.ARTIFACT_MISSING,
                detail=f"成果物欠落: {', '.join(missing)}",
                checked_at=datetime.now(),
            )

        if has_unsupported and not missing:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.ARTIFACT,
                status=CheckStatus.WARNING,
                error_code=None,
                detail="未サポートの artifact type をスキップ",
                checked_at=datetime.now(),
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.ARTIFACT,
            status=CheckStatus.OK,
            error_code=None,
            detail="全成果物確認済",
            checked_at=datetime.now(),
        )

    def _normalize_paths(self, artifacts) -> list:
        result = []
        for a in artifacts:
            if isinstance(a, dict):
                atype = a.get("type", "site_path")
                apath = a.get("path", "")
            else:
                atype = a.type.value
                apath = a.path
            result.append((atype, apath))
        return result
