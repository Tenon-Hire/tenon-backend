"""Application module for candidates schemas candidates candidate sessions windows schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.shared.types.shared_types_base_model import APIModel


class CandidateTrialSummary(APIModel):
    """Summary of the trial for candidate session response."""

    id: int
    title: str
    role: str


class DayWindow(APIModel):
    """Daily availability window in UTC."""

    dayIndex: int
    windowStartAt: datetime
    windowEndAt: datetime


class CurrentDayWindow(DayWindow):
    """Derived current or nearest day window state."""

    state: Literal["upcoming", "active", "closed"]
