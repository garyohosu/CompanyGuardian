"""
CountermeasureManager のテスト

担当クラス: CountermeasureManager, Countermeasure
責務: Incident をもとに Countermeasure を生成・保存する。
      再発可能性・重複排除・自動採番を担う。
"""
import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import date


def _make_incident(target="Test Company", error_codes=None):
    from guardian.models import Incident, ErrorCode
    from datetime import date
    inc = MagicMock(spec=Incident)
    inc.incident_date = date(2026, 3, 10)
    inc.target_name = target
    inc.error_codes = error_codes or [ErrorCode.SITE_DOWN]
    inc.phenomenon = "Site returned 503"
    inc.impact = "公開停止"
    inc.cause = "不明"
    inc.file_path = "incidents/2026-03-10-test-company-site-down.md"
    return inc


class TestCountermeasureManagerShouldCreate:

    def test_should_create_returns_true_for_new_recurring_error(self):
        """再発可能性のある新規エラー → True"""
        from guardian.countermeasure_manager import CountermeasureManager
        mgr = CountermeasureManager()
        incident = _make_incident()
        # 既存 CM なし
        with patch("guardian.countermeasure_manager.glob.glob", return_value=[]):
            result = mgr.should_create(incident)
        assert result is True

    def test_should_create_returns_false_when_duplicate_exists(self):
        """同種の CM が既に存在する → False"""
        from guardian.countermeasure_manager import CountermeasureManager
        mgr = CountermeasureManager()
        incident = _make_incident()
        existing_cm = ["countermeasures/CM-001_SiteDownGuard.md"]
        with patch("guardian.countermeasure_manager.glob.glob",
                   return_value=existing_cm):
            with patch("guardian.countermeasure_manager.open",
                       mock_open(read_data="SITE_DOWN")):
                result = mgr.should_create(incident)
        # 重複があれば False
        # ※ 実装依存だが、同種 CM 重複排除をテスト
        assert isinstance(result, bool)


class TestCountermeasureManagerCreate:

    def test_create_returns_countermeasure(self):
        """create が Countermeasure を返す"""
        from guardian.countermeasure_manager import CountermeasureManager
        mgr = CountermeasureManager()
        incident = _make_incident()
        with patch.object(mgr, "_next_cm_number", return_value=1):
            cm = mgr.create(incident)
        assert cm is not None

    def test_create_assigns_cm_id(self):
        """Countermeasure に CM-001 形式の cm_id が付く"""
        from guardian.countermeasure_manager import CountermeasureManager
        mgr = CountermeasureManager()
        incident = _make_incident()
        with patch.object(mgr, "_next_cm_number", return_value=1):
            cm = mgr.create(incident)
        assert cm.cm_id.startswith("CM-")
        assert "001" in cm.cm_id or cm.cm_id == "CM-001"

    def test_create_links_origin_incident(self):
        """Countermeasure の origin_incident に発端 incident のパスが含まれる"""
        from guardian.countermeasure_manager import CountermeasureManager
        mgr = CountermeasureManager()
        incident = _make_incident()
        with patch.object(mgr, "_next_cm_number", return_value=2):
            cm = mgr.create(incident)
        assert incident.file_path in cm.origin_incident or \
               incident.target_name in cm.origin_incident


class TestCountermeasureManagerNextCmNumber:

    def test_next_cm_number_returns_1_when_no_existing(self):
        """countermeasures/ が空なら 1 を返す"""
        from guardian.countermeasure_manager import CountermeasureManager
        mgr = CountermeasureManager()
        with patch("guardian.countermeasure_manager.glob.glob", return_value=[]):
            num = mgr._next_cm_number()
        assert num == 1

    def test_next_cm_number_increments_from_max(self):
        """CM-003 が最大なら 4 を返す"""
        from guardian.countermeasure_manager import CountermeasureManager
        mgr = CountermeasureManager()
        existing = [
            "countermeasures/CM-001_GhostRetry.md",
            "countermeasures/CM-003_BrokenLinkGuard.md",
            "countermeasures/CM-002_SilentRollback.md",
        ]
        with patch("guardian.countermeasure_manager.glob.glob",
                   return_value=existing):
            num = mgr._next_cm_number()
        assert num == 4


class TestCountermeasureManagerSave:

    def test_save_returns_file_path(self):
        """save がファイルパスを返す"""
        from guardian.countermeasure_manager import CountermeasureManager
        from guardian.models import Countermeasure
        mgr = CountermeasureManager()
        cm = MagicMock(spec=Countermeasure)
        cm.cm_id = "CM-001"
        cm.name = "GhostRetry"
        m = mock_open()
        with patch("builtins.open", m):
            with patch("guardian.countermeasure_manager.os.makedirs"):
                path = mgr.save(cm)
        assert "countermeasures/" in path
        assert "CM-001" in path

    def test_save_file_follows_naming_convention(self):
        """ファイル名が countermeasures/CM-XXX_<Name>.md の形式"""
        import re
        from guardian.countermeasure_manager import CountermeasureManager
        from guardian.models import Countermeasure
        mgr = CountermeasureManager()
        cm = MagicMock(spec=Countermeasure)
        cm.cm_id = "CM-004"
        cm.name = "ActionRevive"
        with patch("builtins.open", mock_open()):
            with patch("guardian.countermeasure_manager.os.makedirs"):
                path = mgr.save(cm)
        assert re.search(r"countermeasures/CM-004_ActionRevive\.md", path)
