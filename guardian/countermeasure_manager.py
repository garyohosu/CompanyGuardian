import os
import re
import glob
from guardian.models import Countermeasure, Incident


class CountermeasureManager:

    def should_create(self, incident: Incident) -> bool:
        existing = glob.glob("countermeasures/CM-*.md")
        if not existing:
            return True

        # 同種の error_code が既存 CM に含まれるか確認
        incident_codes = {ec.value for ec in incident.error_codes}
        for cm_path in existing:
            try:
                with open(cm_path, "r", encoding="utf-8") as f:
                    content = f.read()
                for code in incident_codes:
                    if code in content:
                        return False
            except Exception:
                pass
        return True

    def create(self, incident: Incident) -> Countermeasure:
        num = self._next_cm_number()
        cm_id = f"CM-{num:03d}"
        name = self._derive_name(incident)
        origin = incident.file_path or incident.target_name
        return Countermeasure(
            cm_id=cm_id,
            name=name,
            origin_incident=origin,
            condition=f"{incident.target_name} にて {', '.join(ec.value for ec in incident.error_codes)} 発生時",
            steps="1. 原因を確認する\n2. 対策を実施する\n3. 結果を記録する",
            verification="異常が解消されたことを確認",
            effect="再発防止",
            notes="",
        )

    def save(self, cm: Countermeasure) -> str:
        filename = f"{cm.cm_id}_{cm.name}.md"
        path = f"countermeasures/{filename}"

        os.makedirs("countermeasures", exist_ok=True)
        content = self._render(cm)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        cm.file_path = path
        return path

    def _next_cm_number(self) -> int:
        existing = glob.glob("countermeasures/CM-*.md")
        if not existing:
            return 1
        nums = []
        for path in existing:
            m = re.search(r"CM-(\d+)", os.path.basename(path))
            if m:
                nums.append(int(m.group(1)))
        return max(nums) + 1 if nums else 1

    def _derive_name(self, incident: Incident) -> str:
        if not incident.error_codes:
            return "UnknownIssue"
        code = incident.error_codes[0].value
        mapping = {
            "SITE_DOWN": "SiteDownGuard",
            "ACTION_FAILED": "ActionRevive",
            "ARTIFACT_MISSING": "ArtifactGuard",
            "DAILY_POST_MISSING": "DailyPostGuard",
            "ADSENSE_PAGE_MISSING": "AdSensePageGuard",
            "KEYWORD_MISSING": "KeywordGuard",
            "LINK_BROKEN": "BrokenLinkGuard",
        }
        return mapping.get(code, "IncidentGuard")

    def _render(self, cm: Countermeasure) -> str:
        return f"""# {cm.cm_id}: {cm.name}

- 対策ID: {cm.cm_id}
- 対策名: {cm.name}
- 発端: {cm.origin_incident}

## 適用条件
{cm.condition}

## 手順
{cm.steps}

## 確認方法
{cm.verification}

## 効果
{cm.effect}

## 注意点
{cm.notes}
"""
