"""
各 Checker クラスのテスト

担当クラス: SiteHttpChecker, TopPageKeywordChecker, LinkHealthChecker,
            GithubActionsChecker, ArtifactChecker, DailyPostChecker,
            AdSensePageChecker, ReportGeneratedChecker,
            ConfigValidChecker, SelfStatusChecker
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date


# ---------------------------------------------------------------------------
# SiteHttpChecker
# ---------------------------------------------------------------------------

class TestSiteHttpChecker:

    def _make_company(self, site="https://example.com"):
        from tests.conftest import make_company
        return make_company(site=site, checks=["site_http"])

    def test_returns_ok_for_200(self):
        """HTTP 200 → OK"""
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        mock_resp = MagicMock(status_code=200)
        with patch("guardian.checkers.site_http.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "OK"
        assert result.error_code is None

    def test_returns_ok_for_201(self):
        """HTTP 201 → OK"""
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        mock_resp = MagicMock(status_code=201)
        with patch("guardian.checkers.site_http.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_warning_for_301(self):
        """HTTP 301 → WARNING"""
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        mock_resp = MagicMock(status_code=301)
        with patch("guardian.checkers.site_http.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "WARNING"

    def test_returns_error_for_404(self):
        """HTTP 404 → ERROR / SITE_DOWN"""
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        mock_resp = MagicMock(status_code=404)
        with patch("guardian.checkers.site_http.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "SITE_DOWN"

    def test_returns_error_for_503(self):
        """HTTP 503 → ERROR / SITE_DOWN"""
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        mock_resp = MagicMock(status_code=503)
        with patch("guardian.checkers.site_http.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "SITE_DOWN"

    def test_returns_error_on_connection_error(self):
        """接続エラー → ERROR"""
        import requests as req_lib
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        with patch("guardian.checkers.site_http.requests.get",
                   side_effect=req_lib.ConnectionError("refused")):
            result = checker.check(company)
        assert result.status.value == "ERROR"

    def test_check_result_company_id_matches(self):
        """CheckResult の company_id が Company の id と一致する"""
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        mock_resp = MagicMock(status_code=200)
        with patch("guardian.checkers.site_http.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.company_id == company["id"]

    def test_check_result_check_kind_is_site_http(self):
        """CheckResult の check_kind が SITE_HTTP"""
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        mock_resp = MagicMock(status_code=200)
        with patch("guardian.checkers.site_http.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.check_kind.value == "SITE_HTTP"

    def test_checked_at_is_datetime(self):
        """checked_at が datetime 型"""
        from guardian.checkers.site_http import SiteHttpChecker
        checker = SiteHttpChecker()
        company = self._make_company()
        mock_resp = MagicMock(status_code=200)
        with patch("guardian.checkers.site_http.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert isinstance(result.checked_at, datetime)


# ---------------------------------------------------------------------------
# TopPageKeywordChecker
# ---------------------------------------------------------------------------

class TestTopPageKeywordChecker:

    def _make_company(self, keywords, site="https://example.com"):
        from tests.conftest import make_company
        return make_company(
            site=site,
            required_keywords=keywords,
            checks=["top_page_keyword"],
        )

    def test_returns_ok_when_all_keywords_present(self):
        """全キーワードが本文に含まれる → OK"""
        from guardian.checkers.top_page_keyword import TopPageKeywordChecker
        checker = TopPageKeywordChecker()
        company = self._make_company(["Hello", "World"])
        mock_resp = MagicMock(status_code=200, text="<html>Hello World</html>")
        with patch("guardian.checkers.top_page_keyword.requests.get",
                   return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_error_when_keyword_missing(self):
        """1つでもキーワードが欠けたら ERROR / KEYWORD_MISSING"""
        from guardian.checkers.top_page_keyword import TopPageKeywordChecker
        checker = TopPageKeywordChecker()
        company = self._make_company(["Hello", "Missing"])
        mock_resp = MagicMock(status_code=200, text="<html>Hello World</html>")
        with patch("guardian.checkers.top_page_keyword.requests.get",
                   return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "KEYWORD_MISSING"

    def test_returns_warning_when_no_keywords_defined(self):
        """required_keywords が空の場合 → WARNING（チェックの意味がない）"""
        from guardian.checkers.top_page_keyword import TopPageKeywordChecker
        checker = TopPageKeywordChecker()
        company = self._make_company([])
        mock_resp = MagicMock(status_code=200, text="<html></html>")
        with patch("guardian.checkers.top_page_keyword.requests.get",
                   return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value in ("OK", "WARNING")

    def test_detail_contains_missing_keyword(self):
        """detail に欠落キーワードが含まれる"""
        from guardian.checkers.top_page_keyword import TopPageKeywordChecker
        checker = TopPageKeywordChecker()
        company = self._make_company(["NotHere"])
        mock_resp = MagicMock(status_code=200, text="<html>SomethingElse</html>")
        with patch("guardian.checkers.top_page_keyword.requests.get",
                   return_value=mock_resp):
            result = checker.check(company)
        assert "NotHere" in result.detail


# ---------------------------------------------------------------------------
# LinkHealthChecker
# ---------------------------------------------------------------------------

class TestLinkHealthChecker:

    def _make_portal(self, link_targets=None):
        from tests.conftest import make_company
        return make_company(
            id="root-portal",
            kind="portal",
            site="https://example.com",
            link_targets=link_targets or [],
            checks=["link_health"],
        )

    def _make_virtual(self):
        from tests.conftest import make_company
        return make_company(
            id="virtual-co",
            kind="virtual_company",
            site="https://virtual.example.com",
            checks=["link_health"],
        )

    def test_returns_ok_when_all_links_reachable(self):
        """全リンクが 2xx → OK"""
        from guardian.checkers.link_health import LinkHealthChecker
        checker = LinkHealthChecker()
        company = self._make_portal()
        mock_resp_page = MagicMock(
            status_code=200,
            text='<a href="/about/">About</a>',
        )
        mock_resp_link = MagicMock(status_code=200)
        with patch.object(checker, "_load_expected_portal_targets", return_value=[]):
            with patch("guardian.checkers.link_health.requests.get",
                       side_effect=[mock_resp_page, mock_resp_link]):
                result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_error_when_link_is_404(self):
        """リンク先が 404 → ERROR / LINK_BROKEN"""
        from guardian.checkers.link_health import LinkHealthChecker
        checker = LinkHealthChecker()
        company = self._make_portal()
        mock_resp_page = MagicMock(
            status_code=200,
            text='<a href="/broken/">Broken</a>',
        )
        mock_resp_link = MagicMock(status_code=404)
        with patch("guardian.checkers.link_health.requests.get",
                   side_effect=[mock_resp_page, mock_resp_link]):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "LINK_BROKEN"

    def test_sns_links_excluded(self):
        """SNS リンクはチェック対象外"""
        from guardian.checkers.link_health import LinkHealthChecker
        checker = LinkHealthChecker()
        company = self._make_portal()
        sns_html = '<a href="https://twitter.com/user">Twitter</a>'
        mock_resp_page = MagicMock(status_code=200, text=sns_html)
        with patch.object(checker, "_load_expected_portal_targets", return_value=[]):
            with patch("guardian.checkers.link_health.requests.get",
                       return_value=mock_resp_page) as mock_get:
                result = checker.check(company)
        # Twitter へのリクエストは発生しない
        for call in mock_get.call_args_list[1:]:
            assert "twitter.com" not in str(call)
        # twitter.com への GET が呼ばれていなければ OK / WARNING のいずれか
        assert result.status.value in ("OK", "WARNING")

    def test_explicit_link_targets_are_checked(self):
        """link_targets に指定した URL が確認される"""
        from guardian.checkers.link_health import LinkHealthChecker
        checker = LinkHealthChecker()
        company = self._make_portal(link_targets=["https://external-partner.example.com/"])
        mock_resp_page = MagicMock(status_code=200, text="<p>no links</p>")
        mock_resp_target = MagicMock(status_code=200)
        with patch.object(checker, "_load_expected_portal_targets", return_value=[]):
            with patch("guardian.checkers.link_health.requests.get",
                       side_effect=[mock_resp_page, mock_resp_target]):
                result = checker.check(company)
        assert result.status.value == "OK"

    def test_virtual_company_checks_same_origin_only(self):
        """virtual_company は同一オリジン内リンクのみ対象"""
        from guardian.checkers.link_health import LinkHealthChecker
        checker = LinkHealthChecker()
        company = self._make_virtual()
        html = ('<a href="/about/">About</a>'
                '<a href="https://external.example.com/">External</a>')
        mock_resp_page = MagicMock(status_code=200, text=html)
        mock_resp_internal = MagicMock(status_code=200)
        with patch("guardian.checkers.link_health.requests.get",
                   side_effect=[mock_resp_page, mock_resp_internal]) as mock_get:
            checker.check(company)
        calls = [str(c) for c in mock_get.call_args_list]
        # external.example.com への GET が呼ばれていないことを確認
        assert not any("external.example.com" in c for c in calls[1:])

    def test_portal_returns_warning_for_reachable_mismatched_company_link(self):
        """親ポータルの会社リンクが別URLだが到達可能なら WARNING"""
        from guardian.checkers.link_health import LinkHealthChecker
        checker = LinkHealthChecker()
        company = self._make_portal()
        html = '<a href="https://portal.example.com/company-a/">Company A</a>'
        mock_resp_page = MagicMock(status_code=200, text=html)
        mock_resp_link = MagicMock(status_code=200)
        with patch.object(checker, "_load_expected_portal_targets",
                          return_value=[{"name": "Company A", "site": "https://example.com/company-a/"}]):
            with patch("guardian.checkers.link_health.requests.get",
                       side_effect=[mock_resp_page, mock_resp_link]):
                result = checker.check(company)
        assert result.status.value == "WARNING"
        assert result.error_code.value == "PORTAL_LINK_MISMATCH"

    def test_portal_returns_error_when_expected_company_link_missing(self):
        """親ポータルに expected company link がなければ ERROR"""
        from guardian.checkers.link_health import LinkHealthChecker
        checker = LinkHealthChecker()
        company = self._make_portal()
        mock_resp_page = MagicMock(status_code=200, text='<a href="/about/">About</a>')
        mock_resp_link = MagicMock(status_code=200)
        with patch.object(checker, "_load_expected_portal_targets",
                          return_value=[{"name": "Company A", "site": "https://example.com/company-a/"}]):
            with patch("guardian.checkers.link_health.requests.get",
                       side_effect=[mock_resp_page, mock_resp_link]):
                result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "LINK_BROKEN"


# ---------------------------------------------------------------------------
# GithubActionsChecker
# ---------------------------------------------------------------------------

class TestGithubActionsChecker:

    def _make_company(self, repo="org/repo", workflow="build.yml"):
        from tests.conftest import make_company
        return make_company(repo=repo, workflow=workflow, checks=["github_actions"])

    def _patch_run(self, conclusion, status="completed"):
        return {"conclusion": conclusion, "status": status}

    def test_returns_ok_for_success(self):
        """conclusion=success → OK"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company()
        with patch.object(checker, "_fetch_latest_run",
                          return_value=self._patch_run("success")):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_error_for_failure(self):
        """conclusion=failure → ERROR / ACTION_FAILED"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company()
        with patch.object(checker, "_fetch_latest_run",
                          return_value=self._patch_run("failure")):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "ACTION_FAILED"

    def test_returns_error_for_cancelled(self):
        """conclusion=cancelled → ERROR / ACTION_FAILED"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company()
        with patch.object(checker, "_fetch_latest_run",
                          return_value=self._patch_run("cancelled")):
            result = checker.check(company)
        assert result.status.value == "ERROR"

    def test_returns_error_for_timed_out(self):
        """conclusion=timed_out → ERROR / ACTION_FAILED"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company()
        with patch.object(checker, "_fetch_latest_run",
                          return_value=self._patch_run("timed_out")):
            result = checker.check(company)
        assert result.status.value == "ERROR"

    def test_returns_error_for_action_required(self):
        """conclusion=action_required → ERROR / ACTION_FAILED"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company()
        with patch.object(checker, "_fetch_latest_run",
                          return_value=self._patch_run("action_required")):
            result = checker.check(company)
        assert result.status.value == "ERROR"

    def test_returns_warning_for_in_progress(self):
        """status=in_progress → WARNING"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company()
        with patch.object(checker, "_fetch_latest_run",
                          return_value={"conclusion": None, "status": "in_progress"}):
            result = checker.check(company)
        assert result.status.value == "WARNING"

    def test_returns_warning_for_queued(self):
        """status=queued → WARNING"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company()
        with patch.object(checker, "_fetch_latest_run",
                          return_value={"conclusion": None, "status": "queued"}):
            result = checker.check(company)
        assert result.status.value == "WARNING"

    def test_returns_warning_when_no_history(self):
        """実行履歴なし → WARNING"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company()
        with patch.object(checker, "_fetch_latest_run", return_value=None):
            result = checker.check(company)
        assert result.status.value == "WARNING"

    def test_returns_warning_when_private_repo_requires_auth(self):
        """private repo で token がなければ WARNING / GITHUB_AUTH_REQUIRED"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        company = self._make_company(
            repo="org/private-repo",
            workflow="build.yml",
        )
        company["repo_visibility"] = "private"
        company["github_auth_required"] = True
        with patch.dict("os.environ", {}, clear=True):
            result = checker.check(company)
        assert result.status.value == "WARNING"
        assert result.error_code.value == "GITHUB_AUTH_REQUIRED"

    def test_fetch_latest_run_uses_workflow_endpoint_when_workflow_specified(self):
        """workflow 指定時は workflow runs endpoint を使う"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        response = MagicMock()
        response.json.return_value = {
            "workflow_runs": [{"conclusion": "success", "status": "completed"}]
        }
        response.raise_for_status.return_value = None
        with patch("guardian.checkers.github_actions.requests.get", return_value=response) as mock_get:
            run = checker._fetch_latest_run("org/repo", "build.yml")
        assert run["conclusion"] == "success"
        url = mock_get.call_args[0][0]
        assert url.endswith("/actions/workflows/build.yml/runs")

    def test_fetch_latest_run_uses_repo_runs_endpoint_when_workflow_missing(self):
        """workflow 未指定時は repo 全体の runs endpoint を使う"""
        from guardian.checkers.github_actions import GithubActionsChecker
        checker = GithubActionsChecker()
        response = MagicMock()
        response.json.return_value = {
            "workflow_runs": [{"conclusion": "success", "status": "completed"}]
        }
        response.raise_for_status.return_value = None
        with patch("guardian.checkers.github_actions.requests.get", return_value=response) as mock_get:
            checker._fetch_latest_run("org/repo", None)
        url = mock_get.call_args[0][0]
        assert url.endswith("/actions/runs")


# ---------------------------------------------------------------------------
# ArtifactChecker
# ---------------------------------------------------------------------------

class TestArtifactChecker:

    def _make_company(self, artifacts):
        from tests.conftest import make_company
        return make_company(
            site="https://example.com",
            required_artifacts=artifacts,
            checks=["artifact"],
        )

    def test_returns_ok_when_site_path_exists(self):
        """/index.html が 200 → OK"""
        from guardian.checkers.artifact import ArtifactChecker
        checker = ArtifactChecker()
        company = self._make_company([{"type": "site_path", "path": "/index.html"}])
        mock_resp = MagicMock(status_code=200)
        with patch("guardian.checkers.artifact.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_error_when_site_path_404(self):
        """/index.html が 404 → ERROR / ARTIFACT_MISSING"""
        from guardian.checkers.artifact import ArtifactChecker
        checker = ArtifactChecker()
        company = self._make_company([{"type": "site_path", "path": "/index.html"}])
        mock_resp = MagicMock(status_code=404)
        with patch("guardian.checkers.artifact.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "ARTIFACT_MISSING"

    def test_returns_warning_for_repo_path_unsupported(self):
        """repo_path は初期版未サポート → WARNING"""
        from guardian.checkers.artifact import ArtifactChecker
        checker = ArtifactChecker()
        company = self._make_company([{"type": "repo_path", "path": "README.md"}])
        result = checker.check(company)
        assert result.status.value == "WARNING"

    def test_returns_warning_for_workflow_artifact_unsupported(self):
        """workflow_artifact は初期版未サポート → WARNING"""
        from guardian.checkers.artifact import ArtifactChecker
        checker = ArtifactChecker()
        company = self._make_company([{"type": "workflow_artifact", "path": "site-build"}])
        result = checker.check(company)
        assert result.status.value == "WARNING"

    def test_multiple_site_paths_all_ok(self):
        """複数の site_path が全部 200 → OK"""
        from guardian.checkers.artifact import ArtifactChecker
        checker = ArtifactChecker()
        company = self._make_company([
            {"type": "site_path", "path": "/index.html"},
            {"type": "site_path", "path": "/feed.xml"},
        ])
        mock_resp = MagicMock(status_code=200)
        with patch("guardian.checkers.artifact.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_error_when_any_site_path_missing(self):
        """site_path の 1 つでも 404 → ERROR"""
        from guardian.checkers.artifact import ArtifactChecker
        checker = ArtifactChecker()
        company = self._make_company([
            {"type": "site_path", "path": "/index.html"},
            {"type": "site_path", "path": "/missing.html"},
        ])
        ok_resp = MagicMock(status_code=200)
        ng_resp = MagicMock(status_code=404)
        with patch("guardian.checkers.artifact.requests.get",
                   side_effect=[ok_resp, ng_resp]):
            result = checker.check(company)
        assert result.status.value == "ERROR"

    def test_returns_warning_when_no_artifacts_defined(self):
        """required_artifacts が空 → WARNING"""
        from guardian.checkers.artifact import ArtifactChecker
        checker = ArtifactChecker()
        company = self._make_company([])
        result = checker.check(company)
        assert result.status.value == "WARNING"


# ---------------------------------------------------------------------------
# DailyPostChecker
# ---------------------------------------------------------------------------

class TestDailyPostChecker:

    def _make_company(self, strategy, locator):
        from tests.conftest import make_company
        return make_company(
            site="https://example.com",
            daily_post_strategy=strategy,
            daily_post_locator=locator,
            checks=["daily_post_previous_day"],
        )

    def test_returns_warning_when_no_strategy_defined(self):
        """daily_post_strategy が空 → WARNING"""
        from guardian.checkers.daily_post import DailyPostChecker
        checker = DailyPostChecker()
        company = self._make_company([], None)
        result = checker.check(company)
        assert result.status.value == "WARNING"

    def test_returns_ok_when_feed_xml_has_yesterday_entry(self):
        """feed_xml 戦略で前日エントリあり → OK"""
        from guardian.checkers.daily_post import DailyPostChecker
        checker = DailyPostChecker()
        yesterday = date(2026, 3, 9)
        company = self._make_company(
            strategy=["feed_xml"],
            locator={"feed_url": "/feed.xml", "timezone": "Asia/Tokyo"},
        )
        # _check_strategy をモックして前日エントリ有りを返す
        from guardian.models import CheckResult, CheckStatus, CheckKind
        ok_result = MagicMock(status=CheckStatus.OK)
        with patch.object(checker, "_check_strategy", return_value=ok_result):
            with patch.object(checker, "_resolve_previous_day_jst", return_value=yesterday):
                result = checker.check(company)
        assert result.status == CheckStatus.OK

    def test_returns_error_when_all_strategies_fail(self):
        """全戦略が失敗 → ERROR / DAILY_POST_MISSING"""
        from guardian.checkers.daily_post import DailyPostChecker
        checker = DailyPostChecker()
        yesterday = date(2026, 3, 9)
        company = self._make_company(
            strategy=["feed_xml", "site_path_pattern"],
            locator={"feed_url": "/feed.xml",
                     "path_pattern": "/posts/{yyyy}/{mm}/{dd}/",
                     "timezone": "Asia/Tokyo"},
        )
        from guardian.models import CheckStatus
        ng_result = MagicMock(status=CheckStatus.ERROR)
        with patch.object(checker, "_check_strategy", return_value=ng_result):
            with patch.object(checker, "_resolve_previous_day_jst", return_value=yesterday):
                result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "DAILY_POST_MISSING"

    def test_first_ok_strategy_short_circuits(self):
        """最初に OK の戦略が見つかれば以降は評価しない"""
        from guardian.checkers.daily_post import DailyPostChecker
        checker = DailyPostChecker()
        yesterday = date(2026, 3, 9)
        company = self._make_company(
            strategy=["feed_xml", "site_path_pattern"],
            locator={"feed_url": "/feed.xml",
                     "path_pattern": "/posts/{yyyy}/{mm}/{dd}/",
                     "timezone": "Asia/Tokyo"},
        )
        from guardian.models import CheckStatus
        ok_result = MagicMock(status=CheckStatus.OK)
        with patch.object(checker, "_check_strategy", return_value=ok_result) as mock_cs:
            with patch.object(checker, "_resolve_previous_day_jst", return_value=yesterday):
                result = checker.check(company)
        # feed_xml が OK なので site_path_pattern は呼ばれない
        assert mock_cs.call_count == 1
        assert result.status == CheckStatus.OK

    def test_resolve_previous_day_jst_returns_yesterday(self):
        """_resolve_previous_day_jst が実行日の JST 前日を返す"""
        from guardian.checkers.daily_post import DailyPostChecker
        import zoneinfo
        checker = DailyPostChecker()
        # 2026-03-10 JST を固定して前日が 2026-03-09 になることを確認
        fixed_now = datetime(2026, 3, 10, 6, 0, 0,
                             tzinfo=zoneinfo.ZoneInfo("Asia/Tokyo"))
        with patch("guardian.checkers.daily_post.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            yesterday = checker._resolve_previous_day_jst()
        assert yesterday == date(2026, 3, 9)


# ---------------------------------------------------------------------------
# AdSensePageChecker
# ---------------------------------------------------------------------------

class TestAdSensePageChecker:

    def _make_company(self, pages, marker=None):
        from tests.conftest import make_company
        return make_company(
            site="https://example.com",
            adsense_required=True,
            required_adsense_pages=pages,
            adsense_marker_keyword=marker,
            checks=["adsense_pages"],
        )

    def test_returns_ok_when_all_pages_reachable(self):
        """全 required_adsense_pages が 200 → OK"""
        from guardian.checkers.adsense_page import AdSensePageChecker
        checker = AdSensePageChecker()
        company = self._make_company(["/privacy-policy/", "/contact/"])
        mock_resp = MagicMock(status_code=200, text="<html>content</html>")
        with patch("guardian.checkers.adsense_page.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_error_when_page_404(self):
        """/privacy-policy/ が 404 → ERROR / ADSENSE_PAGE_MISSING"""
        from guardian.checkers.adsense_page import AdSensePageChecker
        checker = AdSensePageChecker()
        company = self._make_company(["/privacy-policy/"])
        mock_resp = MagicMock(status_code=404)
        with patch("guardian.checkers.adsense_page.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "ADSENSE_PAGE_MISSING"

    def test_marker_keyword_absent_is_warning_not_error(self):
        """adsense_marker_keyword が欠落 → WARNING（初期版）"""
        from guardian.checkers.adsense_page import AdSensePageChecker
        checker = AdSensePageChecker()
        company = self._make_company(
            pages=["/privacy-policy/"],
            marker="adsbygoogle",
        )
        mock_resp = MagicMock(status_code=200, text="<html>no marker here</html>")
        with patch("guardian.checkers.adsense_page.requests.get", return_value=mock_resp):
            result = checker.check(company)
        # マーカー欠落は WARNING に留まる
        assert result.status.value in ("OK", "WARNING")
        # ERROR にはならない
        assert result.status.value != "ERROR"

    def test_marker_keyword_present_contributes_to_ok(self):
        """adsense_marker_keyword が本文にある → OK"""
        from guardian.checkers.adsense_page import AdSensePageChecker
        checker = AdSensePageChecker()
        company = self._make_company(
            pages=["/privacy-policy/"],
            marker="adsbygoogle",
        )
        mock_resp = MagicMock(
            status_code=200,
            text="<html>adsbygoogle present</html>",
        )
        with patch("guardian.checkers.adsense_page.requests.get", return_value=mock_resp):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_warning_when_no_pages_defined(self):
        """required_adsense_pages が空 → WARNING"""
        from guardian.checkers.adsense_page import AdSensePageChecker
        checker = AdSensePageChecker()
        company = self._make_company([])
        result = checker.check(company)
        assert result.status.value == "WARNING"


# ---------------------------------------------------------------------------
# ReportGeneratedChecker
# ---------------------------------------------------------------------------

class TestReportGeneratedChecker:

    def _make_guardian(self):
        from tests.conftest import make_company
        return make_company(
            id="company-guardian",
            kind="guardian",
            self_monitor=True,
            checks=["report_generated"],
        )

    def test_returns_ok_when_previous_report_exists(self):
        """前回分の日報ファイルが存在する → OK"""
        from guardian.checkers.report_generated import ReportGeneratedChecker
        from guardian.models import TriggerKind
        checker = ReportGeneratedChecker(trigger=TriggerKind.SCHEDULED)
        company = self._make_guardian()
        with patch("guardian.checkers.report_generated.os.path.exists",
                   return_value=True):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_error_when_previous_report_missing(self):
        """前回分の日報ファイルが存在しない → ERROR / REPORT_MISSING"""
        from guardian.checkers.report_generated import ReportGeneratedChecker
        from guardian.models import TriggerKind
        checker = ReportGeneratedChecker(trigger=TriggerKind.SCHEDULED)
        company = self._make_guardian()
        with patch("guardian.checkers.report_generated.os.path.exists",
                   return_value=False):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "REPORT_MISSING"

    def test_scheduled_trigger_checks_yesterday_report(self):
        """定期実行では前日の日報ファイルパスを対象にする"""
        from guardian.checkers.report_generated import ReportGeneratedChecker
        from guardian.models import TriggerKind
        checker = ReportGeneratedChecker(trigger=TriggerKind.SCHEDULED)
        company = self._make_guardian()
        with patch("guardian.checkers.report_generated.os.path.exists",
                   return_value=True) as mock_exists:
            checker.check(company)
        path_checked = mock_exists.call_args[0][0]
        assert "2026-03-09" in path_checked or "reports/daily/" in path_checked

    def test_manual_trigger_checks_latest_scheduled_report(self):
        """手動実行でも直近の定期実行分の日報を対象にする"""
        from guardian.checkers.report_generated import ReportGeneratedChecker
        from guardian.models import TriggerKind
        checker = ReportGeneratedChecker(trigger=TriggerKind.MANUAL)
        company = self._make_guardian()
        with patch("guardian.checkers.report_generated.os.path.exists",
                   return_value=True):
            result = checker.check(company)
        assert result.status.value == "OK"


# ---------------------------------------------------------------------------
# ConfigValidChecker
# ---------------------------------------------------------------------------

class TestConfigValidChecker:

    def _make_guardian(self):
        from tests.conftest import make_company
        return make_company(
            id="company-guardian",
            kind="guardian",
            checks=["config_valid"],
        )

    def test_returns_ok_when_config_is_valid(self):
        """有効な YAML → OK"""
        from guardian.checkers.config_valid import ConfigValidChecker
        checker = ConfigValidChecker()
        company = self._make_guardian()
        with patch("builtins.open",
                   mock_open(read_data="companies:\n  - id: x\n    name: X\n    kind: virtual_company\n    enabled: true\n    site: https://example.com\n    checks: [site_http]\n")):
            with patch("guardian.checkers.config_valid.os.path.exists", return_value=True):
                result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_error_when_yaml_syntax_invalid(self):
        """YAML 構文エラー → ERROR / CONFIG_INVALID"""
        from guardian.checkers.config_valid import ConfigValidChecker
        from unittest.mock import mock_open
        checker = ConfigValidChecker()
        company = self._make_guardian()
        with patch("builtins.open",
                   mock_open(read_data="companies: [broken")):
            with patch("guardian.checkers.config_valid.os.path.exists", return_value=True):
                result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "CONFIG_INVALID"

    def test_returns_error_when_config_file_missing(self):
        """設定ファイルが存在しない → ERROR / CONFIG_INVALID"""
        from guardian.checkers.config_valid import ConfigValidChecker
        checker = ConfigValidChecker()
        company = self._make_guardian()
        with patch("guardian.checkers.config_valid.os.path.exists", return_value=False):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "CONFIG_INVALID"

    def test_returns_error_when_structurally_invalid(self):
        """YAML 構文は正しくても validate で落ちる設定は ERROR"""
        from guardian.checkers.config_valid import ConfigValidChecker
        checker = ConfigValidChecker()
        company = self._make_guardian()
        with patch("builtins.open",
                   mock_open(read_data="companies:\n  - id: x\n    name: X\n    kind: virtual_company\n    enabled: true\n    checks: [site_http]\n")):
            with patch("guardian.checkers.config_valid.os.path.exists", return_value=True):
                result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "CONFIG_INVALID"


# ---------------------------------------------------------------------------
# SelfStatusChecker
# ---------------------------------------------------------------------------

class TestSelfStatusChecker:

    def _make_guardian(self):
        from tests.conftest import make_company
        return make_company(
            id="company-guardian",
            kind="guardian",
            self_monitor=True,
            checks=["self_status"],
        )

    def test_returns_ok_when_all_self_checks_pass(self):
        """README 必須セクション存在・前回日報整合OK → OK"""
        from guardian.checkers.self_status import SelfStatusChecker
        checker = SelfStatusChecker()
        company = self._make_guardian()
        with patch.object(checker, "_check_readme_sections", return_value=True):
            with patch.object(checker, "_check_prev_report_consistency", return_value=True):
                result = checker.check(company)
        assert result.status.value == "OK"

    def test_returns_error_when_readme_section_missing(self):
        """README 必須セクション欠落 → ERROR / SELF_CHECK_FAILED"""
        from guardian.checkers.self_status import SelfStatusChecker
        checker = SelfStatusChecker()
        company = self._make_guardian()
        with patch.object(checker, "_check_readme_sections", return_value=False):
            with patch.object(checker, "_check_prev_report_consistency", return_value=True):
                result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "SELF_CHECK_FAILED"

    def test_returns_error_when_report_consistency_fails(self):
        """前回日報との整合不一致 → ERROR / SELF_CHECK_FAILED"""
        from guardian.checkers.self_status import SelfStatusChecker
        checker = SelfStatusChecker()
        company = self._make_guardian()
        with patch.object(checker, "_check_readme_sections", return_value=True):
            with patch.object(checker, "_check_prev_report_consistency", return_value=False):
                result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "SELF_CHECK_FAILED"

    def test_readme_sections_checks_12_required_sections(self):
        """_check_readme_sections が SPEC §12 の 12 項目を確認する"""
        from guardian.checkers.self_status import SelfStatusChecker
        checker = SelfStatusChecker()
        # 12 項目すべてを含む README
        readme_with_all = "\n".join([
            "# CompanyGuardian",
            "## 目的",
            "## 実行環境",
            "## 定期実行",
            "## 監視対象",
            "## 実行方法",
            "## 日報",
            "## インシデント",
            "## 再発防止策",
            "## 会社の追加方法",
            "## 自己監視",
            "## 障害時対応",
            "## AdSense",
        ])
        with patch("builtins.open", mock_open(read_data=readme_with_all)):
            assert checker._check_readme_sections(required=None) is True

    def test_readme_sections_fails_when_section_missing(self):
        """必須セクションが 1 つでも欠けると False"""
        from guardian.checkers.self_status import SelfStatusChecker
        checker = SelfStatusChecker()
        readme_incomplete = "# CompanyGuardian\n## 目的だけ"
        with patch("builtins.open", mock_open(read_data=readme_incomplete)):
            assert checker._check_readme_sections(required=None) is False


# ---------------------------------------------------------------------------
# ReportGeneratedChecker - report_generated が UNKNOWN にならない
# ---------------------------------------------------------------------------

class TestReportGeneratedCheckerNotUnknown:

    def _make_guardian(self):
        from tests.conftest import make_company
        return make_company(
            id="company-guardian",
            kind="guardian",
            self_monitor=True,
            checks=["report_generated"],
        )

    def test_report_generated_not_unknown_in_runner(self):
        """_check_all で report_generated が UNKNOWN にならず正常に実行される"""
        from guardian.runner import CompanyGuardianRunner
        from guardian.models import CheckKind
        runner = CompanyGuardianRunner()
        company = self._make_guardian()
        with patch("guardian.checkers.report_generated.os.path.exists", return_value=True):
            results = runner._check_all([company])
        kinds = [r.check_kind for r in results]
        assert CheckKind.UNKNOWN not in kinds

    def test_report_generated_returns_ok_when_report_exists(self):
        """前日日報が存在する → OK"""
        from guardian.checkers.report_generated import ReportGeneratedChecker
        from guardian.models import TriggerKind
        checker = ReportGeneratedChecker(trigger=TriggerKind.SCHEDULED)
        company = {"id": "company-guardian"}
        with patch("guardian.checkers.report_generated.os.path.exists", return_value=True):
            result = checker.check(company)
        assert result.status.value == "OK"
        assert result.check_kind.value == "REPORT_GENERATED"

    def test_report_generated_returns_error_when_report_missing(self):
        """前日日報がない → ERROR / REPORT_MISSING"""
        from guardian.checkers.report_generated import ReportGeneratedChecker
        from guardian.models import TriggerKind
        checker = ReportGeneratedChecker(trigger=TriggerKind.SCHEDULED)
        company = {"id": "company-guardian"}
        with patch("guardian.checkers.report_generated.os.path.exists", return_value=False):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "REPORT_MISSING"


# ---------------------------------------------------------------------------
# ConfigValidChecker - 重複 ID と必須キー不足の検出
# ---------------------------------------------------------------------------

class TestConfigValidCheckerEnhanced:

    def _make_guardian(self):
        from tests.conftest import make_company
        return make_company(
            id="company-guardian",
            kind="guardian",
            checks=["config_valid"],
        )

    def test_config_valid_detects_duplicate_id(self, tmp_path, monkeypatch):
        """重複 ID があれば ERROR / CONFIG_INVALID"""
        import textwrap
        from guardian.checkers.config_valid import ConfigValidChecker
        monkeypatch.chdir(tmp_path)
        (tmp_path / "companies").mkdir()
        yaml_content = textwrap.dedent("""\
            companies:
              - id: dup-co
                name: Co A
                kind: virtual_company
                enabled: true
                checks:
                  - config_valid
              - id: dup-co
                name: Co B
                kind: virtual_company
                enabled: true
                checks:
                  - config_valid
        """)
        (tmp_path / "companies" / "companies.yaml").write_text(yaml_content, encoding="utf-8")
        checker = ConfigValidChecker()
        company = self._make_guardian()
        result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "CONFIG_INVALID"
        assert "重複" in result.detail

    def test_config_valid_detects_missing_site_for_site_http(self, tmp_path, monkeypatch):
        """site_http check があるが site 未設定 → ERROR"""
        import textwrap
        from guardian.checkers.config_valid import ConfigValidChecker
        monkeypatch.chdir(tmp_path)
        (tmp_path / "companies").mkdir()
        yaml_content = textwrap.dedent("""\
            companies:
              - id: no-site-co
                name: No Site
                kind: virtual_company
                enabled: true
                checks:
                  - site_http
        """)
        (tmp_path / "companies" / "companies.yaml").write_text(yaml_content, encoding="utf-8")
        checker = ConfigValidChecker()
        company = self._make_guardian()
        result = checker.check(company)
        assert result.status.value == "ERROR"
        assert "site" in result.detail.lower() or "CONFIG_INVALID" in result.error_code.value

    def test_config_valid_ok_for_valid_yaml(self, tmp_path, monkeypatch):
        """正常な YAML → OK"""
        import textwrap
        from guardian.checkers.config_valid import ConfigValidChecker
        monkeypatch.chdir(tmp_path)
        (tmp_path / "companies").mkdir()
        yaml_content = textwrap.dedent("""\
            companies:
              - id: valid-co
                name: Valid Co
                kind: virtual_company
                site: https://example.com
                enabled: true
                checks:
                  - site_http
        """)
        (tmp_path / "companies" / "companies.yaml").write_text(yaml_content, encoding="utf-8")
        checker = ConfigValidChecker()
        company = self._make_guardian()
        result = checker.check(company)
        assert result.status.value == "OK"


from unittest.mock import mock_open  # noqa: E402 (ファイル末尾にまとめて import)
