import os
import glob
import re
import logging
from datetime import datetime
from guardian.models import DailyReport, CheckStatus, CheckKind, TriggerKind

logger = logging.getLogger(__name__)


class DailyReportGenerator:

    def generate(
        self, results: list, trigger: TriggerKind, autofix_results: list = None
    ) -> DailyReport:
        ok = [r for r in results if r.status == CheckStatus.OK]
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        action_required = warnings + errors

        adsense_anomalies = [
            r for r in results
            if r.check_kind == CheckKind.ADSENSE_PAGES and r.status == CheckStatus.ERROR
        ]

        self_monitor_result = next(
            (r for r in results if r.check_kind == CheckKind.SELF_STATUS), None
        )

        applied = self._build_applied_measures(autofix_results or [])
        logger.info(
            "report generate trigger=%s total=%d ok=%d warning=%d error=%d",
            trigger.value.lower(),
            len(results),
            len(ok),
            len(warnings),
            len(errors),
        )

        return DailyReport(
            executed_at=datetime.now(),
            trigger=trigger,
            total_count=len(results),
            ok_count=len(ok),
            warning_count=len(warnings),
            error_count=len(errors),
            action_required=action_required,
            applied_measures=applied,
            new_countermeasures=[],
            self_monitor_result=self_monitor_result,
            adsense_anomalies=adsense_anomalies,
            summary=self._build_summary(len(ok), len(warnings), len(errors)),
        )

    def _build_applied_measures(self, autofix_results: list) -> list:
        """AutoFixResult リストから日報用の対策実施行を生成する。"""
        if not autofix_results:
            return ["自動修正対象なし"]

        lines = []
        for fix in autofix_results:
            lines.append(f"[AUTO_FIX][{fix.status}] {fix.message}")
        return lines

    def save(self, report: DailyReport) -> str:
        filename = self._resolve_file_name(report.trigger)
        path = f"reports/daily/{filename}"

        os.makedirs("reports/daily", exist_ok=True)
        content = self._render(report)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        report.file_path = path
        logger.info("report written path=%s", path)
        return path

    def _resolve_file_name(self, trigger: TriggerKind) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        if trigger == TriggerKind.SCHEDULED:
            return f"{today}.md"

        # 手動実行: 連番
        existing = glob.glob(f"reports/daily/{today}_manual_*.md")
        if not existing:
            return f"{today}_manual_01.md"
        nums = []
        for path in existing:
            m = re.search(r"_manual_(\d+)\.md$", path)
            if m:
                nums.append(int(m.group(1)))
        next_num = max(nums) + 1 if nums else 1
        return f"{today}_manual_{next_num:02d}.md"

    def _build_summary(self, ok: int, warn: int, err: int) -> str:
        if err == 0 and warn == 0:
            return "全対象正常"
        parts = []
        if err:
            parts.append(f"異常 {err} 件")
        if warn:
            parts.append(f"警告 {warn} 件")
        return "要対応: " + ", ".join(parts)

    def _render(self, report: DailyReport) -> str:
        lines = [
            f"# 日報 {report.executed_at.strftime('%Y-%m-%d')}",
            "",
            f"- 実行日時: {report.executed_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 実行種別: {report.trigger.value}",
            f"- 対象総数: {report.total_count}",
            f"- 正常: {report.ok_count} / 警告: {report.warning_count} / 異常: {report.error_count}",
            "",
            "## 要対応一覧",
        ]
        for r in report.action_required:
            label = r.error_code.value if r.error_code else r.check_kind.value
            lines.append(f"- [{r.status.value}] {r.company_id} / {label}: {r.detail}")

        lines += ["", "## 対策実施", ""]
        if report.applied_measures:
            for m in report.applied_measures:
                lines.append(f"- {m}")
        else:
            lines.append("- 自動修正対象なし")

        lines += ["", "## 新規 countermeasure", ""]
        for cm in report.new_countermeasures:
            lines.append(f"- {cm}")

        lines += ["", "## 自己監視結果"]
        if report.self_monitor_result:
            r = report.self_monitor_result
            lines.append(f"- [{r.status.value}] {r.detail}")
        else:
            lines.append("- 未実施")

        lines += ["", "## AdSense 関連異常", ""]
        for r in report.adsense_anomalies:
            lines.append(f"- {r.company_id}: {r.detail}")

        lines += ["", "## 総括", "", report.summary]
        return "\n".join(lines) + "\n"
