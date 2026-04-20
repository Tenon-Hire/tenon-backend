"""Application module for tasks routes tasks handoff upload utils workflows."""

from __future__ import annotations

from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_KIND_RECORDING,
    RECORDING_ASSET_KIND_SUPPLEMENTAL,
)
from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_READY,
)
from app.media.services.media_services_media_keys_service import recording_public_id


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


def normalize_handoff_status_result(
    result: object,
) -> tuple[object | None, object | None, object | None]:
    """Normalize handoff status results across legacy and enriched shapes."""
    if not isinstance(result, tuple):
        return None, None, None
    if len(result) >= 3:
        recording, transcript, transcript_job = result[:3]
        return recording, transcript, transcript_job
    if len(result) == 2:
        recording, transcript = result
        return recording, transcript, None
    if len(result) == 1:
        return result[0], None, None
    return None, None, None


def build_transcript_status_payload(
    transcript,
    *,
    transcript_job=None,
) -> dict[str, object]:
    """Build transcript status payload."""
    text = None
    segments = None
    transcript_status = getattr(transcript, "status", None)
    if transcript_status == TRANSCRIPT_STATUS_READY:
        text = getattr(transcript, "text", None)
        segments = serialize_transcript_segments(
            getattr(transcript, "segments_json", None)
        )
    return {
        "status": transcript_status,
        "progress": None,
        "lastError": getattr(transcript, "last_error", None),
        "jobStatus": getattr(transcript_job, "status", None),
        "jobAttempt": getattr(transcript_job, "attempt", None),
        "jobMaxAttempts": getattr(transcript_job, "max_attempts", None),
        "retryable": bool(
            transcript_job is not None
            and getattr(transcript_job, "status", None) != "succeeded"
        ),
        "text": text,
        "segments": segments,
    }


def build_recording_status_payload(
    recording,
    *,
    download_url: str | None,
) -> dict[str, object]:
    """Build handoff recording payload."""
    return {
        "recordingId": recording_public_id(recording.id),
        "assetKind": getattr(recording, "asset_kind", None)
        or RECORDING_ASSET_KIND_RECORDING,
        "status": getattr(recording, "status", None),
        "downloadUrl": download_url,
    }


def build_supplemental_status_payloads(
    supplemental_materials,
    *,
    download_url_resolver,
) -> list[dict[str, object]]:
    """Build supplemental material payloads."""
    payloads: list[dict[str, object]] = []
    for asset in supplemental_materials or []:
        payloads.append(
            {
                "recordingId": recording_public_id(asset.id),
                "assetKind": getattr(asset, "asset_kind", None)
                or RECORDING_ASSET_KIND_SUPPLEMENTAL,
                "status": getattr(asset, "status", None),
                "downloadUrl": download_url_resolver(asset),
            }
        )
    return payloads
