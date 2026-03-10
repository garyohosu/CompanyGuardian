from unittest.mock import MagicMock, patch


class TestGitHubAuthResolver:
    def test_env_token_has_priority(self):
        from guardian.github_auth import GitHubAuthResolver

        resolver = GitHubAuthResolver()
        with patch.dict("os.environ", {"GITHUB_TOKEN": "token-value"}, clear=True):
            with patch("guardian.github_auth.shutil.which") as mock_which:
                status = resolver.get_auth_status(refresh=True)

        assert status.mode == "env_token"
        mock_which.assert_not_called()

    def test_gh_cli_mode_when_auth_status_succeeds(self):
        from guardian.github_auth import GitHubAuthResolver

        resolver = GitHubAuthResolver()
        completed = MagicMock(returncode=0, stdout="Logged in", stderr="")
        with patch.dict("os.environ", {}, clear=True):
            with patch("guardian.github_auth.shutil.which", return_value="C:\\bin\\gh.exe"):
                with patch("guardian.github_auth.subprocess.run", return_value=completed):
                    status = resolver.get_auth_status(refresh=True)

        assert status.mode == "gh_cli"

    def test_none_mode_when_no_token_and_no_gh(self):
        from guardian.github_auth import GitHubAuthResolver

        resolver = GitHubAuthResolver()
        with patch.dict("os.environ", {}, clear=True):
            with patch("guardian.github_auth.shutil.which", return_value=None):
                status = resolver.get_auth_status(refresh=True)

        assert status.mode == "none"


class TestGitHubRepoClient:
    def test_rerun_failed_jobs_uses_gh_cli_transport(self):
        from guardian.github_auth import GitHubApiResponse, GitHubAuthResolver, GitHubAuthStatus
        from guardian.github_client import GitHubRepoClient

        auth = GitHubAuthResolver()
        client = GitHubRepoClient(auth=auth)
        with patch.object(auth, "get_auth_status", return_value=GitHubAuthStatus(mode="gh_cli")):
            with patch.object(auth, "run_gh_api", return_value=GitHubApiResponse(status_code=201, text="")) as mock_run:
                ok, status_code = client.rerun_failed_jobs("org/repo", 123)

        assert ok is True
        assert status_code == 201
        mock_run.assert_called_once()
