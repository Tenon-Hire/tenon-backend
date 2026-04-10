"""Application module for trials services trials candidates compare model workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TrialCompareAccessContext:
    """Represent trial compare access context data and behavior."""

    trial_id: int


__all__ = ["TrialCompareAccessContext"]
