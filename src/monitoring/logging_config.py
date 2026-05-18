"""
src/monitoring/logging_config.py
---------------------------------
Structured JSON logging for the healthcare RAG system.

PHI POLICY: Query text is NEVER included in log records.
Log only: query_id, stage, timings, confidence scores, doc_ids, error types.

Usage:
    from monitoring.logging_config import configure_json_logging
    configure_json_logging()   # call once at app startup
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

# Standard LogRecord attributes that should not be emitted as extra JSON fields
_STDLIB_ATTRS: frozenset[str] = frozenset({
    "name", "msg", "args", "created", "filename", "funcName", "levelname",
    "levelno", "lineno", "module", "msecs", "message", "pathname", "process",
    "processName", "relativeCreated", "stack_info", "thread", "threadName",
    "exc_info", "exc_text", "taskName",
})


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        log_obj: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.message,
        }
        # Merge extra fields set by the caller (query_id, stage, latency_ms, etc.)
        for key, val in record.__dict__.items():
            if key not in _STDLIB_ATTRS and not key.startswith("_"):
                log_obj[key] = val

        if record.exc_info:
            log_obj["exc"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def configure_json_logging(level: int = logging.INFO) -> None:
    """
    Switch the root logger to JSON output.
    Safe to call multiple times — idempotent.
    """
    formatter = JsonFormatter()
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setFormatter(formatter)
