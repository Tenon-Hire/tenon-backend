from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import HTTPException

from app.config import settings
from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    StorageMediaError,
)
from app.media.repositories.recordings import (
    RECORDING_ASSET_STATUS_PURGED,
    RECORDING_ASSET_STATUS_UPLOADED,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import (
    TRANSCRIPT_STATUS_READY,
)
from app.media.repositories.transcripts import repository as transcripts_repo
from app.media.services.media_services_media_privacy_service import (
    delete_recording_asset,
    purge_expired_media_assets,
    record_candidate_session_consent,
    require_media_consent,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


__all__ = [name for name in globals() if not name.startswith("__")]
