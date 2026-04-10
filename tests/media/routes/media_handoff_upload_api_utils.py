from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

import app.submissions.routes.submissions_routes.submissions_routes_submissions_routes_submissions_routes_detail_media_routes as submissions_detail_route
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    serialize_day_windows,
)
from app.config import settings
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    StorageMediaError,
    get_storage_media_provider,
)
from app.media.repositories.recordings import (
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_UPLOADING,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import (
    TRANSCRIPT_STATUS_PENDING,
    TRANSCRIPT_STATUS_READY,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.media.services.media_services_media_transcription_jobs_service import (
    TRANSCRIBE_RECORDING_JOB_TYPE,
    transcribe_recording_idempotency_key,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Job,
    RecordingAsset,
    Submission,
    Transcript,
)
from app.shared.utils.shared_utils_errors_utils import (
    MEDIA_STORAGE_UNAVAILABLE,
    REQUEST_TOO_LARGE,
)
from tests.shared.factories import (
    create_candidate_session,
    create_company,
    create_submission,
    create_talent_partner,
    create_trial,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def _fake_storage_provider() -> FakeStorageMediaProvider:
    provider = get_storage_media_provider()
    assert isinstance(provider, FakeStorageMediaProvider)
    return provider


CONSENT_KWARGS = {"consent_version": "mvp1", "ai_notice_version": "mvp1"}


def _set_closed_windows(candidate_session) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    window_start = now - timedelta(days=2)
    window_end = now - timedelta(days=1)
    candidate_session.scheduled_start_at = window_start
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(
        [
            {
                "dayIndex": day_index,
                "windowStartAt": window_start,
                "windowEndAt": window_end,
            }
            for day_index in range(1, 6)
        ]
    )


__all__ = [name for name in globals() if not name.startswith("__")]
