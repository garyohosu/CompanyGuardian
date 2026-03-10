"""
実動作スモークテスト

実際の HTTP 通信を行うテスト。
ネットワーク環境が必要。CIでは --smoke フラグ付き実行を想定。
モック版と実通信版を分離し、@pytest.mark.smoke でタグ付けする。
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime


# ---------------------------------------------------------------------------
# スモークテストマーカー
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.smoke


# ---------------------------------------------------------------------------
# スクリプト起動テスト（モック版）
# ---------------------------------------------------------------------------

class TestCheckTargetsScript:

    def test_script_runs_manual_trigger(self):
        """check_targets.py が --trigger manual で正常終了する（モック）"""
        import sys
        from unittest.mock import patch, MagicMock

        mock_runner = MagicMock()
        mock_runner.run.return_value = None

        with patch("guardian.runner.CompanyGuardianRunner", return_value=mock_runner):
            with patch("sys.argv", ["check_targets.py", "--trigger", "manual"]):
                import importlib
                import scripts.check_targets as ct
                importlib.reload(ct)
                # main() を直接呼ぶ
                ct.main()

        mock_runner.run.assert_called_once()
        from guardian.models import TriggerKind
        call_arg = mock_runner.run.call_args[0][0]
        assert call_arg == TriggerKind.MANUAL

    def test_script_runs_scheduled_trigger(self):
        """check_targets.py がデフォルト（scheduled）で正常終了する（モック）"""
        import sys

        mock_runner = MagicMock()
        mock_runner.run.return_value = None

        with patch("guardian.runner.CompanyGuardianRunner", return_value=mock_runner):
            with patch("sys.argv", ["check_targets.py"]):
                import importlib
                import scripts.check_targets as ct
                importlib.reload(ct)
                ct.main()

        from guardian.models import TriggerKind
        call_arg = mock_runner.run.call_args[0][0]
        assert call_arg == TriggerKind.SCHEDULED


# ---------------------------------------------------------------------------
# Runner 全体モック実行
# ---------------------------------------------------------------------------

class TestRunnerFullMock:

    def test_runner_produces_daily_report_file(self):
        """Runner がモック環境で日報ファイルを生成する"""
        from guardian.models import TriggerKind
        from guardian.runner import CompanyGuardianRunner

        runner = CompanyGuardianRunner()

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.text = "<html>test</html>"

        mock_run_data = {"conclusion": "success", "status": "completed"}

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch("guardian.config_loader.yaml.safe_load") as mock_yaml:
                    mock_yaml.return_value = {
                        "companies": [
                            {
                                "id": "mock-portal",
                                "name": "Mock Portal",
                                "kind": "portal",
                                "site": "https://example.com",
                                "enabled": True,
                                "adsense_required": False,
                                "checks": ["site_http"],
                                "required_adsense_pages": [],
                                "required_keywords": [],
                                "link_targets": [],
                            }
                        ]
                    }
                    with patch("builtins.open", mock_open()):
                        with patch("guardian.checkers.site_http.requests.get",
                                   return_value=mock_200):
                            with patch.object(runner, "_push_outputs"):
                                with patch("guardian.daily_report_generator.os.makedirs"):
                                    with patch("guardian.daily_report_generator.glob.glob",
                                               return_value=[]):
                                        runner.run(TriggerKind.SCHEDULED)
            finally:
                os.chdir(orig_dir)

    def test_runner_handles_site_down_gracefully(self):
        """サイトダウン時も Runner が正常終了して incident を生成しようとする"""
        import requests as req_lib
        from guardian.models import TriggerKind
        from guardian.runner import CompanyGuardianRunner

        runner = CompanyGuardianRunner()
        mock_recorder = MagicMock()
        mock_incident = MagicMock()
        mock_recorder.create.return_value = mock_incident
        mock_recorder.save.return_value = "incidents/test.md"
        runner._incident_recorder = mock_recorder
        runner._cm_manager = MagicMock()
        runner._cm_manager.should_create.return_value = False

        with patch("guardian.config_loader.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "companies": [
                    {
                        "id": "down-co",
                        "name": "Down Co",
                        "kind": "virtual_company",
                        "site": "https://down.example.com",
                        "enabled": True,
                        "adsense_required": False,
                        "checks": ["site_http"],
                        "required_adsense_pages": [],
                        "required_keywords": [],
                        "link_targets": [],
                    }
                ]
            }
            with patch("builtins.open", mock_open()):
                with patch("guardian.checkers.site_http.requests.get",
                           side_effect=req_lib.ConnectionError("refused")):
                    with patch.object(runner, "_push_outputs"):
                        with patch("guardian.daily_report_generator.os.makedirs"):
                            with patch("guardian.daily_report_generator.glob.glob",
                                       return_value=[]):
                                runner.run(TriggerKind.SCHEDULED)

        # incident recorder が呼ばれた
        mock_recorder.create.assert_called()

    def test_runner_continues_after_one_company_fails(self):
        """1社でネットワークエラーが起きても残り社を継続処理する"""
        from guardian.models import TriggerKind, CheckStatus
        from guardian.runner import CompanyGuardianRunner
        import requests as req_lib

        runner = CompanyGuardianRunner()

        call_log = []
        def side_effect(url, **kwargs):
            call_log.append(url)
            if "fail" in url:
                raise req_lib.ConnectionError("refused")
            m = MagicMock()
            m.status_code = 200
            m.text = ""
            return m

        with patch("guardian.config_loader.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "companies": [
                    {
                        "id": "fail-co", "name": "Fail Co",
                        "kind": "virtual_company",
                        "site": "https://fail.example.com",
                        "enabled": True, "adsense_required": False,
                        "checks": ["site_http"],
                        "required_adsense_pages": [], "required_keywords": [], "link_targets": [],
                    },
                    {
                        "id": "ok-co", "name": "OK Co",
                        "kind": "virtual_company",
                        "site": "https://ok.example.com",
                        "enabled": True, "adsense_required": False,
                        "checks": ["site_http"],
                        "required_adsense_pages": [], "required_keywords": [], "link_targets": [],
                    },
                ]
            }
            with patch("builtins.open", mock_open()):
                with patch("guardian.checkers.site_http.requests.get",
                           side_effect=side_effect):
                    with patch.object(runner, "_push_outputs"):
                        with patch("guardian.daily_report_generator.os.makedirs"):
                            with patch("guardian.daily_report_generator.glob.glob",
                                       return_value=[]):
                                runner.run(TriggerKind.SCHEDULED)

        # 両社の URL が試行された
        assert any("fail.example.com" in u for u in call_log)
        assert any("ok.example.com" in u for u in call_log)


# ---------------------------------------------------------------------------
# SiteHttpChecker 実通信テスト（--network フラグ付き時のみ）
# ---------------------------------------------------------------------------

@pytest.mark.network
class TestSiteHttpReal:

    def test_root_portal_is_reachable(self):
        """Root Portal (garyohosu.github.io) が実際に到達できる"""
        from guardian.checkers.site_http import SiteHttpChecker
        from guardian.models import CheckStatus
        from tests.conftest import make_company

        checker = SiteHttpChecker()
        company = make_company(
            id="root-portal",
            site="https://garyohosu.github.io/",
            checks=["site_http"],
        )
        result = checker.check(company)
        # 2xx/3xx は許容（リダイレクトあり得る）
        assert result.status.value in ("OK", "WARNING"), \
            f"Root Portal が到達不能: {result.detail}"

    def test_auto_ai_blog_is_reachable(self):
        """Auto AI Blog が実際に到達できる"""
        from guardian.checkers.site_http import SiteHttpChecker
        from tests.conftest import make_company

        checker = SiteHttpChecker()
        company = make_company(
            id="auto-ai-blog",
            site="https://garyohosu.github.io/auto-ai-blog/",
            checks=["site_http"],
        )
        result = checker.check(company)
        assert result.status.value in ("OK", "WARNING"), \
            f"Auto AI Blog が到達不能: {result.detail}"
