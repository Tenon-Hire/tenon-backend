from __future__ import annotations

from functools import lru_cache

from app.integrations.transcription.base import TranscriptionProvider
from app.integrations.transcription.fake_provider import FakeTranscriptionProvider


@lru_cache
def get_transcription_provider() -> TranscriptionProvider:
    """Return the configured transcription provider implementation."""
    return FakeTranscriptionProvider()


__all__ = ["get_transcription_provider"]
