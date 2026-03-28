"""Application module for recruiters routes admin templates recruiters admin templates schemas routes workflows."""

from __future__ import annotations

from typing import Literal

from app.shared.types.shared_types_base_model import APIModel


class TemplateHealthRunRequest(APIModel):
    """Request payload for live template health checks."""

    templateKeys: list[str]
    mode: Literal["live", "static"] = "live"
    timeoutSeconds: int = 180
    concurrency: int = 2
