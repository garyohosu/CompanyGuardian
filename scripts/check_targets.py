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
from guardian.logging_utils import setup_logging, get_log_path
from guardian.runner import CompanyGuardianRunner

logger = logging.getLogger("check_targets")


def main():
    setup_logging(force=True)
    parser = argparse.ArgumentParser(description="CompanyGuardian 巡回スクリプト")
    parser.add_argument(
        "--trigger",
        choices=["scheduled", "manual"],
        default="scheduled",
        help="実行トリガー種別 (デフォルト: scheduled)",
    )
    args = parser.parse_args()

    trigger = TriggerKind.SCHEDULED if args.trigger == "scheduled" else TriggerKind.MANUAL
    logger.info(
        f"CompanyGuardian bootstrap trigger={trigger.value.lower()} log_path={get_log_path()}"
    )

    runner = CompanyGuardianRunner()
    try:
        runner.run(trigger)
        logger.info("CompanyGuardian command completed")
    except Exception as e:
        logger.error(f"CompanyGuardian fatal error message=\"{e}\"", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
