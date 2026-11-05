"""Application diagnostics and persistent structured logging."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """Render one machine-readable JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for name in ("event", "service", "provider", "job_kind"):
            value = getattr(record, name, None)
            if value not in (None, ""):
                payload[name] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_dir: Path) -> Path:
    """Configure the ``aivillage`` logger and return its active log path."""
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "aivillage.log"
    logger = logging.getLogger("aivillage")
    logger.setLevel(logging.INFO)
    for handler in list(logger.handlers):
        if getattr(handler, "_aivillage_handler", False):
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3,
                                  encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    handler._aivillage_handler = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.propagate = True
    return path
