"""Application module for types progress model workflows."""

from __future__ import annotations

from app.shared.types.shared_types_base_model import APIModel


class ProgressSummary(APIModel):
    """Shared progress summary schema."""

    completed: int
    total: int
