import logging
import os
import sys

DEFAULT_LOG_PATH = "logs/company_guardian.log"


class ImmediateFlushStreamHandler(logging.StreamHandler):
    def emit(self, record):
        if self.stream is not sys.stdout or getattr(self.stream, "closed", False):
            self.stream = sys.stdout
        try:
            super().emit(record)
        except ValueError:
            self.stream = sys.stdout
            super().emit(record)


def setup_logging(
    level: int | None = None,
    log_path: str = DEFAULT_LOG_PATH,
    force: bool = False,
) -> str:
    root = logging.getLogger()
    resolved_level = level if level is not None else _resolve_log_level()

    if getattr(root, "_company_guardian_configured", False) and not force:
        root.setLevel(resolved_level)
        for handler in root.handlers:
            if isinstance(handler, ImmediateFlushStreamHandler):
                handler.setLevel(resolved_level)
                handler.stream = sys.stdout
        return getattr(root, "_company_guardian_log_path", log_path)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass

    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    if force:
        for handler in list(root.handlers):
            root.removeHandler(handler)

    console_handler = ImmediateFlushStreamHandler(sys.stdout)
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setLevel(resolved_level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root.setLevel(resolved_level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root._company_guardian_configured = True
    root._company_guardian_log_path = log_path
    logging.captureWarnings(True)
    return log_path


def get_log_path() -> str:
    root = logging.getLogger()
    return getattr(root, "_company_guardian_log_path", DEFAULT_LOG_PATH)


def _resolve_log_level() -> int:
    raw = os.environ.get("COMPANY_GUARDIAN_LOG_LEVEL") or os.environ.get("LOG_LEVEL") or "INFO"
    value = str(raw).upper()
    return getattr(logging, value, logging.INFO)
