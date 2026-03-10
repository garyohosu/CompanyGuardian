import yaml
from guardian.models import (
    Company, CompanyKind, CheckKind, RequiredArtifact, ArtifactType,
    DailyPostLocator, _CheckKindStr,
)


class ConfigLoader:

    def load(self, path: str) -> list:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        companies = []
        for item in (data or {}).get("companies", []):
            company = self._parse_company(item)
            companies.append(company)
        return companies

    def _parse_company(self, item: dict) -> Company:
        kind_str = item.get("kind", "")
        try:
            kind = CompanyKind(kind_str)
        except ValueError:
            kind = None

        checks = []
        for ck_str in item.get("checks", []):
            checks.append(_CheckKindStr(ck_str))

        # required_artifacts
        raw_artifacts = list(item.get("required_artifacts", []))

        # required_paths → required_artifacts(site_path) に変換（後方互換）
        existing_site_paths = {
            a["path"] if isinstance(a, dict) else a.path
            for a in raw_artifacts
        }
        for path_str in item.get("required_paths", []):
            if path_str not in existing_site_paths:
                raw_artifacts.append({"type": "site_path", "path": path_str})

        # required_repo_paths → required_artifacts(repo_path) に変換
        existing_repo_paths = {
            a["path"] if isinstance(a, dict) else a.path
            for a in raw_artifacts
            if (a["type"] if isinstance(a, dict) else a.type.value) == "repo_path"
        }
        for path_str in item.get("required_repo_paths", []):
            if path_str not in existing_repo_paths:
                raw_artifacts.append({"type": "repo_path", "path": path_str})

        artifacts = []
        for a in raw_artifacts:
            if isinstance(a, dict):
                try:
                    atype = ArtifactType(a.get("type", ""))
                except ValueError:
                    atype = ArtifactType.SITE_PATH
                artifacts.append(RequiredArtifact(type=atype, path=a.get("path", "")))
            else:
                artifacts.append(a)

        # daily_post_locator
        locator_raw = item.get("daily_post_locator")
        if locator_raw and isinstance(locator_raw, dict):
            locator = DailyPostLocator(
                feed_url=locator_raw.get("feed_url"),
                sitemap_url=locator_raw.get("sitemap_url"),
                path_pattern=locator_raw.get("path_pattern"),
                index_url=locator_raw.get("index_url"),
                keyword_pattern=locator_raw.get("keyword_pattern"),
                timezone=locator_raw.get("timezone", "Asia/Tokyo"),
            )
        else:
            locator = None

        return Company(
            id=item.get("id"),
            name=item.get("name", ""),
            kind=kind,
            enabled=item.get("enabled", False),
            checks=checks,
            site=item.get("site"),
            repo=item.get("repo"),
            workflow=item.get("workflow"),
            adsense_required=item.get("adsense_required", False),
            required_keywords=list(item.get("required_keywords", [])),
            required_artifacts=artifacts,
            daily_post_strategy=list(item.get("daily_post_strategy", [])),
            daily_post_locator=locator,
            required_adsense_pages=list(item.get("required_adsense_pages", [])),
            adsense_marker_keyword=item.get("adsense_marker_keyword"),
            link_targets=list(item.get("link_targets", [])),
            self_monitor=item.get("self_monitor", False),
            portal_visible=item.get("portal_visible", True),
            notes=item.get("notes", ""),
            repo_visibility=item.get("repo_visibility", "public"),
            github_auth_required=item.get("github_auth_required", False),
        )

    def validate(self, companies: list) -> bool:
        """検証に通れば True、1件でもエラーがあれば False。"""
        return len(self.validate_with_errors(companies)) == 0

    def validate_with_errors(self, companies: list) -> list:
        """検証エラー文字列のリストを返す。空リストなら正常。"""
        errors = []
        site_required_checks = {
            "site_http",
            "top_page_keyword",
            "link_health",
            "adsense_pages",
        }
        valid_kinds = {"portal", "virtual_company", "guardian"}
        ids_seen = set()

        for c in companies:
            cid = c["id"] if isinstance(c, dict) else c.id
            ckind = c["kind"] if isinstance(c, dict) else c.kind
            cchecks = c["checks"] if isinstance(c, dict) else c.checks
            cenabled = c["enabled"] if isinstance(c, dict) else c.enabled
            csite = c["site"] if isinstance(c, dict) else c.site
            crepo = c["repo"] if isinstance(c, dict) else c.repo
            carts = c["required_artifacts"] if isinstance(c, dict) else c.required_artifacts
            cadsense_required = c["adsense_required"] if isinstance(c, dict) else c.adsense_required
            cadsense_pages = c["required_adsense_pages"] if isinstance(c, dict) else c.required_adsense_pages

            if not cid:
                errors.append("id が未設定の会社がある")
                continue  # id なしは以降のチェック不可

            if cid in ids_seen:
                errors.append(f"id 重複: {cid}")
            ids_seen.add(cid)

            kind_val = ckind.value if hasattr(ckind, "value") else str(ckind)
            if kind_val not in valid_kinds:
                errors.append(f"{cid}: kind が不正: {kind_val!r}")

            if not isinstance(cenabled, bool):
                errors.append(f"{cid}: enabled が bool でない: {cenabled!r}")

            if not cchecks:
                errors.append(f"{cid}: checks が空")

            check_strs = [str(ck) for ck in (cchecks or [])]
            if any(ck in site_required_checks for ck in check_strs) and not csite:
                errors.append(f"{cid}: site が必要な check があるが site 未設定")

            if "github_actions" in check_strs and not crepo:
                errors.append(f"{cid}: github_actions check があるが repo 未設定")

            if cadsense_required and not cadsense_pages:
                errors.append(
                    f"{cid}: adsense_required=True だが required_adsense_pages 未設定"
                )

            if self._has_site_path_artifact(carts) and not csite:
                errors.append(f"{cid}: site_path artifact があるが site 未設定")

        return errors

    def _has_site_path_artifact(self, artifacts: list) -> bool:
        for artifact in artifacts or []:
            if isinstance(artifact, dict):
                if artifact.get("type") == "site_path":
                    return True
            elif getattr(artifact, "type", None) == ArtifactType.SITE_PATH:
                return True
        return False
