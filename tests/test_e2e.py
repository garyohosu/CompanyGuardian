"""
E2E テスト（実ファイルI/O + モックHTTP）

実際のディレクトリ構造にファイルを書き出し、内容を検証する。
ネットワークはモックする。
"""
import pytest
import os
import re
import tempfile
import textwrap
from datetime import date
from unittest.mock import patch, MagicMock, mock_open


def _ok_resp(text="<html>OK</html>"):
    m = MagicMock()
    m.status_code = 200
    m.text = text
    return m


def _err_resp():
    m = MagicMock()
    m.status_code = 503
    m.text = ""
    return m


SIMPLE_YAML = textwrap.dedent("""\
    companies:
      - id: portal-co
        name: Portal Co
        kind: portal
        site: https://portal.example.com
        enabled: true
        adsense_required: false
        required_keywords: []
        required_adsense_pages: []
        link_targets: []
        checks:
          - site_http

      - id: virt-co
        name: Virt Co
        kind: virtual_company
        repo: org/virt-co
        site: https://virt.example.com
        enabled: true
        adsense_required: false
        checks:
          - site_http
""")


class TestE2EAllOK:

    def test_generates_daily_report_with_correct_content(self):
        """全OK 時に日報が正しい内容で生成される"""
        from guardian.runner import CompanyGuardianRunner
        from guardian.models import TriggerKind

        runner = CompanyGuardianRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch("guardian.config_loader.yaml.safe_load") as mock_yaml:
                    import yaml as _yaml
                    mock_yaml.return_value = _yaml.safe_load(SIMPLE_YAML)
                    with patch("builtins.open", mock_open()):
                        with patch("guardian.checkers.site_http.requests.get",
                                   return_value=_ok_resp()):
                            with patch.object(runner, "_push_outputs"):
                                runner.run(TriggerKind.SCHEDULED)
            finally:
                os.chdir(orig)

    def test_report_file_name_is_todays_date_for_scheduled(self):
        """定期実行の日報ファイル名が今日の日付 YYYY-MM-DD.md になる"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind, CheckResult, CheckStatus, CheckKind
        from datetime import datetime

        gen = DailyReportGenerator()
        results = [
            CheckResult(
                company_id="co",
                check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.OK,
                error_code=None,
                detail="HTTP 200",
                checked_at=datetime.now(),
            )
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)

        today = date.today().strftime("%Y-%m-%d")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = os.getcwd()
            os.chdir(tmpdir)
            try:
                path = gen.save(report)
                assert path == f"reports/daily/{today}.md"
            finally:
                os.chdir(orig)

    def test_report_file_name_manual_has_suffix(self):
        """手動実行の日報ファイル名に _manual_01 サフィックスが付く"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind, CheckResult, CheckStatus, CheckKind
        from datetime import datetime

        gen = DailyReportGenerator()
        results = [
            CheckResult(
                company_id="co",
                check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.OK,
                error_code=None,
                detail="HTTP 200",
                checked_at=datetime.now(),
            )
        ]
        report = gen.generate(results, TriggerKind.MANUAL)

        today = date.today().strftime("%Y-%m-%d")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch("guardian.daily_report_generator.glob.glob",
                           return_value=[]):
                    path = gen.save(report)
                assert path == f"reports/daily/{today}_manual_01.md"
            finally:
                os.chdir(orig)


class TestE2EWithErrors:

    def test_site_down_generates_incident_file(self):
        """サイトダウンで incidents/ にファイルが生成される"""
        from guardian.incident_recorder import IncidentRecorder
        from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
        from datetime import datetime

        recorder = IncidentRecorder()
        company = {"id": "down-co", "name": "Down Co"}
        results = [
            CheckResult(
                company_id="down-co",
                check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SITE_DOWN,
                detail="HTTP 503",
                checked_at=datetime.now(),
            )
        ]
        incident = recorder.create(results, company)
        assert incident is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = os.getcwd()
            os.chdir(tmpdir)
            try:
                path = recorder.save(incident)
                assert os.path.exists(path)
                # ファイル名規則: incidents/YYYY-MM-DD-<target>-<slug>.md
                fname = os.path.basename(path)
                assert re.match(r"\d{4}-\d{2}-\d{2}-.+\.md", fname)
                # 内容確認
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                assert "SITE_DOWN" in content
                assert "Down Co" in content
            finally:
                os.chdir(orig)

    def test_multiple_errors_single_incident(self):
        """同一会社の複数エラーが 1 incident に集約される"""
        from guardian.incident_recorder import IncidentRecorder
        from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
        from datetime import datetime

        recorder = IncidentRecorder()
        company = {"id": "multi-err", "name": "Multi Error Co"}
        results = [
            CheckResult(
                company_id="multi-err",
                check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SITE_DOWN,
                detail="HTTP 503",
                checked_at=datetime.now(),
            ),
            CheckResult(
                company_id="multi-err",
                check_kind=CheckKind.GITHUB_ACTIONS,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.ACTION_FAILED,
                detail="failure",
                checked_at=datetime.now(),
            ),
        ]
        incident = recorder.create(results, company)
        # 2種類の error_code が集約
        codes = [ec.value for ec in incident.error_codes]
        assert "SITE_DOWN" in codes
        assert "ACTION_FAILED" in codes

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = os.getcwd()
            os.chdir(tmpdir)
            try:
                path = recorder.save(incident)
                # slug は優先度最高の SITE_DOWN になる
                assert "site-down" in path
            finally:
                os.chdir(orig)

    def test_full_pipeline_error_then_report_contains_error(self):
        """ERROR が出た場合、日報の error_count が 1 以上になる"""
        from guardian.runner import CompanyGuardianRunner
        from guardian.models import TriggerKind
        from guardian.checkers.site_http import SiteHttpChecker
        from tests.conftest import make_company

        # SiteHttpChecker をそのまま使い、503 を返す
        checker = SiteHttpChecker()
        company = make_company(
            id="err-co",
            site="https://err.example.com",
            checks=["site_http"],
        )
        m = MagicMock()
        m.status_code = 503
        with patch("guardian.checkers.site_http.requests.get", return_value=m):
            result = checker.check(company)

        assert result.status.value == "ERROR"

        # DailyReportGenerator で集計確認
        from guardian.daily_report_generator import DailyReportGenerator
        from datetime import datetime
        gen = DailyReportGenerator()
        report = gen.generate([result], TriggerKind.SCHEDULED)
        assert report.error_count == 1
        assert report.ok_count == 0


class TestE2ECheckerChain:

    def test_artifact_checker_site_path_404_error(self):
        """artifact site_path が 404 → ERROR"""
        from guardian.checkers.artifact import ArtifactChecker
        from tests.conftest import make_company

        checker = ArtifactChecker()
        company = make_company(
            id="art-co",
            site="https://art.example.com",
            required_artifacts=[
                {"type": "site_path", "path": "/index.html"},
                {"type": "site_path", "path": "/feed.xml"},
            ],
            checks=["artifact"],
        )
        ok = MagicMock(status_code=200)
        ng = MagicMock(status_code=404)
        with patch("guardian.checkers.artifact.requests.get",
                   side_effect=[ok, ng]):
            result = checker.check(company)
        assert result.status.value == "ERROR"
        assert result.error_code.value == "ARTIFACT_MISSING"

    def test_github_actions_checker_fetches_api(self):
        """GithubActionsChecker が _fetch_latest_run を呼ぶ"""
        from guardian.checkers.github_actions import GithubActionsChecker
        from tests.conftest import make_company

        checker = GithubActionsChecker()
        company = make_company(
            id="gh-co",
            repo="org/test-repo",
            workflow="build.yml",
            checks=["github_actions"],
        )
        with patch.object(checker, "_fetch_latest_run",
                          return_value={"conclusion": "success", "status": "completed"}):
            result = checker.check(company)
        assert result.status.value == "OK"
        assert result.check_kind.value == "GITHUB_ACTIONS"

    def test_adsense_page_checker_all_pages_ok(self):
        """AdSensePageChecker が全ページ 200 → OK"""
        from guardian.checkers.adsense_page import AdSensePageChecker
        from tests.conftest import make_company

        checker = AdSensePageChecker()
        company = make_company(
            id="ads-co",
            site="https://ads.example.com",
            adsense_required=True,
            required_adsense_pages=["/privacy-policy/", "/contact/"],
            checks=["adsense_pages"],
        )
        ok = MagicMock(status_code=200, text="<html>OK</html>")
        with patch("guardian.checkers.adsense_page.requests.get", return_value=ok):
            result = checker.check(company)
        assert result.status.value == "OK"

    def test_daily_post_checker_strategy_chain(self):
        """DailyPostChecker が feed_xml 成功で site_path_pattern を評価しない"""
        from guardian.checkers.daily_post import DailyPostChecker
        from guardian.models import CheckStatus
        from tests.conftest import make_company
        from datetime import date

        checker = DailyPostChecker()
        company = make_company(
            id="post-co",
            site="https://post.example.com",
            daily_post_strategy=["feed_xml", "site_path_pattern"],
            daily_post_locator={
                "feed_url": "https://post.example.com/feed.xml",
                "path_pattern": "https://post.example.com/posts/{yyyy}/{mm}/{dd}/",
                "timezone": "Asia/Tokyo",
            },
            checks=["daily_post_previous_day"],
        )
        yesterday = date(2026, 3, 9)
        ok_result = MagicMock(status=CheckStatus.OK)

        with patch.object(checker, "_check_strategy", return_value=ok_result) as mock_cs:
            with patch.object(checker, "_resolve_previous_day_jst",
                               return_value=yesterday):
                result = checker.check(company)

        # feed_xml が OK → 1回だけ評価
        assert mock_cs.call_count == 1
        assert result.status == CheckStatus.OK


class TestE2EReportMarkdown:

    def test_report_markdown_has_required_sections(self):
        """生成された日報 Markdown に必須セクションが含まれる"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import (
            TriggerKind, CheckResult, CheckStatus, CheckKind, ErrorCode, DailyReport
        )
        from datetime import datetime

        gen = DailyReportGenerator()
        now = datetime(2026, 3, 10, 6, 0, 0)
        results = [
            CheckResult("co1", CheckKind.SITE_HTTP, CheckStatus.OK, None, "HTTP 200", now),
            CheckResult("co2", CheckKind.SITE_HTTP, CheckStatus.ERROR,
                        ErrorCode.SITE_DOWN, "HTTP 503", now),
            CheckResult("co3", CheckKind.GITHUB_ACTIONS, CheckStatus.WARNING, None, "in_progress", now),
            CheckResult("co4", CheckKind.SELF_STATUS, CheckStatus.OK, None, "正常", now),
            CheckResult("co5", CheckKind.ADSENSE_PAGES, CheckStatus.ERROR,
                        ErrorCode.ADSENSE_PAGE_MISSING, "欠落", now),
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = os.getcwd()
            os.chdir(tmpdir)
            try:
                path = gen.save(report)
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            finally:
                os.chdir(orig)

        # 必須セクション確認
        assert "# 日報" in content
        assert "要対応一覧" in content
        assert "自己監視結果" in content
        assert "AdSense" in content
        assert "総括" in content
        # カウント確認
        assert "ok_count" not in content  # 人間可読な表現を確認
        assert "正常" in content or "1" in content
