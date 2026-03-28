"""Application module for candidates candidate sessions services candidates candidate sessions schedule gates model workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TaskWindow:
    """Window evaluation for a task day at a specific timestamp."""

    window_start_at: datetime | None
    window_end_at: datetime | None
    next_open_at: datetime | None
    is_open: bool
    now: datetime


__all__ = ["TaskWindow"]
