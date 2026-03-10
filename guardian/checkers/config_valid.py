import os
import logging
from datetime import datetime
from guardian.models import CheckResult, CheckStatus, CheckKind, ErrorCode
from guardian.config_loader import ConfigLoader

_CONFIG_PATH = "companies/companies.yaml"
logger = logging.getLogger(__name__)


class ConfigValidChecker:

    def check(self, company) -> CheckResult:
        company_id = company["id"]
        logger.debug("target=%s checker=config_valid path=%s", company_id, _CONFIG_PATH)

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
            logger.debug("target=%s checker=config_valid parse_error=\"%s\"", company_id, e)
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.CONFIG_VALID,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.CONFIG_INVALID,
                detail=f"YAML 解析エラー: {e}",
                checked_at=datetime.now(),
            )

        validation_errors = loader.validate_with_errors(companies)
        if validation_errors:
            logger.debug("target=%s checker=config_valid errors=%s", company_id, "; ".join(validation_errors[:3]))
            detail = "設定内容が不正: " + "; ".join(validation_errors[:3])
            if len(validation_errors) > 3:
                detail += f" 他 {len(validation_errors) - 3} 件"
            return CheckResult(
                company_id=company_id,
                check_kind=CheckKind.CONFIG_VALID,
                status=CheckStatus.ERROR,
                error_code=ErrorCode.CONFIG_INVALID,
                detail=detail,
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
