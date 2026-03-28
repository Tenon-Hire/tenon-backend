"""Application module for integrations transcription base client workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TranscriptionProviderError(RuntimeError):
    """Raised when transcription provider execution fails."""


@dataclass(frozen=True)
class TranscriptionResult:
    """Normalized transcript output from a provider."""

    text: str
    segments: list[dict[str, object]]
    model_name: str | None = None


class TranscriptionProvider(Protocol):
    """Provider contract for converting a recording into transcript text."""

    def transcribe_recording(
        self,
        *,
        source_url: str,
        content_type: str,
    ) -> TranscriptionResult:
        """Execute transcribe recording."""
        ...


__all__ = [
    "TranscriptionProvider",
    "TranscriptionProviderError",
    "TranscriptionResult",
]
