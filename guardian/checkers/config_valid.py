import os
from datetime import datetime
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
from guardian.config_loader import ConfigLoader

_CONFIG_PATH = "companies/companies.yaml"


class ConfigValidChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]

        if not os.path.exists(_CONFIG_PATH):
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.CONFIG_VALID,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.CONFIG_INVALID,
                detail=f"設定ファイルが存在しない: {_CONFIG_PATH}",
                checked_at=datetime.now(),
            )

        try:
            loader = ConfigLoader()
            companies = loader.load(_CONFIG_PATH)
        except Exception as e:
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.CONFIG_VALID,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.CONFIG_INVALID,
                detail=f"YAML 解析エラー: {e}",
                checked_at=datetime.now(),
            )

        if not loader.validate(companies):
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.CONFIG_VALID,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.CONFIG_INVALID,
                detail="設定内容が不正",
                checked_at=datetime.now(),
            )

        return CheckResult(
            company_id=company_id,
            check_kind=CheckKind.CONFIG_VALID,
            status=CheckStatus.OK,
            error_code=None,
            detail="設定ファイル正常",
            checked_at=datetime.now(),
        )
