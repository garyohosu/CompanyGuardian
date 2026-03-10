import os
import re
from datetime import datetime, date
from guardian.models import Incident, CheckStatus, ErrorCode

_SLUG_PRIORITY = [
    ErrorCode.SITE_DOWN,
    ErrorCode.ACTION_FAILED,
    ErrorCode.ARTIFACT_MISSING,
    ErrorCode.DAILY_POST_MISSING,
    ErrorCode.ADSENSE_PAGE_MISSING,
    ErrorCode.KEYWORD_MISSING,
    ErrorCode.LINK_BROKEN,
]

_SLUG_MAP = {
    ErrorCode.SITE_DOWN: "site-down",
    ErrorCode.ACTION_FAILED: "action-failed",
    ErrorCode.ARTIFACT_MISSING: "artifact-missing",
    ErrorCode.DAILY_POST_MISSING: "daily-post-missing",
    ErrorCode.ADSENSE_PAGE_MISSING: "adsense-page-missing",
    ErrorCode.KEYWORD_MISSING: "keyword-missing",
    ErrorCode.LINK_BROKEN: "link-broken",
    ErrorCode.CONFIG_INVALID: "config-invalid",
    ErrorCode.SELF_CHECK_FAILED: "self-check-failed",
    ErrorCode.REPORT_MISSING: "report-missing",
    ErrorCode.UNKNOWN_ERROR: "unknown-error",
}


def _slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


def _primary_slug(error_codes) -> str:
    for ec in _SLUG_PRIORITY:
        if ec in error_codes:
            return _SLUG_MAP[ec]
    if error_codes:
        return _SLUG_MAP.get(error_codes[0], "unknown-error")
    return "unknown-error"


class IncidentRecorder:

    def create(self, results, company) -> Incident:
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        if not errors:
            return None

        target_name = company["name"] if isinstance(company, dict) else company.name
        error_codes = []
        seen = set()
        for r in errors:
            if r.error_code and r.error_code not in seen:
                error_codes.append(r.error_code)
                seen.add(r.error_code)

        phenomena = [r.detail for r in errors]

        return Incident(
            incident_date=date.today(),
            target_name=target_name,
            error_codes=error_codes,
            phenomenon="; ".join(phenomena),
            impact="",
            cause="調査中",
            quick_fix="",
            permanent_fix_candidates="",
            result="",
            related_countermeasure="",
        )

    def save(self, incident: Incident) -> str:
        target_slug = _slugify(incident.target_name)
        error_slug = _primary_slug(incident.error_codes)
        date_str = incident.incident_date.strftime("%Y-%m-%d")
        filename = f"{date_str}-{target_slug}-{error_slug}.md"
        path = f"incidents/{filename}"

        os.makedirs("incidents", exist_ok=True)
        content = self._render(incident)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        incident.file_path = path
        return path

    def _render(self, incident: Incident) -> str:
        codes = ", ".join(ec.value for ec in incident.error_codes)
        return f"""# インシデント: {incident.target_name}

- 発生日: {incident.incident_date}
- 対象: {incident.target_name}
- 異常区分: {codes}

## 現象
{incident.phenomenon}

## 影響範囲
{incident.impact}

## 原因
{incident.cause}

## 応急対策
{incident.quick_fix}

## 恒久対策候補
{incident.permanent_fix_candidates}

## 結果
{incident.result}

## 関連 countermeasure
{incident.related_countermeasure}
"""
