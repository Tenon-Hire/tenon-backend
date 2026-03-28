"""Application module for jobs handlers scenario generation parse handler workflows."""

from __future__ import annotations

from typing import Any

from app.shared.utils.shared_utils_parsing_utils import (
    parse_positive_int as _parse_positive_int_value,
)


def _parse_positive_int(value: Any) -> int | None:
    return _parse_positive_int_value(value)


__all__ = ["_parse_positive_int"]
