"""Application module for jobs handlers transcribe recording handler workflows."""

from __future__ import annotations

import logging
from typing import Any

from app.integrations.storage_media import (
    get_storage_media_provider,
    resolve_signed_url_ttl,
)
from app.integrations.transcription import (
    TranscriptionProviderError,
    get_transcription_provider,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.services.media_services_media_transcription_jobs_service import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
)
from app.shared.database import async_session_maker
from app.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_helpers_handler import (
    _normalize_segments,
    _sanitize_error,
)
from app.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_runtime_handler import (
    handle_transcribe_recording_impl,
)
from app.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_state_handler import (
    _mark_failure as _mark_failure_impl,
)
from app.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_state_handler import (
    _mark_processing as _mark_processing_impl,
)
from app.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_state_handler import (
    _mark_ready as _mark_ready_impl,
)
from app.shared.utils.shared_utils_parsing_utils import (
    parse_positive_int as _parse_positive_int_value,
)

logger = logging.getLogger(__name__)


def _parse_positive_int(value: Any) -> int | None:
    return _parse_positive_int_value(value)


async def _mark_processing(recording_id: int):
    return await _mark_processing_impl(
        recording_id, async_session_maker=async_session_maker
    )


async def _mark_failure(recording_id: int, *, reason: str):
    return await _mark_failure_impl(
        recording_id, reason=reason, async_session_maker=async_session_maker
    )


async def _mark_ready(
    recording_id: int, *, text: str, segments, model_name: str | None
):
    return await _mark_ready_impl(
        recording_id,
        text=text,
        segments=segments,
        model_name=model_name,
        async_session_maker=async_session_maker,
    )


async def handle_transcribe_recording(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Handle transcribe recording."""
    return await handle_transcribe_recording_impl(
        payload_json,
        parse_positive_int=_parse_positive_int,
        normalize_segments=_normalize_segments,
        sanitize_error=_sanitize_error,
        mark_processing=_mark_processing,
        mark_ready=_mark_ready,
        mark_failure=_mark_failure,
        async_session_maker=async_session_maker,
        recordings_repo=recordings_repo,
        get_storage_media_provider=get_storage_media_provider,
        resolve_signed_url_ttl=resolve_signed_url_ttl,
        get_transcription_provider=get_transcription_provider,
        transcription_provider_error=TranscriptionProviderError,
        logger=logger,
    )


__all__ = ["TRANSCRIBE_RECORDING_JOB_TYPE", "handle_transcribe_recording"]
