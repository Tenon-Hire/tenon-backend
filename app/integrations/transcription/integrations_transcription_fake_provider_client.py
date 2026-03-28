"""Application module for integrations transcription fake provider client workflows."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app.integrations.transcription.integrations_transcription_base_client import (
    TranscriptionProvider,
    TranscriptionProviderError,
    TranscriptionResult,
)


class FakeTranscriptionProvider(TranscriptionProvider):
    """Deterministic transcription provider for local and test usage."""

    def __init__(self, *, model_name: str = "fake-stt-v1") -> None:
        self._model_name = model_name

    def transcribe_recording(
        self,
        *,
        source_url: str,
        content_type: str,
    ) -> TranscriptionResult:
        """Execute transcribe recording."""
        if not source_url:
            raise TranscriptionProviderError("source_url is required")
        parsed = urlparse(source_url)
        query = parse_qs(parsed.query)
        key = ((query.get("key") or [""])[0] or "").strip()
        if not key:
            raise TranscriptionProviderError("missing storage key")

        filename = key.rsplit("/", 1)[-1]
        normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
        text = f"Auto transcript for {filename} ({normalized_type})"
        segments = [
            {
                "startMs": 0,
                "endMs": 1500,
                "text": text,
            }
        ]
        return TranscriptionResult(
            text=text,
            segments=segments,
            model_name=self._model_name,
        )


__all__ = ["FakeTranscriptionProvider"]
