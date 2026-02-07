"""Structured JSON logging configuration."""

import logging
import sys
from typing import Any

import json


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "session_id"):
            log_obj["sessionId"] = record.session_id

        if hasattr(record, "request_id"):
            log_obj["requestId"] = record.request_id

        return json.dumps(log_obj)


def setup_logging(debug: bool = False) -> None:
    """Configure structured JSON logging."""
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    logging.root.handlers = [handler]
    logging.root.setLevel(level)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
