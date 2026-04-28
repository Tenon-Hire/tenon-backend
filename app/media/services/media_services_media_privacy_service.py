from __future__ import annotations

from app.config import settings
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import repository as transcripts_repo

from .media_services_media_privacy_consent_service import (
    record_candidate_session_consent,
    require_media_consent,
)
from .media_services_media_privacy_delete_service import delete_recording_asset
from .media_services_media_privacy_model import MediaRetentionPurgeResult
from .media_services_media_privacy_purge_service import (
    compute_media_retention_expires_at,
    purge_candidate_session_media_for_data_request,
    purge_expired_media_assets,
)

__all__ = [
    "MediaRetentionPurgeResult",
    "compute_media_retention_expires_at",
    "delete_recording_asset",
    "purge_candidate_session_media_for_data_request",
    "purge_expired_media_assets",
    "record_candidate_session_consent",
    "recordings_repo",
    "require_media_consent",
    "settings",
    "transcripts_repo",
]
