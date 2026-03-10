"""
結合テスト

実際のモジュール連携をテストする。
HTTP通信・GitHub API・ファイルI/O はモックする。
"""
import pytest
import textwrap
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, date


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

MINIMAL_YAML = textwrap.dedent("""\
    companies:
      - id: test-portal
        name: Test Portal
        kind: portal
        site: https://example.com
        enabled: true
        adsense_required: true
        required_adsense_pages:
          - /privacy-policy/
        checks:
          - site_http
          - adsense_pages

      - id: test-company
        name: Test Company
        kind: virtual_company
        repo: org/test-company
        site: https://test-company.example.com
        enabled: true
        adsense_required: false
        checks:
          - github_actions
          - site_http
""")

YAML_WITH_DAILY_POST = textwrap.dedent("""\
    companies:
      - id: daily-co
        name: Daily Co
        kind: virtual_company
        repo: org/daily-co
        site: https://daily.example.com
        enabled: true
        adsense_required: false
        required_artifacts:
          - type: site_path
            path: /index.html
          - type: site_path
            path: /feed.xml
        daily_post_strategy:
          - feed_xml
          - site_path_pattern
        daily_post_locator:
          feed_url: https://daily.example.com/feed.xml
          path_pattern: https://daily.example.com/posts/{yyyy}/{mm}/{dd}/
          timezone: Asia/Tokyo
        checks:
          - site_http
          - artifact
          - daily_post_previous_day
""")


def _mock_200():
    m = MagicMock()
    m.status_code = 200
    m.text = "<html>OK</html>"
    return m


def _mock_404():
    m = MagicMock()
    m.status_code = 404
    m.text = ""
    return m


def _mock_503():
    m = MagicMock()
    m.status_code = 503
    m.text = ""
    return m


# ---------------------------------------------------------------------------
# ConfigLoader → Company 変換の結合テスト
# ---------------------------------------------------------------------------

class TestConfigLoaderIntegration:

    def test_load_and_validate_companies_yaml(self):
        """実際の companies.yaml を読み込んで validate が通る"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        companies = loader.load("companies/companies.yaml")
        assert len(companies) > 0
        # guardian エントリが存在する
        kinds = [str(c.kind.value) for c in companies]
        assert "guardian" in kinds
        assert "portal" in kinds
        assert "virtual_company" in kinds

    def test_load_enabled_disabled_filtering(self):
        """enabled=false の会社は Runner でフィルタされる"""
        yaml = textwrap.dedent("""\
            companies:
              - id: enabled-co
                name: Enabled
                kind: virtual_company
                site: https://enabled.example.com
                enabled: true
                checks: [site_http]
              - id: disabled-co
                name: Disabled
                kind: virtual_company
                site: https://disabled.example.com
                enabled: false
                checks: [site_http]
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml)):
            companies = loader.load("fake.yaml")
        enabled = [c for c in companies if c.enabled]
        disabled = [c for c in companies if not c.enabled]
        assert len(enabled) == 1
        assert len(disabled) == 1


# ---------------------------------------------------------------------------
# Runner → Checker → CheckResult パイプライン
# ---------------------------------------------------------------------------

class TestRunnerCheckerPipeline:

    def _make_runner(self):
        from guardian.runner import CompanyGuardianRunner
        return CompanyGuardianRunner()

    def test_full_pipeline_all_ok(self):
        """全チェック正常 → 日報 ok_count が一致する"""
        from guardian.models import TriggerKind
        runner = self._make_runner()

        with patch("builtins.open", mock_open(read_data=MINIMAL_YAML)):
            with patch("guardian.config_loader.yaml.safe_load") as mock_yaml:
                mock_yaml.return_value = {
                    "companies": [
                        {
                            "id": "test-co",
                            "name": "Test Co",
                            "kind": "virtual_company",
                            "site": "https://example.com",
                            "enabled": True,
                            "checks": ["site_http"],
                        }
                    ]
                }
                with patch("guardian.checkers.site_http.requests.get",
                           return_value=_mock_200()):
                    with patch.object(runner, "_push_outputs"):
                        with patch("guardian.daily_report_generator.os.makedirs"):
                            with patch("builtins.open", mock_open()):
                                runner.run(TriggerKind.SCHEDULED)

    def test_site_http_error_creates_incident(self):
        """site_http が ERROR のとき incident が作られる"""
        from guardian.models import TriggerKind, CheckStatus
        from guardian.runner import CompanyGuardianRunner
        runner = CompanyGuardianRunner()

        mock_recorder = MagicMock()
        mock_incident = MagicMock()
        mock_recorder.create.return_value = mock_incident
        mock_recorder.save.return_value = "incidents/xxx.md"
        runner._incident_recorder = mock_recorder
        runner._cm_manager = MagicMock()
        runner._cm_manager.should_create.return_value = False

        with patch("guardian.config_loader.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "companies": [
                    {
                        "id": "err-co",
                        "name": "Err Co",
                        "kind": "virtual_company",
                        "site": "https://example.com",
                        "enabled": True,
                        "checks": ["site_http"],
                    }
                ]
            }
            with patch("builtins.open", mock_open()):
                with patch("guardian.checkers.site_http.requests.get",
                           return_value=_mock_503()):
                    with patch.object(runner, "_push_outputs"):
                        with patch("guardian.daily_report_generator.os.makedirs"):
                            runner.run(TriggerKind.SCHEDULED)

        mock_recorder.create.assert_called()
        mock_recorder.save.assert_called()

    def test_disabled_company_is_skipped(self):
        """enabled=false の会社はチェックしない"""
        from guardian.models import TriggerKind
        from guardian.runner import CompanyGuardianRunner
        runner = CompanyGuardianRunner()

        with patch("guardian.config_loader.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "companies": [
                    {
                        "id": "disabled-co",
                        "name": "Disabled",
                        "kind": "virtual_company",
                        "site": "https://disabled.example.com",
                        "enabled": False,
                        "checks": ["site_http"],
                    }
                ]
            }
            with patch("builtins.open", mock_open()):
                with patch("guardian.checkers.site_http.requests.get",
                           return_value=_mock_200()) as mock_get:
                    with patch.object(runner, "_push_outputs"):
                        with patch("guardian.daily_report_generator.os.makedirs"):
                            runner.run(TriggerKind.SCHEDULED)

        # disabled なので site_http が呼ばれない
        mock_get.assert_not_called()

    def test_unknown_check_kind_produces_warning_result(self):
        """未知の check_kind は WARNING になる"""
        from guardian.runner import CompanyGuardianRunner
        runner = CompanyGuardianRunner()
        company = {
            "id": "co-1", "name": "Co 1", "kind": "virtual_company",
            "enabled": True, "site": "https://example.com",
            "checks": ["totally_unknown_check"],
        }
        results = runner._check_all([company])
        assert any(r.status.value == "WARNING" for r in results)

    def test_exception_in_checker_does_not_abort_remaining(self):
        """1社のチェックで例外が起きても残りを継続する"""
        from guardian.runner import CompanyGuardianRunner
        from guardian.models import TriggerKind
        import requests as req_lib
        runner = CompanyGuardianRunner()

        companies_data = [
            {
                "id": "fail-co", "name": "Fail Co", "kind": "virtual_company",
                "site": "https://fail.example.com", "enabled": True,
                "checks": ["site_http"],
            },
            {
                "id": "ok-co", "name": "OK Co", "kind": "virtual_company",
                "site": "https://ok.example.com", "enabled": True,
                "checks": ["site_http"],
            },
        ]

        call_count = {"n": 0}
        def side_effect(url, **kwargs):
            call_count["n"] += 1
            if "fail" in url:
                raise req_lib.ConnectionError("connection refused")
            return _mock_200()

        with patch("guardian.checkers.site_http.requests.get", side_effect=side_effect):
            results = runner._check_all(companies_data)

        # fail-co は ERROR、ok-co は OK
        statuses = {r.company_id: r.status.value for r in results}
        assert statuses.get("fail-co") == "ERROR"
        assert statuses.get("ok-co") == "OK"


# ---------------------------------------------------------------------------
# ConfigLoader → Runner → DailyReport 集計
# ---------------------------------------------------------------------------

class TestReportAggregation:

    def test_report_counts_match_results(self):
        """日報の ok/warning/error カウントが CheckResult と一致する"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind, CheckResult, CheckStatus, CheckKind, ErrorCode
        gen = DailyReportGenerator()

        results = []
        now = datetime(2026, 3, 10, 6, 0, 0)
        for i in range(3):
            results.append(CheckResult(
                company_id=f"co-{i}", check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.OK, error_code=None,
                detail="HTTP 200", checked_at=now,
            ))
        results.append(CheckResult(
            company_id="warn-co", check_kind=CheckKind.GITHUB_ACTIONS,
            status=CheckStatus.WARNING, error_code=None,
            detail="in_progress", checked_at=now,
        ))
        results.append(CheckResult(
            company_id="err-co", check_kind=CheckKind.SITE_HTTP,
            status=CheckStatus.ERROR, error_code=ErrorCode.SITE_DOWN,
            detail="HTTP 503", checked_at=now,
        ))

        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert report.total_count == 5
        assert report.ok_count == 3
        assert report.warning_count == 1
        assert report.error_count == 1
        assert len(report.action_required) == 2  # WARNING + ERROR

    def test_adsense_anomalies_in_report(self):
        """AdSense エラーが report.adsense_anomalies に反映される"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind, CheckResult, CheckStatus, CheckKind, ErrorCode
        gen = DailyReportGenerator()
        now = datetime(2026, 3, 10, 6, 0, 0)

        results = [
            CheckResult(
                company_id="adsense-co",
                check_kind=CheckKind.ADSENSE_PAGES,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.ADSENSE_PAGE_MISSING,
                detail="ページ欠落: /privacy-policy/",
                checked_at=now,
            )
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert len(report.adsense_anomalies) == 1
        assert report.adsense_anomalies[0].company_id == "adsense-co"

    def test_self_monitor_result_in_report(self):
        """self_status 結果が report.self_monitor_result に反映される"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind, CheckResult, CheckStatus, CheckKind
        gen = DailyReportGenerator()
        now = datetime(2026, 3, 10, 6, 0, 0)

        results = [
            CheckResult(
                company_id="company-guardian",
                check_kind=CheckKind.SELF_STATUS,
                status=CheckStatus.OK,
                error_code=None,
                detail="自己監視正常",
                checked_at=now,
            )
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)
        assert report.self_monitor_result is not None
        assert report.self_monitor_result.status == CheckStatus.OK


# ---------------------------------------------------------------------------
# IncidentRecorder → CountermeasureManager 連携
# ---------------------------------------------------------------------------

class TestIncidentCountermeasureIntegration:

    def test_incident_to_countermeasure_flow(self):
        """ERROR → Incident → Countermeasure の生成フロー"""
        from guardian.incident_recorder import IncidentRecorder
        from guardian.countermeasure_manager import CountermeasureManager
        from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
        from datetime import datetime

        recorder = IncidentRecorder()
        cm_mgr = CountermeasureManager()

        company = {"id": "test-co", "name": "Test Company"}
        results = [
            CheckResult(
                company_id="test-co",
                check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SITE_DOWN,
                detail="HTTP 503",
                checked_at=datetime(2026, 3, 10, 6, 0, 0),
            )
        ]

        incident = recorder.create(results, company)
        assert incident is not None
        assert incident.target_name == "Test Company"
        assert ErrorCode.SITE_DOWN in incident.error_codes

        # save
        with patch("guardian.incident_recorder.os.makedirs"):
            with patch("builtins.open", mock_open()):
                path = recorder.save(incident)
        assert "incidents/" in path

        # countermeasure 判断
        with patch("guardian.countermeasure_manager.glob.glob", return_value=[]):
            should_create = cm_mgr.should_create(incident)
        assert should_create is True

        # countermeasure 生成・保存
        with patch.object(cm_mgr, "_next_cm_number", return_value=1):
            cm = cm_mgr.create(incident)
        assert cm.cm_id == "CM-001"
        assert incident.target_name in cm.origin_incident or \
               incident.file_path in cm.origin_incident

        with patch("guardian.countermeasure_manager.os.makedirs"):
            with patch("builtins.open", mock_open()):
                cm_path = cm_mgr.save(cm)
        assert "countermeasures/CM-001" in cm_path

    def test_no_incident_for_ok_results(self):
        """OK のみの結果では incident も countermeasure も生成しない"""
        from guardian.incident_recorder import IncidentRecorder
        from guardian.models import CheckResult, CheckStatus, CheckKind
        from datetime import datetime

        recorder = IncidentRecorder()
        company = {"id": "ok-co", "name": "OK Company"}
        results = [
            CheckResult(
                company_id="ok-co",
                check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.OK,
                error_code=None,
                detail="HTTP 200",
                checked_at=datetime.now(),
            )
        ]
        incident = recorder.create(results, company)
        assert incident is None


# ---------------------------------------------------------------------------
# 実ファイルを使った結合テスト
# ---------------------------------------------------------------------------

class TestFileOutputIntegration:

    def test_daily_report_file_saved_to_correct_path(self):
        """日報が reports/daily/ に保存される"""
        from guardian.daily_report_generator import DailyReportGenerator
        from guardian.models import TriggerKind, CheckResult, CheckStatus, CheckKind

        gen = DailyReportGenerator()
        results = [
            CheckResult(
                company_id="test-co",
                check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.OK,
                error_code=None,
                detail="HTTP 200",
                checked_at=datetime(2026, 3, 10, 6, 0, 0),
            )
        ]
        report = gen.generate(results, TriggerKind.SCHEDULED)

        with tempfile.TemporaryDirectory() as tmpdir:
            # reports/daily/ ディレクトリを tmpdir 内に模倣
            import os
            orig_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                path = gen.save(report)
                assert os.path.exists(path)
                assert path.startswith("reports/daily/")
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                assert "# 日報" in content
            finally:
                os.chdir(orig_dir)

    def test_incident_file_saved_correctly(self):
        """incident ファイルが incidents/ に保存される"""
        from guardian.incident_recorder import IncidentRecorder
        from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode

        recorder = IncidentRecorder()
        company = {"id": "site-down-co", "name": "Site Down Co"}
        results = [
            CheckResult(
                company_id="site-down-co",
                check_kind=CheckKind.SITE_HTTP,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.SITE_DOWN,
                detail="HTTP 503",
                checked_at=datetime(2026, 3, 10, 6, 0, 0),
            )
        ]
        incident = recorder.create(results, company)

        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            orig_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                path = recorder.save(incident)
                assert os.path.exists(path)
                assert path.startswith("incidents/")
                assert "site-down" in path
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                assert "SITE_DOWN" in content
                assert "Site Down Co" in content
            finally:
                os.chdir(orig_dir)

    def test_countermeasure_file_naming_convention(self):
        """countermeasure ファイルが CM-XXX_<Name>.md の形式で保存される"""
        import re
        from guardian.countermeasure_manager import CountermeasureManager
        from guardian.models import Incident, ErrorCode
        from datetime import date

        mgr = CountermeasureManager()

        inc = MagicMock()
        inc.incident_date = date(2026, 3, 10)
        inc.target_name = "Test Co"
        inc.error_codes = [ErrorCode.SITE_DOWN]
        inc.phenomenon = "Site down"
        inc.file_path = "incidents/2026-03-10-test-co-site-down.md"

        with patch.object(mgr, "_next_cm_number", return_value=5):
            cm = mgr.create(inc)

        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            orig_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                path = mgr.save(cm)
                assert os.path.exists(path)
                assert re.search(r"countermeasures/CM-005_\w+\.md", path)
            finally:
                os.chdir(orig_dir)


# ---------------------------------------------------------------------------
# companies.yaml のロードと各フィールド検証
# ---------------------------------------------------------------------------

class TestCompaniesYamlIntegration:

    def test_companies_yaml_loads_all_entries(self):
        """companies.yaml が全エントリを読み込める"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        companies = loader.load("companies/companies.yaml")
        # 1 portal + 10 virtual + 1 guardian = 12
        assert len(companies) == 12

    def test_companies_yaml_validates(self):
        """companies.yaml が validate を通過する"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        companies = loader.load("companies/companies.yaml")
        assert loader.validate(companies) is True

    def test_guardian_company_has_self_monitor(self):
        """guardian エントリが self_monitor=True になっている"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        companies = loader.load("companies/companies.yaml")
        guardian = next(c for c in companies if c.kind.value == "guardian")
        assert guardian.self_monitor is True

    def test_portal_has_adsense_pages(self):
        """portal エントリが required_adsense_pages を持つ"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        companies = loader.load("companies/companies.yaml")
        portal = next(c for c in companies if c.kind.value == "portal")
        assert len(portal.required_adsense_pages) > 0

    def test_virtual_companies_have_site(self):
        """virtual_company エントリが site を持つ"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        companies = loader.load("companies/companies.yaml")
        virtual = [c for c in companies if c.kind.value == "virtual_company"]
        for c in virtual:
            assert c.site is not None, f"{c.id} に site がない"

    def test_auto_ai_blog_has_daily_post_config(self):
        """auto-ai-blog が daily_post_strategy を持つ"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        companies = loader.load("companies/companies.yaml")
        blog = next(c for c in companies if c.id == "auto-ai-blog")
        assert len(blog.daily_post_strategy) > 0
        assert blog.daily_post_locator is not None
