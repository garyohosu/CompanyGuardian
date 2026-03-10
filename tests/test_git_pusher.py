"""
GitPusher のテスト

担当クラス: GitPusher
責務: 出力 Markdown を git add → commit → push する。
"""
import pytest
from unittest.mock import patch, MagicMock, call


class TestGitPusher:

    def _make_pusher(self):
        from guardian.git_pusher import GitPusher
        return GitPusher()

    def test_push_outputs_returns_true_on_success(self):
        """git push 成功 → True"""
        pusher = self._make_pusher()
        files = ["reports/daily/2026-03-10.md"]
        with patch.object(pusher, "_git_add") as mock_add:
            with patch.object(pusher, "_git_commit") as mock_commit:
                with patch.object(pusher, "_git_push", return_value=True):
                    result = pusher.push_outputs(files)
        assert result is True

    def test_push_outputs_calls_git_add_with_files(self):
        """push_outputs が _git_add を正しいファイルで呼ぶ"""
        pusher = self._make_pusher()
        files = ["reports/daily/2026-03-10.md",
                 "incidents/2026-03-10-test-co.md"]
        with patch.object(pusher, "_git_add") as mock_add:
            with patch.object(pusher, "_git_commit"):
                with patch.object(pusher, "_git_push", return_value=True):
                    pusher.push_outputs(files)
        mock_add.assert_called_once_with(files)

    def test_push_outputs_calls_git_commit(self):
        """push_outputs が _git_commit を呼ぶ"""
        pusher = self._make_pusher()
        files = ["reports/daily/2026-03-10.md"]
        with patch.object(pusher, "_git_add"):
            with patch.object(pusher, "_git_commit") as mock_commit:
                with patch.object(pusher, "_git_push", return_value=True):
                    pusher.push_outputs(files)
        mock_commit.assert_called_once()

    def test_push_outputs_returns_false_on_push_failure(self):
        """git push 失敗 → False"""
        pusher = self._make_pusher()
        files = ["reports/daily/2026-03-10.md"]
        with patch.object(pusher, "_git_add"):
            with patch.object(pusher, "_git_commit"):
                with patch.object(pusher, "_git_push", return_value=False):
                    result = pusher.push_outputs(files)
        assert result is False

    def test_push_outputs_returns_false_on_exception(self):
        """git コマンド例外 → False（エラーログを残して終了）"""
        pusher = self._make_pusher()
        files = ["reports/daily/2026-03-10.md"]
        with patch.object(pusher, "_git_add", side_effect=RuntimeError("git error")):
            result = pusher.push_outputs(files)
        assert result is False

    def test_git_add_invokes_subprocess(self):
        """_git_add が subprocess を呼ぶ"""
        import subprocess
        pusher = self._make_pusher()
        with patch("guardian.git_pusher.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            pusher._git_add(["file.md"])
        mock_run.assert_called()

    def test_git_push_invokes_subprocess(self):
        """_git_push が subprocess を呼ぶ"""
        import subprocess
        pusher = self._make_pusher()
        with patch("guardian.git_pusher.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            pusher._git_push()
        mock_run.assert_called()

    def test_git_commit_message_contains_date(self):
        """commit メッセージに日付が含まれる"""
        import subprocess
        pusher = self._make_pusher()
        with patch("guardian.git_pusher.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            pusher._git_commit("2026-03-10 の日報")
        args = mock_run.call_args[0][0]
        assert "2026-03-10" in " ".join(str(a) for a in args)
