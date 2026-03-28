"""Application module for integrations transcription factory client workflows."""

from __future__ import annotations

from functools import lru_cache

from app.integrations.transcription.integrations_transcription_base_client import (
    TranscriptionProvider,
)
from app.integrations.transcription.integrations_transcription_fake_provider_client import (
    FakeTranscriptionProvider,
)


@lru_cache
def get_transcription_provider() -> TranscriptionProvider:
    """Return the configured transcription provider implementation."""
    return FakeTranscriptionProvider()


__all__ = ["get_transcription_provider"]
