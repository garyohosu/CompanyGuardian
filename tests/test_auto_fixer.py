"""
AutoFixer のテスト

担当クラス: AutoFixer
責務: README コピー、GitHub Actions 低リスク再試行
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from guardian.github_auth import GitHubAuthStatus


class TestAutoFixerReadme:

    def test_readme_copy_when_no_readme_md(self, tmp_path, monkeypatch):
        """README.md が無く README.txt がある場合、自動コピーされる"""
        from guardian.auto_fixer import AutoFixer
        monkeypatch.chdir(tmp_path)
        readme_txt = tmp_path / "README.txt"
        readme_txt.write_text("# テスト README\n## 目的\n", encoding="utf-8")

        fixer = AutoFixer()
        result = fixer.fix_readme_if_needed()

        assert result is not None
        assert result.status == "OK"
        assert os.path.exists("README.md")
        assert "README.md" in result.changed_files

    def test_no_fix_when_readme_md_exists(self, tmp_path, monkeypatch):
        """README.md が既に存在する場合は修正不要で None を返す"""
        from guardian.auto_fixer import AutoFixer
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# 既存 README\n", encoding="utf-8")

        fixer = AutoFixer()
        result = fixer.fix_readme_if_needed()

        assert result is None

    def test_no_fix_when_neither_readme_exists(self, tmp_path, monkeypatch):
        """README.md も README.txt もない場合は修正不要で None を返す"""
        from guardian.auto_fixer import AutoFixer
        monkeypatch.chdir(tmp_path)

        fixer = AutoFixer()
        result = fixer.fix_readme_if_needed()

        assert result is None

    def test_readme_copy_preserves_content(self, tmp_path, monkeypatch):
        """コピーした README.md の内容が README.txt と同じ"""
        from guardian.auto_fixer import AutoFixer
        monkeypatch.chdir(tmp_path)
        content = "# テスト\n## 目的\nテスト用\n"
        (tmp_path / "README.txt").write_text(content, encoding="utf-8")

        fixer = AutoFixer()
        fixer.fix_readme_if_needed()

        with open("README.md", encoding="utf-8") as f:
            assert f.read() == content

    def test_readme_txt_not_deleted_after_copy(self, tmp_path, monkeypatch):
        """コピー後も README.txt は削除されない"""
        from guardian.auto_fixer import AutoFixer
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.txt").write_text("# テスト\n", encoding="utf-8")

        fixer = AutoFixer()
        fixer.fix_readme_if_needed()

        assert os.path.exists("README.txt")

    def test_readme_fix_returns_fail_on_error(self, tmp_path, monkeypatch):
        """コピーに失敗した場合 FAIL を返す"""
        from guardian.auto_fixer import AutoFixer
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.txt").write_text("# テスト\n", encoding="utf-8")

        fixer = AutoFixer()
        with patch("guardian.auto_fixer.shutil.copy2", side_effect=OSError("permission denied")):
            result = fixer.fix_readme_if_needed()

        assert result is not None
        assert result.status == "FAIL"
        assert "FAIL" in result.status


class TestAutoFixerGithubActions:

    def _make_fixer(self):
        from guardian.auto_fixer import AutoFixer, _retried_runs
        _retried_runs.clear()
        return AutoFixer()

    def test_skip_when_no_repo(self):
        """repo 未設定の場合はスキップ"""
        fixer = self._make_fixer()
        result = fixer.retry_github_actions_if_applicable("test-co", "")
        assert result.status == "SKIP"

    def test_skip_when_no_token(self):
        """認証手段なしの場合はスキップ"""
        fixer = self._make_fixer()
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="none")):
            result = fixer.retry_github_actions_if_applicable("test-co", "org/repo")
        assert result.status == "SKIP"
        assert "GitHub 認証手段なし" in result.message

    def test_skip_when_conclusion_is_cancelled(self):
        """conclusion=cancelled は再試行対象外"""
        fixer = self._make_fixer()
        mock_run = {"id": 123, "conclusion": "cancelled", "status": "completed"}
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="env_token")):
            with patch.object(fixer, "_fetch_latest_run", return_value=mock_run):
                result = fixer.retry_github_actions_if_applicable("test-co", "org/repo")
        assert result.status == "SKIP"
        assert "再試行対象外" in result.message

    def test_skip_when_conclusion_is_timed_out(self):
        """conclusion=timed_out は再試行対象外"""
        fixer = self._make_fixer()
        mock_run = {"id": 123, "conclusion": "timed_out", "status": "completed"}
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="env_token")):
            with patch.object(fixer, "_fetch_latest_run", return_value=mock_run):
                result = fixer.retry_github_actions_if_applicable("test-co", "org/repo")
        assert result.status == "SKIP"

    def test_retry_once_for_failure(self):
        """conclusion=failure で未試行なら 1 回再試行する"""
        fixer = self._make_fixer()
        mock_run = {"id": 456, "conclusion": "failure", "status": "completed"}
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="env_token")):
            with patch.object(fixer, "_fetch_latest_run", return_value=mock_run):
                with patch.object(fixer._github, "rerun_failed_jobs", return_value=(True, 201)):
                    result = fixer.retry_github_actions_if_applicable("test-co", "org/repo")
        assert result.status == "WARN"
        assert "再試行" in result.message

    def test_retry_only_once_per_run(self):
        """同一 run_id は 2 回目以降スキップされる"""
        fixer = self._make_fixer()
        mock_run = {"id": 789, "conclusion": "failure", "status": "completed"}
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="env_token")):
            with patch.object(fixer, "_fetch_latest_run", return_value=mock_run):
                with patch.object(fixer._github, "rerun_failed_jobs", return_value=(True, 201)):
                    first = fixer.retry_github_actions_if_applicable("test-co", "org/repo")
                    second = fixer.retry_github_actions_if_applicable("test-co", "org/repo")

        assert first.status == "WARN"
        assert second.status == "SKIP"
        assert "既に再試行済み" in second.message

    def test_retry_fail_on_api_error(self):
        """再試行 API が 4xx を返した場合 FAIL"""
        fixer = self._make_fixer()
        mock_run = {"id": 999, "conclusion": "failure", "status": "completed"}
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="env_token")):
            with patch.object(fixer, "_fetch_latest_run", return_value=mock_run):
                with patch.object(fixer._github, "rerun_failed_jobs", return_value=(False, 403)):
                    result = fixer.retry_github_actions_if_applicable("test-co", "org/repo")
        assert result.status == "FAIL"

    def test_skip_when_run_fetch_fails(self):
        """最新 run 取得失敗時はスキップ"""
        fixer = self._make_fixer()
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="env_token")):
            with patch.object(fixer, "_fetch_latest_run", return_value=None):
                result = fixer.retry_github_actions_if_applicable("test-co", "org/repo")
        assert result.status == "SKIP"

    def test_gh_cli_auth_allows_retry(self):
        """gh auth 済みなら GITHUB_TOKEN なしでも再試行する"""
        fixer = self._make_fixer()
        mock_run = {"id": 222, "conclusion": "failure", "status": "completed"}
        with patch.object(fixer._github, "get_auth_status", return_value=GitHubAuthStatus(mode="gh_cli")):
            with patch.object(fixer, "_fetch_latest_run", return_value=mock_run):
                with patch.object(fixer._github, "rerun_failed_jobs", return_value=(True, 201)):
                    result = fixer.retry_github_actions_if_applicable("test-co", "org/repo")

        assert result.status == "WARN"
        assert "auth=gh_cli" in result.message
