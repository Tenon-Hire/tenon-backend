from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.integrations.transcription import (
    FakeTranscriptionProvider,
    OpenAITranscriptionProvider,
    TranscriptionProviderError,
)
from app.integrations.transcription import (
    integrations_transcription_factory_client as transcription_factory,
)
from app.integrations.transcription import (
    integrations_transcription_openai_provider_client as openai_provider_module,
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


def test_transcription_factory_returns_openai_provider_in_real_mode(monkeypatch):
    transcription_factory.get_transcription_provider.cache_clear()
    monkeypatch.setattr(
        transcription_factory,
        "resolve_transcription_config",
        lambda: SimpleNamespace(runtime_mode="real", provider="openai"),
    )
    provider = transcription_factory.get_transcription_provider()
    assert isinstance(provider, OpenAITranscriptionProvider)
    transcription_factory.get_transcription_provider.cache_clear()


def test_openai_transcription_provider_normalizes_segments(monkeypatch):
    class _FakeDownloadResponse:
        headers = {"Content-Type": "audio/mpeg"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"fake-audio"

        def geturl(self):
            return "https://fake.example/files/demo.mp3"

    class _FakeTranscriptions:
        @staticmethod
        def create(**_kwargs):
            return SimpleNamespace(
                model_dump=lambda: {
                    "text": "Shipped the fix and validated the handoff.",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 1.25,
                            "text": "Shipped the fix and validated the handoff.",
                        }
                    ],
                }
            )

    class _FakeOpenAI:
        def __init__(self, **_kwargs):
            self.audio = SimpleNamespace(transcriptions=_FakeTranscriptions())

    monkeypatch.setattr(
        openai_provider_module,
        "resolve_transcription_config",
        lambda: SimpleNamespace(
            model="gpt-4o-transcribe",
            timeout_seconds=15,
            max_retries=1,
        ),
    )
    monkeypatch.setattr(openai_provider_module.settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai_provider_module, "urlopen", lambda *_args, **_kwargs: _FakeDownloadResponse())
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))

    provider = OpenAITranscriptionProvider()
    result = provider.transcribe_recording(
        source_url="https://fake.example/download?key=recordings/demo.mp3",
        content_type="audio/mpeg",
    )

    assert result.model_name == "gpt-4o-transcribe"
    assert result.text == "Shipped the fix and validated the handoff."
    assert result.segments == [
        {
            "startMs": 0,
            "endMs": 1250,
            "text": "Shipped the fix and validated the handoff.",
        }
    ]
