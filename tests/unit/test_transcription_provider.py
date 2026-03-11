from __future__ import annotations

import pytest

from app.integrations.transcription import (
    FakeTranscriptionProvider,
    TranscriptionProviderError,
)


def test_fake_transcription_provider_requires_source_url():
    provider = FakeTranscriptionProvider()
    with pytest.raises(TranscriptionProviderError, match="source_url is required"):
        provider.transcribe_recording(source_url="", content_type="video/mp4")


def test_fake_transcription_provider_requires_storage_key_query_param():
    provider = FakeTranscriptionProvider()
    with pytest.raises(TranscriptionProviderError, match="missing storage key"):
        provider.transcribe_recording(
            source_url="https://fake.example/download?expires=123",
            content_type="video/mp4",
        )


def test_fake_transcription_provider_returns_deterministic_payload():
    provider = FakeTranscriptionProvider(model_name="model-x")
    result = provider.transcribe_recording(
        source_url=(
            "https://fake.example/download?"
            "key=candidate-sessions/1/tasks/2/recordings/demo.mp4"
        ),
        content_type="video/mp4; charset=utf-8",
    )
    assert result.model_name == "model-x"
    assert "demo.mp4" in result.text
    assert result.segments[0]["startMs"] == 0
