from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date
from typing import Optional, List


class TriggerKind(Enum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"


class CheckStatus(Enum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ErrorCode(Enum):
    ACTION_FAILED = "ACTION_FAILED"
    GITHUB_AUTH_REQUIRED = "GITHUB_AUTH_REQUIRED"
    SITE_DOWN = "SITE_DOWN"
    SITE_DEGRADED = "SITE_DEGRADED"
    ARTIFACT_MISSING = "ARTIFACT_MISSING"
    KEYWORD_MISSING = "KEYWORD_MISSING"
    LINK_BROKEN = "LINK_BROKEN"
    PORTAL_LINK_MISMATCH = "PORTAL_LINK_MISMATCH"
    DAILY_POST_MISSING = "DAILY_POST_MISSING"
    ADSENSE_PAGE_MISSING = "ADSENSE_PAGE_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    SELF_CHECK_FAILED = "SELF_CHECK_FAILED"
    REPORT_MISSING = "REPORT_MISSING"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class CheckKind(Enum):
    SITE_HTTP = "SITE_HTTP"
    TOP_PAGE_KEYWORD = "TOP_PAGE_KEYWORD"
    LINK_HEALTH = "LINK_HEALTH"
    GITHUB_ACTIONS = "GITHUB_ACTIONS"
    ARTIFACT = "ARTIFACT"
    DAILY_POST_PREVIOUS_DAY = "DAILY_POST_PREVIOUS_DAY"
    ADSENSE_PAGES = "ADSENSE_PAGES"
    REPORT_GENERATED = "REPORT_GENERATED"
    CONFIG_VALID = "CONFIG_VALID"
    SELF_STATUS = "SELF_STATUS"
    UNKNOWN = "UNKNOWN"


class CompanyKind(Enum):
    PORTAL = "portal"
    VIRTUAL_COMPANY = "virtual_company"
    GUARDIAN = "guardian"


class ArtifactType(Enum):
    SITE_PATH = "site_path"
    REPO_PATH = "repo_path"
    WORKFLOW_ARTIFACT = "workflow_artifact"


class DailyPostStrategy(Enum):
    SITE_PATH_PATTERN = "site_path_pattern"
    FEED_XML = "feed_xml"
    SITEMAP_XML = "sitemap_xml"
    INDEX_PAGE_KEYWORD = "index_page_keyword"


class _CheckKindStr(str):
    """YAML から読んだチェック種別文字列。.value でローカーケース文字列を返す。"""
    @property
    def value(self):
        return str(self)


@dataclass
class CheckResult:
    company_id: str
    check_kind: CheckKind
    status: CheckStatus
    error_code: Optional[ErrorCode]
    detail: str
    checked_at: datetime

    @property
    def is_error(self) -> bool:
        return self.status == CheckStatus.ERROR

    @property
    def is_warning(self) -> bool:
        return self.status == CheckStatus.WARNING

    @property
    def is_ok(self) -> bool:
        return self.status == CheckStatus.OK


@dataclass
class RequiredArtifact:
    type: ArtifactType
    path: str


@dataclass
class DailyPostLocator:
    feed_url: Optional[str] = None
    sitemap_url: Optional[str] = None
    path_pattern: Optional[str] = None
    index_url: Optional[str] = None
    keyword_pattern: Optional[str] = None
    timezone: str = "Asia/Tokyo"


@dataclass
class Company:
    id: str
    name: str
    kind: CompanyKind
    enabled: bool
    checks: list
    site: Optional[str] = None
    repo: Optional[str] = None
    workflow: Optional[str] = None
    adsense_required: bool = False
    required_keywords: List[str] = field(default_factory=list)
    required_artifacts: List[RequiredArtifact] = field(default_factory=list)
    daily_post_strategy: list = field(default_factory=list)
    daily_post_locator: Optional[DailyPostLocator] = None
    required_adsense_pages: List[str] = field(default_factory=list)
    adsense_marker_keyword: Optional[str] = None
    link_targets: List[str] = field(default_factory=list)
    self_monitor: bool = False
    portal_visible: bool = True
    notes: str = ""
    repo_visibility: str = "public"
    github_auth_required: bool = False

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


@dataclass
class Incident:
    incident_date: date
    target_name: str
    error_codes: List[ErrorCode]
    phenomenon: str = ""
    impact: str = ""
    cause: str = ""
    quick_fix: str = ""
    permanent_fix_candidates: str = ""
    result: str = ""
    related_countermeasure: str = ""
    file_path: str = ""


@dataclass
class Countermeasure:
    cm_id: str
    name: str
    origin_incident: str = ""
    condition: str = ""
    steps: str = ""
    verification: str = ""
    effect: str = ""
    notes: str = ""
    file_path: str = ""


@dataclass
class DailyReport:
    executed_at: datetime
    trigger: TriggerKind
    total_count: int
    ok_count: int
    warning_count: int
    error_count: int
    action_required: List[CheckResult] = field(default_factory=list)
    applied_measures: List[str] = field(default_factory=list)
    new_countermeasures: List[str] = field(default_factory=list)
    self_monitor_result: Optional[CheckResult] = None
    adsense_anomalies: List[CheckResult] = field(default_factory=list)
    summary: str = ""
    file_path: str = ""
