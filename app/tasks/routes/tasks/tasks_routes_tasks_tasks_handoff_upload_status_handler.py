"""Application module for tasks routes tasks handoff upload status handler workflows."""

from __future__ import annotations

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.media.services.media_services_media_transcription_jobs_service import (
    load_transcribe_recording_job,
)
from app.shared.database.shared_database_models_model import Trial
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    HandoffStatusResponse,
)


async def handoff_status_route_impl(
    *,
    task_id: int,
    candidate_session,
    db,
    storage_provider,
    recording,
    transcript,
    transcript_job,
    supplemental_materials,
    is_downloadable_fn,
    resolve_signed_url_ttl_fn,
    build_transcript_status_payload_fn,
    build_recording_status_payload_fn,
    build_supplemental_status_payloads_fn,
    logger,
) -> HandoffStatusResponse:
    """Execute handoff status route impl."""
    if transcript_job is None and recording is not None:
        company_id = getattr(
            getattr(candidate_session, "trial", None), "company_id", None
        )
        if not isinstance(company_id, int) and isinstance(
            getattr(candidate_session, "trial_id", None), int
        ):
            trial = await db.get(Trial, candidate_session.trial_id)
            company_id = getattr(trial, "company_id", None)
        if isinstance(company_id, int):
            transcript_job = await load_transcribe_recording_job(
                db, company_id=company_id, recording_id=recording.id
            )
    recording_payload = None
    if recording is not None:
        download_url = None
        if is_downloadable_fn(recording):
            try:
                download_url = storage_provider.create_signed_download_url(
                    recording.storage_key,
                    expires_seconds=resolve_signed_url_ttl_fn(),
                )
            except (StorageMediaError, ValueError) as exc:
                logger.warning(
                    "Failed to sign candidate handoff status download URL recordingId=%s taskId=%s candidateSessionId=%s",
                    recording.id,
                    task_id,
                    candidate_session.id,
                    exc_info=exc,
                )
        recording_payload = build_recording_status_payload_fn(
            recording, download_url=download_url
        )
    transcript_payload = None
    if transcript is not None:
        transcript_payload = build_transcript_status_payload_fn(
            transcript, transcript_job=transcript_job
        )
    supplemental_payloads = build_supplemental_status_payloads_fn(
        supplemental_materials,
        download_url_resolver=lambda asset: (
            None
            if not is_downloadable_fn(asset)
            else _resolve_download_url(
                storage_provider, asset, resolve_signed_url_ttl_fn
            )
        ),
    )
    return HandoffStatusResponse(
        recording=recording_payload,
        supplementalMaterials=supplemental_payloads,
        transcript=transcript_payload,
    )


def _resolve_download_url(storage_provider, recording, resolve_signed_url_ttl_fn):
    try:
        return storage_provider.create_signed_download_url(
            recording.storage_key,
            expires_seconds=resolve_signed_url_ttl_fn(),
        )
    except (StorageMediaError, ValueError):
        return None
