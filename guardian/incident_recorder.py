import os
import re
import logging
from datetime import datetime, date
from guardian.models import Incident, CheckStatus, ErrorCode

logger = logging.getLogger(__name__)

_SLUG_PRIORITY = [
    ErrorCode.STALE_CONTENT,
    ErrorCode.DUPLICATE_CONTENT,
    ErrorCode.SERIAL_STALLED,
    ErrorCode.DAILY_POST_MISSING,
    ErrorCode.SITE_DOWN,
    ErrorCode.ACTION_FAILED,
    ErrorCode.ARTIFACT_MISSING,
    ErrorCode.ADSENSE_PAGE_MISSING,
    ErrorCode.KEYWORD_MISSING,
    ErrorCode.LINK_BROKEN,
]

_SLUG_MAP = {
    ErrorCode.STALE_CONTENT: "stale-content",
    ErrorCode.DUPLICATE_CONTENT: "duplicate-content",
    ErrorCode.SERIAL_STALLED: "serial-stalled",
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

    def create(self, results, company, content_context=None) -> Incident:
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        if not errors:
            logger.debug(
                "incident skipped target=%s reason=no_error_results",
                company["id"] if isinstance(company, dict) else company.id,
            )
            return None

        primary = self._select_primary_error(errors)
        target_name = company["name"] if isinstance(company, dict) else company.name
        target_id = company["id"] if isinstance(company, dict) else company.id
        error_codes = []
        seen = set()
        for r in errors:
            if r.error_code and r.error_code not in seen:
                error_codes.append(r.error_code)
                seen.add(r.error_code)

        phenomena = [r.detail for r in errors]
        analysis = (content_context or {}).get("analysis")
        fix = (content_context or {}).get("fix")
        verification_fix = (content_context or {}).get("verification_fix")
        executed_fix = fix.message if fix else "自動修正未実施"
        fix_result = verification_fix.message if verification_fix else (fix.message if fix and fix.status in {"FAIL", "SKIP"} else "未解決")
        next_action = ""
        if verification_fix and verification_fix.status == "FAIL":
            next_action = analysis.recommended_fix if analysis else "手動対応"
        elif fix and fix.status in {"SKIP", "FAIL"}:
            next_action = analysis.recommended_fix if analysis else "手動対応"
        elif not fix and analysis:
            next_action = analysis.recommended_fix

        logger.info(
            "target=%s incident create codes=%s cause_code=%s",
            target_id,
            ",".join(ec.value for ec in error_codes),
            analysis.cause_code if analysis else "",
        )

        return Incident(
            incident_date=date.today(),
            target_name=target_name,
            error_codes=error_codes,
            company_id=target_id,
            phenomenon=primary.detail if primary else "; ".join(phenomena),
            impact="公開サイトは到達可能だが、業務継続または品質に重大な異常あり",
            cause=analysis.cause_summary if analysis else "調査中",
            cause_code=analysis.cause_code if analysis else "",
            cause_summary=analysis.cause_summary if analysis else "",
            recommended_fix=analysis.recommended_fix if analysis else "",
            quick_fix=executed_fix or (analysis.recommended_fix if analysis else ""),
            permanent_fix_candidates=analysis.recommended_fix if analysis else "",
            result=fix_result,
            executed_fix=executed_fix,
            fix_result=fix_result,
            next_action=next_action,
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
        logger.info("incident written path=%s", path)
        return path

    def _render(self, incident: Incident) -> str:
        codes = ", ".join(ec.value for ec in incident.error_codes)
        return f"""# インシデント: {incident.target_name}

- 発生日: {incident.incident_date}
- 対象会社: {incident.target_name}
- 対象ID: {incident.company_id}
- 異常コード: {codes}

## 現象
{incident.phenomenon}

## 影響範囲
{incident.impact}

## 原因分類
{incident.cause_code}

## 原因要約
{incident.cause_summary or incident.cause}

## 推奨修正
{incident.recommended_fix or incident.permanent_fix_candidates}

## 実施した修正
{incident.executed_fix or incident.quick_fix}

## 修正結果
{incident.fix_result or incident.result}

## 次アクション
{incident.next_action}

## 原因
{incident.cause}

## 関連 countermeasure
{incident.related_countermeasure}
"""

    def _select_primary_error(self, errors):
        priorities = {code: idx for idx, code in enumerate(_SLUG_PRIORITY)}
        return sorted(
            errors,
            key=lambda r: priorities.get(r.error_code, 999) if r.error_code else 999,
        )[0]
