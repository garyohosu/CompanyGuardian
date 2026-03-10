#!/usr/bin/env python
"""
CompanyGuardian エントリポイント

Usage:
    python scripts/check_targets.py              # 定期実行（SCHEDULED）
    python scripts/check_targets.py --trigger manual  # 手動実行
"""
import argparse
import logging
import sys
import os

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardian.models import TriggerKind
from guardian.runner import CompanyGuardianRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("check_targets")


def main():
    parser = argparse.ArgumentParser(description="CompanyGuardian 巡回スクリプト")
    parser.add_argument(
        "--trigger",
        choices=["scheduled", "manual"],
        default="scheduled",
        help="実行トリガー種別 (デフォルト: scheduled)",
    )
    args = parser.parse_args()

    trigger = TriggerKind.SCHEDULED if args.trigger == "scheduled" else TriggerKind.MANUAL
    logger.info(f"CompanyGuardian 開始 trigger={trigger.value}")

    runner = CompanyGuardianRunner()
    try:
        runner.run(trigger)
        logger.info("CompanyGuardian 完了")
    except Exception as e:
        logger.error(f"CompanyGuardian 実行エラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
