from __future__ import annotations

import json
import logging

from aivillage.diagnostics import configure_logging


def test_configured_log_file_contains_structured_exception(tmp_path):
    log_path = configure_logging(tmp_path)
    logger = logging.getLogger("aivillage.test")

    try:
        raise RuntimeError("device unavailable")
    except RuntimeError:
        logger.exception("voice shutdown failed", extra={"event": "service_stop_failed",
                                                         "service": "voice"})

    for handler in logging.getLogger("aivillage").handlers:
        handler.flush()
    record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert record["level"] == "ERROR"
    assert record["event"] == "service_stop_failed"
    assert record["service"] == "voice"
    assert record["message"] == "voice shutdown failed"
    assert "RuntimeError: device unavailable" in record["exception"]
