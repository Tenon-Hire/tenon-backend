from __future__ import annotations

from typing import Literal

from app.domains.common.base import APIModel


class RecordingDeleteResponse(APIModel):
    """Response payload for recording deletion."""

    status: Literal["deleted"]
