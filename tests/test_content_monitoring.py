from datetime import date, datetime
from unittest.mock import MagicMock, patch


def _make_content_entry(**kwargs):
    from guardian.models import ContentEntry

    defaults = dict(
        url="https://example.com/post",
        title="Sample",
        published_on=date(2026, 3, 9),
        excerpt="excerpt",
        slug="sample",
        content_hash="hash-1",
        progress_value=None,
    )
    defaults.update(kwargs)
    return ContentEntry(**defaults)


def _make_result(error_code="STALE_CONTENT", check_kind="LATEST_POST_FRESHNESS", detail="detail", context=None):
    from guardian.models import CheckResult, CheckKind, CheckStatus, ErrorCode

    return CheckResult(
        company_id="test-company",
        check_kind=CheckKind[check_kind],
        status=CheckStatus.ERROR,
        error_code=ErrorCode[error_code],
        detail=detail,
        checked_at=datetime(2026, 3, 10, 10, 0, 0),
        context=context or {},
    )


class TestLatestPostFreshnessChecker:
    def test_old_latest_date_is_stale_content(self):
        from guardian.checkers.latest_post_freshness import LatestPostFreshnessChecker
        from guardian.models import CheckStatus, ErrorCode
        from tests.conftest import make_company

        checker = LatestPostFreshnessChecker()
        checker._state_store = MagicMock()
        company = make_company(
            checks=["latest_post_freshness"],
            freshness_rule={
                "max_age_days": 1,
                "label": "最新記事",
                "stale_message_template": "{label}が {latest_date} で停止",
            },
        )
        with patch.object(checker, "_now", return_value=datetime(2026, 3, 10, 10, 0, 0)):
            with patch.object(
                checker._inspector,
                "fetch_entries",
                return_value=[_make_content_entry(published_on=date(2026, 3, 6))],
            ):
                result = checker.check(company)

        assert result.status == CheckStatus.ERROR
        assert result.error_code == ErrorCode.STALE_CONTENT
        assert "2026-03-06" in result.detail


class TestLatestPostUniquenessChecker:
    def test_same_content_hash_is_duplicate_content(self):
        from guardian.checkers.latest_post_uniqueness import LatestPostUniquenessChecker
        from guardian.models import CheckStatus, ErrorCode
        from tests.conftest import make_company

        checker = LatestPostUniquenessChecker()
        checker._state_store = MagicMock()
        company = make_company(
            checks=["latest_post_uniqueness"],
            uniqueness_rule={
                "compare_fields": ["title", "content_hash"],
            },
        )
        entries = [
            _make_content_entry(
                title="The God Agni",
                published_on=date(2026, 3, 9),
                content_hash="same-hash",
            ),
            _make_content_entry(
                url="https://example.com/post-2",
                title="The God Agni",
                published_on=date(2026, 3, 8),
                content_hash="same-hash",
            ),
        ]
        with patch.object(checker._inspector, "fetch_entries", return_value=entries):
            result = checker.check(company)

        assert result.status == CheckStatus.ERROR
        assert result.error_code == ErrorCode.DUPLICATE_CONTENT
        assert "2026-03-08" in result.detail
        assert "2026-03-09" in result.detail


class TestSerialProgressChecker:
    def test_unchanged_progress_for_days_is_serial_stalled(self):
        from guardian.checkers.serial_progress import SerialProgressChecker
        from guardian.models import CheckStatus, ErrorCode
        from tests.conftest import make_company

        checker = SerialProgressChecker()
        checker._state_store = MagicMock()
        checker._state_store.get_target_state.return_value = {
            "last_seen_progress_value": 1,
            "last_progress_changed_at": "2026-03-08T00:00:00",
        }
        company = make_company(
            checks=["serial_progress"],
            serial_rule={
                "label": "フランケンシュタイン",
                "stagnant_days": 1,
                "progress_display_offset": 1,
                "stalled_message_template": "{label}第{display_progress_value}章から進行停止",
            },
        )
        with patch.object(checker, "_now", return_value=datetime(2026, 3, 10, 10, 0, 0)):
            with patch.object(
                checker._inspector,
                "fetch_serial_entry",
                return_value=_make_content_entry(
                    progress_value=1,
                    published_on=date(2026, 3, 9),
                    title="フランケンシュタイン",
                ),
            ):
                result = checker.check(company)

        assert result.status == CheckStatus.ERROR
        assert result.error_code == ErrorCode.SERIAL_STALLED
        assert "第2章" in result.detail


class TestContentIncidentAnalyzer:
    def test_stale_content_can_be_classified_as_workflow_failed(self):
        from guardian.content_incident_analyzer import ContentIncidentAnalyzer
        from tests.conftest import make_company

        analyzer = ContentIncidentAnalyzer()
        company = make_company(
            repo="org/repo",
            workflow="daily.yml",
            freshness_rule={
                "workflow": "daily.yml",
                "repo_path_pattern": "docs/posts/daily/{date}.html",
            },
        )
        result = _make_result(
            error_code="STALE_CONTENT",
            check_kind="LATEST_POST_FRESHNESS",
            detail="最新日次レポートが 2026-03-06 で停止",
            context={"latest_date": "2026-03-06"},
        )
        failure_run = {"id": 123, "status": "completed", "conclusion": "failure", "updated_at": "2026-03-09T08:13:31Z"}
        with patch.object(analyzer._github, "get_latest_workflow_run", return_value=failure_run):
            with patch.object(analyzer._github, "list_workflow_runs", return_value=[failure_run]):
                with patch.object(analyzer._github, "get_latest_commit", return_value={"commit": {"author": {"date": "2026-03-09T08:12:00Z"}}}):
                    with patch.object(analyzer._github, "path_exists", return_value=False):
                        with patch.object(analyzer._github, "get_run_jobs", return_value=[{"name": "daily", "steps": [{"name": "Run daily job", "conclusion": "failure"}]}]):
                            analysis = analyzer.analyze(company, result)

        assert analysis.cause_code == "WORKFLOW_FAILED"
        assert analysis.diagnostics["suggested_action"] == "rerun_failed_jobs"


class TestContentAutoFixer:
    def test_allowed_fix_executes_rerun(self):
        from guardian.content_autofix import ContentAutoFixer, _attempted_actions
        from guardian.github_auth import GitHubAuthStatus
        from guardian.models import ContentIncidentAnalysis
        from tests.conftest import make_company

        _attempted_actions.clear()
        fixer = ContentAutoFixer()
        company = make_company(repo="org/repo", workflow="daily.yml")
        result = _make_result(error_code="STALE_CONTENT")
        analysis = ContentIncidentAnalysis(
            company_id="test-company",
            error_code=result.error_code,
            cause_code="WORKFLOW_FAILED",
            cause_summary="failure",
            recommended_fix="workflow rerun",
            diagnostics={
                "repo": "org/repo",
                "workflow": "daily.yml",
                "latest_run": {"id": 456},
                "suggested_action": "rerun_failed_jobs",
            },
        )
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="env_token")):
            with patch.object(fixer._github, "rerun_failed_jobs", return_value=(True, 201)):
                fix = fixer.apply(company, result, analysis)

        assert fix.status == "OK"
        assert "再実行" in fix.message

    def test_gh_cli_auth_does_not_skip_allowed_fix(self):
        from guardian.content_autofix import ContentAutoFixer, _attempted_actions
        from guardian.github_auth import GitHubAuthStatus
        from guardian.models import ContentIncidentAnalysis
        from tests.conftest import make_company

        _attempted_actions.clear()
        fixer = ContentAutoFixer()
        company = make_company(repo="org/repo", workflow="daily.yml")
        result = _make_result(error_code="STALE_CONTENT")
        analysis = ContentIncidentAnalysis(
            company_id="test-company",
            error_code=result.error_code,
            cause_code="WORKFLOW_FAILED",
            cause_summary="failure",
            recommended_fix="workflow rerun",
            diagnostics={
                "repo": "org/repo",
                "workflow": "daily.yml",
                "latest_run": {"id": 456},
                "suggested_action": "rerun_failed_jobs",
            },
        )

        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="gh_cli")):
            with patch.object(fixer._github, "rerun_failed_jobs", return_value=(True, 201)):
                fix = fixer.apply(company, result, analysis)

        assert fix.status == "OK"
        assert "auth=gh_cli" in fix.message

    def test_none_auth_skips_allowed_fix(self):
        from guardian.content_autofix import ContentAutoFixer
        from guardian.github_auth import GitHubAuthStatus
        from guardian.models import ContentIncidentAnalysis
        from tests.conftest import make_company

        fixer = ContentAutoFixer()
        company = make_company(repo="org/repo", workflow="daily.yml")
        result = _make_result(error_code="STALE_CONTENT")
        analysis = ContentIncidentAnalysis(
            company_id="test-company",
            error_code=result.error_code,
            cause_code="WORKFLOW_FAILED",
            cause_summary="failure",
            recommended_fix="workflow rerun",
            diagnostics={
                "repo": "org/repo",
                "workflow": "daily.yml",
                "latest_run": {"id": 456},
                "suggested_action": "rerun_failed_jobs",
            },
        )

        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="none")):
            fix = fixer.apply(company, result, analysis)

        assert fix.status == "SKIP"
        assert "GitHub 認証手段なし" in fix.message

    def test_high_risk_fix_is_skipped(self):
        from guardian.content_autofix import ContentAutoFixer
        from guardian.models import ContentIncidentAnalysis
        from tests.conftest import make_company

        fixer = ContentAutoFixer()
        company = make_company(repo="org/repo")
        result = _make_result(error_code="DUPLICATE_CONTENT", check_kind="LATEST_POST_UNIQUENESS")
        analysis = ContentIncidentAnalysis(
            company_id="test-company",
            error_code=result.error_code,
            cause_code="SELECTION_LOGIC_BROKEN",
            cause_summary="selection logic issue",
            recommended_fix="manual investigation",
            diagnostics={"repo": "org/repo"},
        )
        fix = fixer.apply(company, result, analysis)

        assert fix.status == "SKIP"


class TestContentStateStore:
    def test_state_file_keeps_required_fields(self, tmp_path, monkeypatch):
        from guardian.content_state import ContentStateStore

        monkeypatch.chdir(tmp_path)
        store = ContentStateStore("state/content_monitoring_state.json")
        path = store.update_target(
            "aozora-daily-translations",
            _make_content_entry(
                url="https://example.com/work/2026-03-09",
                title="The God Agni",
                published_on=date(2026, 3, 9),
                content_hash="hash-123",
                progress_value=2,
            ),
            datetime(2026, 3, 10, 10, 0, 0),
        )
        state = store.load()["aozora-daily-translations"]

        assert path == "state/content_monitoring_state.json"
        assert state["target_id"] == "aozora-daily-translations"
        assert state["last_seen_latest_date"] == "2026-03-09"
        assert state["last_seen_latest_url"] == "https://example.com/work/2026-03-09"
        assert state["last_seen_title"] == "The God Agni"
        assert state["last_seen_content_hash"] == "hash-123"
        assert state["last_seen_progress_value"] == 2
        assert state["last_checked_at"] == "2026-03-10T10:00:00"
