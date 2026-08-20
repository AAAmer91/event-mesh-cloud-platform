"""Structured JSON Logger for CloudWatch / Observability."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def __init__(self, service_name: str = "event-mesh-platform"):
        super().__init__()
        self.service_name = service_name
        self.environment = os.getenv("ENVIRONMENT", "local")

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", self.service_name),
            "environment": self.environment,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Include trace correlation IDs if present
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "order_id"):
            log_data["order_id"] = record.order_id

        # Include custom extra metadata
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data.update(record.extra_data)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(service_name: str = "event-mesh-platform") -> logging.Logger:
    """Returns a configured structured JSON logger."""
    logger = logging.getLogger(service_name)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter(service_name=service_name))
        logger.addHandler(handler)
        logger.propagate = False

    return logger
