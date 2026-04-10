"""Schemas for Talent Partner-facing company AI configuration."""

from __future__ import annotations

from app.ai import PromptOverrideSet
from app.shared.types.shared_types_base_model import APIModel


class CompanyAIConfigRead(APIModel):
    """Serialized Talent Partner company AI config."""

    companyId: int
    companyName: str
    promptPackVersion: str
    promptOverrides: PromptOverrideSet | None = None


class CompanyAIConfigWrite(APIModel):
    """Write payload for Talent Partner company AI config."""

    promptOverrides: PromptOverrideSet | None = None


__all__ = ["CompanyAIConfigRead", "CompanyAIConfigWrite"]
