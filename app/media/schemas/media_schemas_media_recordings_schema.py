"""Application module for media schemas media recordings schema workflows."""

from __future__ import annotations

from typing import Literal

from app.shared.types.shared_types_base_model import APIModel


class RecordingDeleteResponse(APIModel):
    """Response payload for recording deletion."""

    status: Literal["deleted"]
