from __future__ import annotations

from app.integrations.transcription import TranscriptionResult
from app.media.repositories.recordings import (
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_READY,
    RECORDING_ASSET_STATUS_UPLOADED,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import (
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_PENDING,
    TRANSCRIPT_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_READY,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.shared.jobs.handlers import transcribe_recording as handler
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


__all__ = [name for name in globals() if not name.startswith("__")]
