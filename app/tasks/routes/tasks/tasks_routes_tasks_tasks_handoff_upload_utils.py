"""Application module for tasks routes tasks handoff upload utils workflows."""

from __future__ import annotations

from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_READY,
)


def coerce_optional_int(value: object) -> int | None:
    """Execute coerce optional int."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def serialize_transcript_segments(raw_segments: object) -> list[dict[str, object]]:
    """Serialize transcript segments."""
    if not isinstance(raw_segments, list):
        return []
    segments: list[dict[str, object]] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        segment: dict[str, object] = {"text": text}
        segment_id = item.get("id")
        if segment_id is not None:
            segment["id"] = str(segment_id)
        start_ms = coerce_optional_int(item.get("startMs"))
        end_ms = coerce_optional_int(item.get("endMs"))
        if start_ms is not None:
            segment["startMs"] = start_ms
        if end_ms is not None:
            segment["endMs"] = end_ms
        segments.append(segment)
    return segments


def build_transcript_status_payload(transcript) -> dict[str, object]:
    """Build transcript status payload."""
    text = None
    segments = None
    if transcript.status == TRANSCRIPT_STATUS_READY:
        text = transcript.text
        segments = serialize_transcript_segments(transcript.segments_json)
    return {
        "status": transcript.status,
        "progress": None,
        "text": text,
        "segments": segments,
    }
