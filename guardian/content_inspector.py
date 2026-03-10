import hashlib
import html
import json
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import requests

from guardian.models import ContentEntry


class ContentInspector:
    """公開サイトや公開 state から content 状態を抽出する。"""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def fetch_entries(self, company, rule: dict, limit: int = 5) -> list[ContentEntry]:
        source_type = (rule or {}).get("source_type", "html_regex")
        if source_type == "json":
            entries = self._entries_from_json(company, rule)
        else:
            entries = self._entries_from_html(company, rule)

        entries = self._dedupe_entries(entries)
        entries.sort(
            key=lambda e: (
                e.published_on or date.min,
                e.progress_value or -1,
                e.url,
            ),
            reverse=True,
        )

        compare_fields = set((rule or {}).get("compare_fields", []) or [])
        if (rule or {}).get("fetch_content_hash") or "content_hash" in compare_fields:
            self.populate_content_hashes(entries[:limit])

        return entries[:limit]

    def fetch_serial_entry(self, company, rule: dict) -> ContentEntry | None:
        source_type = (rule or {}).get("source_type", "json")
        if source_type == "json":
            return self._serial_entry_from_json(company, rule)
        entries = self._entries_from_html(company, rule)
        return entries[0] if entries else None

    def populate_content_hashes(self, entries: list[ContentEntry]) -> None:
        for entry in entries:
            if entry.content_hash:
                continue
            if not entry.url:
                continue
            try:
                response = requests.get(
                    entry.url,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                entry.fetch_status = response.status_code
                if response.status_code >= 400:
                    continue
                text = self._normalize_page_text(response.text)
                entry.content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if not entry.excerpt:
                    entry.excerpt = text[:180]
            except Exception:
                entry.fetch_status = None

    def _entries_from_html(self, company, rule: dict) -> list[ContentEntry]:
        source_url = self._source_url(company, rule)
        if not source_url:
            return []
        entry_regex = (rule or {}).get("entry_regex")
        if not entry_regex:
            return []
        text = self._fetch_text(source_url)
        if text is None:
            return []

        flags = re.IGNORECASE | re.DOTALL
        entries = []
        for match in re.finditer(entry_regex, text, flags):
            groups = match.groupdict()
            raw_url = groups.get("url", "")
            parsed_date = self._parse_entry_date(groups, rule)
            title = self._clean_text(groups.get("title", ""))
            excerpt = self._clean_text(groups.get("excerpt", ""))
            progress_value = self._parse_int(groups.get("progress"))
            entry = ContentEntry(
                url=urljoin(source_url, raw_url) if raw_url else "",
                title=title,
                published_on=parsed_date,
                excerpt=excerpt,
                slug=self._slug_from_url(raw_url),
                progress_value=progress_value,
            )
            entries.append(entry)
        return entries

    def _entries_from_json(self, company, rule: dict) -> list[ContentEntry]:
        source_url = self._source_url(company, rule)
        if not source_url:
            return []
        text = self._fetch_text(source_url)
        if text is None:
            return []
        try:
            payload = json.loads(text)
        except Exception:
            return []

        items_path = (rule or {}).get("items_path")
        if not items_path:
            return []
        items = self._extract_json_path(payload, items_path)
        if not isinstance(items, list):
            return []

        entries = []
        for item in items:
            if not isinstance(item, dict):
                continue
            date_value = self._extract_json_path(item, (rule or {}).get("date_path", "date"))
            parsed_date = self._parse_date(date_value, rule)
            raw_url = self._extract_json_path(item, (rule or {}).get("url_path", "url")) or ""
            title = self._clean_text(
                self._extract_json_path(item, (rule or {}).get("title_path", "title")) or ""
            )
            excerpt = self._clean_text(
                self._extract_json_path(item, (rule or {}).get("excerpt_path", "excerpt")) or ""
            )
            progress_value = self._parse_int(
                self._extract_json_path(item, (rule or {}).get("progress_path", "progress"))
            )
            entries.append(
                ContentEntry(
                    url=urljoin(source_url, raw_url) if raw_url else "",
                    title=title,
                    published_on=parsed_date,
                    excerpt=excerpt,
                    slug=self._slug_from_url(raw_url),
                    progress_value=progress_value,
                )
            )
        return entries

    def _serial_entry_from_json(self, company, rule: dict) -> ContentEntry | None:
        source_url = self._source_url(company, rule)
        if not source_url:
            return None
        text = self._fetch_text(source_url)
        if text is None:
            return None
        try:
            payload = json.loads(text)
        except Exception:
            return None

        progress_value = self._parse_int(
            self._extract_json_path(payload, (rule or {}).get("progress_path", "progress"))
        )
        latest_date = self._parse_date(
            self._extract_json_path(payload, (rule or {}).get("date_path", "date")),
            rule,
        )
        url_template = (rule or {}).get("url_template", "")
        url = url_template.format(progress_value=progress_value) if url_template and progress_value is not None else ""
        title = (rule or {}).get("work_label", "")
        return ContentEntry(
            url=urljoin(self._company_site(company), url) if url else self._company_site(company),
            title=title,
            published_on=latest_date,
            slug=self._slug_from_url(url),
            progress_value=progress_value,
        )

    def _source_url(self, company, rule: dict) -> str:
        if (rule or {}).get("source_url"):
            return rule["source_url"]
        return self._company_site(company)

    def _company_site(self, company) -> str:
        return company["site"] if isinstance(company, dict) else company.site

    def _headers(self) -> dict:
        return {"User-Agent": "CompanyGuardian"}

    def _fetch_text(self, url: str) -> str | None:
        try:
            response = requests.get(url, headers=self._headers(), timeout=self.timeout)
            if response.status_code >= 400:
                return None
            return response.text
        except Exception:
            return None

    def _parse_entry_date(self, groups: dict, rule: dict) -> date | None:
        raw_date = groups.get("date")
        if raw_date:
            return self._parse_date(raw_date, rule)
        year = groups.get("year")
        month = groups.get("month")
        day = groups.get("day")
        if year and month and day:
            try:
                return date(int(year), int(month), int(day))
            except Exception:
                return None
        return None

    def _parse_date(self, raw_value, rule: dict) -> date | None:
        if raw_value in (None, ""):
            return None
        if isinstance(raw_value, date):
            return raw_value

        raw = str(raw_value).strip()
        formats = (rule or {}).get("date_formats") or [(rule or {}).get("date_format", "%Y-%m-%d")]
        if isinstance(formats, str):
            formats = [formats]

        for fmt in formats:
            try:
                return datetime.strptime(raw[: len(datetime.now().strftime(fmt))], fmt).date()
            except Exception:
                continue

        iso_like = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
        if iso_like:
            try:
                return datetime.strptime(iso_like.group(1), "%Y-%m-%d").date()
            except Exception:
                return None
        return None

    def _extract_json_path(self, payload, path: str):
        if not path:
            return None
        current = payload
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _clean_text(self, value: str) -> str:
        if not value:
            return ""
        text = re.sub(r"<[^>]+>", " ", value)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_page_text(self, text: str) -> str:
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _slug_from_url(self, value: str) -> str:
        if not value:
            return ""
        parsed = urlparse(value)
        path = parsed.path.rstrip("/")
        if not path:
            return ""
        slug = path.split("/")[-1]
        if slug == "index" and "/" in path:
            slug = path.split("/")[-2]
        return slug

    def _parse_int(self, value) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(str(value))
        except Exception:
            return None

    def _dedupe_entries(self, entries: list[ContentEntry]) -> list[ContentEntry]:
        seen = set()
        output = []
        for entry in entries:
            key = (
                entry.url,
                entry.published_on.isoformat() if entry.published_on else "",
                entry.title,
                entry.progress_value,
            )
            if key in seen:
                continue
            seen.add(key)
            output.append(entry)
        return output
