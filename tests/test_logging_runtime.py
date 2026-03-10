import logging
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestLoggingSetup:
    def test_setup_logging_writes_to_stdout_and_file(self, tmp_path, monkeypatch, capsys):
        from guardian.logging_utils import setup_logging

        monkeypatch.chdir(tmp_path)
        log_path = tmp_path / "logs" / "company_guardian.log"
        setup_logging(force=True, log_path=str(log_path))

        logging.getLogger("test-logger").info("runtime log visible")
        captured = capsys.readouterr()

        assert "[INFO] runtime log visible" in captured.out
        assert log_path.exists()
        assert "runtime log visible" in log_path.read_text(encoding="utf-8")


class TestRunnerLogging:
    def test_runner_logs_target_progress_and_result(self, caplog):
        from guardian.runner import CompanyGuardianRunner
        from guardian.models import CheckResult, CheckStatus, CheckKind
        from tests.conftest import make_company

        mock_checker = MagicMock()
        mock_checker.check.return_value = CheckResult(
            company_id="demo-co",
            check_kind=CheckKind.SITE_HTTP,
            status=CheckStatus.OK,
            error_code=None,
            detail="HTTP 200",
            checked_at=datetime(2026, 3, 10, 6, 0, 0),
        )

        with patch("guardian.runner.setup_logging", return_value="logs/company_guardian.log"):
            runner = CompanyGuardianRunner()

        company = make_company(id="demo-co", checks=["site_http"])
        with caplog.at_level(logging.INFO):
            with patch("guardian.runner.CHECKER_REGISTRY", {"site_http": lambda: mock_checker}):
                runner._check_all([company])

        messages = [record.getMessage() for record in caplog.records]
        assert any("target=demo-co kind=virtual_company checks=site_http" in msg for msg in messages)
        assert any("target=demo-co check=site_http start" in msg for msg in messages)
        assert any("target=demo-co check=site_http result=OK message=\"HTTP 200\"" in msg for msg in messages)


class TestGitPusherLogging:
    def test_git_pusher_logs_targets_and_push_result(self, caplog):
        from guardian.git_pusher import GitPusher

        pusher = GitPusher()
        with caplog.at_level(logging.INFO):
            with patch.object(pusher, "_git_add") as mock_add:
                with patch.object(pusher, "_git_commit", return_value=True):
                    with patch.object(pusher, "_git_push", return_value=True):
                        result = pusher.push_outputs(["reports/daily/2026-03-10.md"])

        assert result is True
        messages = [record.getMessage() for record in caplog.records]
        assert any("git add targets=reports/daily/2026-03-10.md" in msg for msg in messages)
        assert any("git commit result=OK" in msg for msg in messages)
        assert any("git push result=OK" in msg for msg in messages)
