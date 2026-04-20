"""Application module for submissions presentation submissions detail media payloads utils workflows."""

from __future__ import annotations

from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_KIND_RECORDING,
    RECORDING_ASSET_KIND_SUPPLEMENTAL,
)
from app.media.services.media_services_media_keys_service import recording_public_id


def build_recording_payload(recording, *, download_url: str | None):
    """Build recording payload."""
    if recording is None:
        return None
    return {
        "recordingId": recording_public_id(recording.id),
        "assetKind": getattr(recording, "asset_kind", None)
        or RECORDING_ASSET_KIND_RECORDING,
        "contentType": recording.content_type,
        "bytes": recording.bytes,
        "status": recording.status,
        "createdAt": recording.created_at,
        "downloadUrl": download_url,
    }


def build_transcript_payload(transcript, *, transcript_job=None):
    """Build transcript payload."""
    if transcript is None:
        return None
    segments = transcript.segments_json
    job_status = getattr(transcript_job, "status", None)
    job_attempt = getattr(transcript_job, "attempt", None)
    job_max_attempts = getattr(transcript_job, "max_attempts", None)
    return {
        "status": transcript.status,
        "modelName": transcript.model_name,
        "lastError": transcript.last_error,
        "jobStatus": job_status,
        "jobAttempt": job_attempt,
        "jobMaxAttempts": job_max_attempts,
        "retryable": bool(transcript_job is not None and job_status != "succeeded"),
        "text": transcript.text,
        "segmentsJson": segments,
        "segments": segments,
    }


def build_handoff_payload(
    recording,
    *,
    download_url: str | None,
    transcript_payload,
    supplemental_materials=None,
):
    """Build handoff payload."""
    if recording is None and not supplemental_materials:
        return None
    asset_kind = None
    recording_id = None
    if recording is not None:
        recording_id = recording_public_id(recording.id)
        asset_kind = (
            getattr(recording, "asset_kind", None) or RECORDING_ASSET_KIND_RECORDING
        )
    elif supplemental_materials:
        asset_kind = RECORDING_ASSET_KIND_SUPPLEMENTAL
    return {
        "recordingId": recording_id,
        "assetKind": asset_kind,
        "downloadUrl": download_url,
        "transcript": transcript_payload,
        "supplementalMaterials": supplemental_materials or [],
    }


def build_supplemental_materials_payloads(
    supplemental_materials,
    *,
    download_url_resolver=None,
):
    """Build supplemental material payloads."""
    if not supplemental_materials:
        return []
    payloads = []
    for asset in supplemental_materials:
        asset_kind = (
            getattr(asset, "asset_kind", None) or RECORDING_ASSET_KIND_SUPPLEMENTAL
        )
        download_url = None
        if download_url_resolver is not None and getattr(asset, "storage_key", None):
            download_url = download_url_resolver(asset)
        payloads.append(
            {
                "recordingId": recording_public_id(asset.id),
                "assetKind": asset_kind,
                "contentType": asset.content_type,
                "bytes": asset.bytes,
                "status": asset.status,
                "createdAt": asset.created_at,
                "downloadUrl": download_url,
            }
        )
    return payloads
