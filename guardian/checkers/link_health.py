import requests
from urllib.parse import urljoin, urlparse
from datetime import datetime
from guardian.config_loader import ConfigLoader
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

_SNS_DOMAINS = {
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "youtube.com", "tiktok.com", "t.co",
    "pinterest.com", "snapchat.com",
}

_EXCLUDED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico",
                        ".css", ".js", ".woff", ".woff2", ".ttf"}


class LinkHealthChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        site = company["site"]
        kind = company["kind"] if isinstance(company, dict) else company.kind.value
        link_targets = company["link_targets"] if isinstance(company, dict) else company.link_targets

        try:
            resp = requests.get(site, timeout=10)
            html = resp.text
        except Exception as e:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.LINK_HEALTH,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SITE_DOWN,
                detail=str(e),
                checked_at=datetime.now(),
            )

        anchors = self._extract_anchors(html, site, kind)
        links = [anchor["href"] for anchor in anchors]
        links = self._filter_excluded(links, site, kind)
        links = list(dict.fromkeys(links))

        # 明示指定リンクも追加
        for lt in (link_targets or []):
            if lt not in links:
                links.append(lt)

        portal_mismatches = []
        portal_missing = []
        if kind == "portal":
            anchors = [
                anchor for anchor in anchors
                if anchor["href"] in links
            ]
            portal_mismatches, portal_missing = self._collect_portal_expectations(anchors)

        broken = self._collect_broken_links(links)

        mismatch_errors = [
            mismatch for mismatch in portal_mismatches
            if mismatch["href"] in broken
        ]
        mismatch_warnings = [
            mismatch for mismatch in portal_mismatches
            if mismatch["href"] not in broken
        ]

        if broken or portal_missing or mismatch_errors:
            detail_parts = []
            if broken:
                detail_parts.append(f"リンク切れ: {', '.join(broken[:5])}")
            if portal_missing:
                missing_summary = ", ".join(
                    f"{item['name']}({item['expected_site']})" for item in portal_missing[:5]
                )
                detail_parts.append(f"ポータル掲載漏れ: {missing_summary}")
            if mismatch_errors:
                mismatch_error_summary = ", ".join(
                    f"{item['name']}({item['href']})" for item in mismatch_errors[:5]
                )
                detail_parts.append(f"ポータルリンク不達: {mismatch_error_summary}")
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.LINK_HEALTH,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.LINK_BROKEN,
                detail=" / ".join(detail_parts),
                checked_at=datetime.now(),
            )

        if mismatch_warnings:
            mismatch_summary = ", ".join(
                f"{item['name']}({item['href']} != {item['expected_site']})"
                for item in mismatch_warnings[:5]
            )
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.LINK_HEALTH,
                status=CheckStatus.WARNING,
                error_code=ErrorCode.PORTAL_LINK_MISMATCH,
                detail=f"ポータルリンク差異: {mismatch_summary}",
                checked_at=datetime.now(),
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.LINK_HEALTH,
            status=CheckStatus.OK,
            error_code=None,
            detail="リンク正常",
            checked_at=datetime.now(),
        )

    def _extract_anchors(self, html: str, base_url: str, kind: str) -> list:
        import re
        matches = re.findall(
            r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        base_parsed = urlparse(base_url)
        result = []
        for href, inner_html in matches:
            if href.startswith("mailto:") or href.startswith("javascript:") or href.startswith("#"):
                continue
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)

            # virtual_company は同一オリジンのみ
            if kind == "virtual_company":
                if parsed.netloc != base_parsed.netloc:
                    continue

            # 拡張子フィルタ
            path_lower = parsed.path.lower()
            if any(path_lower.endswith(ext) for ext in _EXCLUDED_EXTENSIONS):
                continue

            text = re.sub(r"<[^>]+>", " ", inner_html)
            text = re.sub(r"\s+", " ", text).strip()
            result.append({"href": absolute, "text": text})
        return result

    def _filter_excluded(self, links: list, base_url: str, kind: str) -> list:
        result = []
        for link in links:
            parsed = urlparse(link)
            netloc = parsed.netloc.lower()
            # SNS 除外
            if any(netloc == sns or netloc.endswith("." + sns) for sns in _SNS_DOMAINS):
                continue
            # クエリ付きトラッキングリンク除外（utm_ 等）
            if "utm_" in (parsed.query or ""):
                continue
            result.append(link)
        return result

    def _collect_broken_links(self, links: list) -> list:
        broken = []
        for link in links:
            try:
                r = requests.get(link, timeout=10, allow_redirects=True)
                if r.status_code >= 400:
                    broken.append(link)
            except Exception:
                broken.append(link)
        return broken

    def _collect_portal_expectations(self, anchors: list) -> tuple:
        mismatches = []
        missing = []
        for target in self._load_expected_portal_targets():
            match_type, anchor = self._find_portal_match(anchors, target)
            if match_type == "exact":
                continue
            if match_type == "mismatch":
                mismatches.append({
                    "name": target["name"],
                    "expected_site": target["site"],
                    "href": anchor["href"],
                })
                continue
            missing.append({
                "name": target["name"],
                "expected_site": target["site"],
            })
        return mismatches, missing

    def _load_expected_portal_targets(self) -> list:
        loader = ConfigLoader()
        companies = loader.load("companies/companies.yaml")
        return [
            {"name": company.name, "site": company.site}
            for company in companies
            if company.kind and company.kind.value == "virtual_company"
            and company.enabled
            and company.portal_visible
            and company.site
        ]

    def _find_portal_match(self, anchors: list, target: dict) -> tuple:
        expected_site = target["site"]
        target_name = target["name"].lower()
        exact_anchor = next(
            (
                anchor for anchor in anchors
                if self._normalized_portal_url(anchor["href"]) == self._normalized_portal_url(expected_site)
            ),
            None,
        )
        if exact_anchor is not None:
            return "exact", exact_anchor

        named_anchor = next(
            (
                anchor for anchor in anchors
                if target_name in (anchor.get("text", "").lower())
            ),
            None,
        )
        if named_anchor is not None:
            return "mismatch", named_anchor

        return "missing", None

    def _normalized_portal_url(self, url: str) -> tuple:
        parsed = urlparse(url)
        path = parsed.path or "/"
        if path.lower().endswith("/index.html"):
            path = path[:-11] or "/"
        if path != "/":
            path = path.rstrip("/") or "/"
        return (
            parsed.netloc.lower(),
            path.lower(),
            parsed.query,
        )
