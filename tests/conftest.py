"""
pytest 共通フィクスチャ
"""
import pytest
from datetime import date, datetime


# ---------------------------------------------------------------------------
# テスト用の最小 Company データ
# ---------------------------------------------------------------------------

def make_company(**kwargs):
    """Company ライクな辞書を返す簡易ファクトリ。実装時は dataclass/pydantic に合わせる。"""
    defaults = dict(
        id="test-company",
        name="Test Company",
        kind="virtual_company",
        enabled=True,
        checks=["site_http"],
        site="https://example.com",
        repo="org/test-company",
        workflow="build.yml",
        adsense_required=False,
        required_keywords=[],
        required_artifacts=[],
        daily_post_strategy=[],
        daily_post_locator=None,
        required_adsense_pages=[],
        adsense_marker_keyword=None,
        link_targets=[],
        self_monitor=False,
        portal_visible=True,
        notes="",
        repo_visibility="public",
        github_auth_required=False,
    )
    defaults.update(kwargs)
    return defaults


@pytest.fixture
def portal_company():
    return make_company(
        id="root-portal",
        name="Root Portal",
        kind="portal",
        checks=["site_http", "top_page_keyword", "link_health", "adsense_pages"],
        adsense_required=True,
        required_adsense_pages=["/privacy-policy/", "/contact/"],
        required_keywords=["ポータル", "会社一覧"],
    )


@pytest.fixture
def virtual_company():
    return make_company(
        id="auto-ai-blog",
        name="Auto AI Blog",
        kind="virtual_company",
        checks=["github_actions", "site_http", "artifact", "daily_post_previous_day", "adsense_pages"],
        adsense_required=True,
        required_artifacts=[
            {"type": "site_path", "path": "/index.html"},
            {"type": "site_path", "path": "/feed.xml"},
        ],
        daily_post_strategy=["feed_xml", "site_path_pattern"],
        daily_post_locator={
            "feed_url": "/feed.xml",
            "path_pattern": "/posts/{yyyy}/{mm}/{dd}/",
            "timezone": "Asia/Tokyo",
        },
        required_adsense_pages=["/privacy-policy/", "/contact/"],
        adsense_marker_keyword="adsbygoogle",
    )


@pytest.fixture
def guardian_company():
    return make_company(
        id="company-guardian",
        name="CompanyGuardian",
        kind="guardian",
        checks=["github_actions", "report_generated", "config_valid", "self_status"],
        adsense_required=False,
        self_monitor=True,
        site=None,
    )


@pytest.fixture
def sample_ok_result():
    from datetime import datetime
    return {
        "company_id": "test-company",
        "check_kind": "site_http",
        "status": "OK",
        "error_code": None,
        "detail": "HTTP 200",
        "checked_at": datetime(2026, 3, 10, 6, 0, 0),
    }


@pytest.fixture
def sample_error_result():
    from datetime import datetime
    return {
        "company_id": "test-company",
        "check_kind": "site_http",
        "status": "ERROR",
        "error_code": "SITE_DOWN",
        "detail": "HTTP 503",
        "checked_at": datetime(2026, 3, 10, 6, 0, 0),
    }
