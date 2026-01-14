from __future__ import annotations

import logging
import re
from typing import Any

_SENSITIVE_KEYS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "secret",
    "password",
    "set-cookie",
    "cookie",
}

_REDACT_PATTERNS = [
    (re.compile(r"(?i)bearer\s+\S+"), "Bearer [redacted]"),
    (re.compile(r"(?i)(api[-_]?key|token|secret)[:=]\s*[^\s]+"), r"\1=[redacted]"),
]


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(s in lowered for s in _SENSITIVE_KEYS)


def _redact_string(value: str) -> str:
    redacted = value
    for pattern, repl in _REDACT_PATTERNS:
        redacted = pattern.sub(repl, redacted)
    return redacted


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _redact_mapping(value)
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(v) for v in value)
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _redact_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in mapping.items():
        if _is_sensitive_key(key):
            redacted[key] = "[redacted]"
        else:
            redacted[key] = _redact_value(value)
    return redacted


class RedactionFilter(logging.Filter):
    """Redact sensitive tokens/headers from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Scrub sensitive values from the log record."""
        if isinstance(record.args, dict):
            record.args = _redact_mapping(record.args)
        elif isinstance(record.args, tuple):
            record.args = _redact_value(record.args)
        if isinstance(record.msg, str) and not record.args:
            record.msg = _redact_string(record.msg)

        for key, value in list(record.__dict__.items()):
            if key in {"args", "msg"}:
                continue
            if _is_sensitive_key(key):
                record.__dict__[key] = "[redacted]"
            else:
                record.__dict__[key] = _redact_value(value)
        return True


_REDACTOR = RedactionFilter()


def _attach_filter_to_handlers() -> None:
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(f, RedactionFilter) for f in handler.filters):
            handler.addFilter(_REDACTOR)


def configure_logging() -> None:
    """Attach redaction filter to all log records once."""
    _attach_filter_to_handlers()
    if getattr(configure_logging, "_configured", False):
        return
    original_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = original_factory(*args, **kwargs)
        _REDACTOR.filter(record)
        return record

    logging.setLogRecordFactory(record_factory)

    original_add_handler = logging.Logger.addHandler

    def add_handler(self, hdlr, *, _orig=original_add_handler):
        if not any(isinstance(f, RedactionFilter) for f in hdlr.filters):
            hdlr.addFilter(_REDACTOR)
        return _orig(self, hdlr)

    logging.Logger.addHandler = add_handler
    configure_logging._configured = True
