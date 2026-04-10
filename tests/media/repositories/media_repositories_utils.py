from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime, timedelta

from app.media.repositories.recordings import (
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_PURGED,
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_UPLOADING,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import (
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_PENDING,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.submissions.repositories import repository as submissions_repo
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


__all__ = [name for name in globals() if not name.startswith("__")]
