import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(cid: str | None) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        cid = _correlation_id.get()
        if cid:
            payload["correlation_id"] = cid
        if record.exc_info and record.exc_info[1]:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            payload.update(record.extra_data)
        return json.dumps(payload, default=str)


class DevFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        color = self.COLORS.get(record.levelname, "")
        cid = _correlation_id.get()
        cid_str = f" [{cid[:8]}]" if cid else ""
        msg = f"{ts} {color}{record.levelname:<8}{self.RESET} {record.name}{cid_str}: {record.getMessage()}"
        if record.exc_info and record.exc_info[1]:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


_setup_done = False


def setup_logging(
    level: str | None = None,
    environment: str | None = None,
    json_output: bool | None = None,
) -> None:
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    try:
        from src.core.config import get_settings
        settings = get_settings()
        level = level or settings.log_level or "INFO"
        environment = environment or settings.environment or "development"
    except Exception:
        level = level or "INFO"
        environment = environment or "development"

    if json_output is None:
        json_output = environment == "production"

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if root.handlers:
        root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if json_output else DevFormatter())
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not _setup_done:
        setup_logging()
    return logger
