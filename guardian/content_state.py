import json
import logging
import os
from datetime import date, datetime

from guardian.models import ContentEntry

logger = logging.getLogger(__name__)


class ContentStateStore:
    """content 監視用の最小状態を JSON で保持する。"""

    def __init__(self, path: str = "state/content_monitoring_state.json"):
        self.path = path

    def load(self) -> dict:
        if not os.path.exists(self.path):
            logger.debug("state load path=%s exists=no", self.path)
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = data if isinstance(data, dict) else {}
            logger.debug("state load path=%s exists=yes targets=%d", self.path, len(result))
            return result
        except Exception as e:
            logger.error("state load failed path=%s message=\"%s\"", self.path, e, exc_info=True)
            return {}

    def save(self, state: dict) -> str:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        logger.info("state written path=%s targets=%d", self.path, len(state))
        return self.path

    def get_target_state(self, target_id: str) -> dict:
        state = dict(self.load().get(target_id, {}) or {})
        logger.debug("state target=%s found=%s", target_id, "yes" if state else "no")
        return state

    def update_target(
        self,
        target_id: str,
        latest_entry: ContentEntry | None,
        checked_at: datetime,
    ) -> str:
        state = self.load()
        previous = dict(state.get(target_id, {}) or {})
        record = {
            "target_id": target_id,
            "last_seen_latest_date": self._date_to_str(
                latest_entry.published_on if latest_entry else None
            ),
            "last_seen_latest_url": latest_entry.url if latest_entry else "",
            "last_seen_title": latest_entry.title if latest_entry else "",
            "last_seen_content_hash": latest_entry.content_hash if latest_entry else "",
            "last_seen_progress_value": latest_entry.progress_value if latest_entry else None,
            "last_checked_at": checked_at.isoformat(),
            "last_progress_changed_at": previous.get("last_progress_changed_at"),
        }

        if latest_entry and latest_entry.progress_value is not None:
            prev_progress = previous.get("last_seen_progress_value")
            if prev_progress != latest_entry.progress_value or not record["last_progress_changed_at"]:
                record["last_progress_changed_at"] = checked_at.isoformat()

        state[target_id] = record
        logger.debug(
            "state update target=%s latest_date=%s progress=%s",
            target_id,
            record["last_seen_latest_date"],
            record["last_seen_progress_value"],
        )
        return self.save(state)

    def _date_to_str(self, value: date | None) -> str:
        if value is None:
            return ""
        return value.isoformat()
