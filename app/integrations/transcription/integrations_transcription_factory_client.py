"""Application module for integrations transcription factory client workflows."""

from __future__ import annotations

from functools import lru_cache

from app.ai import allow_demo_or_test_mode, resolve_transcription_config
from app.integrations.transcription.integrations_transcription_base_client import (
    TranscriptionProvider,
)
from app.integrations.transcription.integrations_transcription_fake_provider_client import (
    FakeTranscriptionProvider,
)
from app.integrations.transcription.integrations_transcription_openai_provider_client import (
    OpenAITranscriptionProvider,
)


@lru_cache
def get_transcription_provider() -> TranscriptionProvider:
    """Return the configured transcription provider implementation."""
    config = resolve_transcription_config()
    if allow_demo_or_test_mode(config.runtime_mode):
        return FakeTranscriptionProvider()
    if config.provider == "openai":
        return OpenAITranscriptionProvider()
    raise ValueError(f"Unsupported transcription provider: {config.provider}")


__all__ = ["get_transcription_provider"]
