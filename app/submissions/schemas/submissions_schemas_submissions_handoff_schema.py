"""Application module for submissions schemas submissions handoff schema workflows."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.shared.types.shared_types_base_model import APIModel


class HandoffUploadInitRequest(BaseModel):
    """Represent handoff upload init request data and behavior."""

    contentType: str
    sizeBytes: int = Field(gt=0)
    filename: str | None = None


class HandoffUploadInitResponse(APIModel):
    """Represent handoff upload init response data and behavior."""

    recordingId: str
    uploadUrl: str
    expiresInSeconds: int


class HandoffUploadCompleteRequest(BaseModel):
    """Represent handoff upload complete request data and behavior."""

    recordingId: str


class HandoffUploadCompleteResponse(APIModel):
    """Represent handoff upload complete response data and behavior."""

    recordingId: str
    status: str


class HandoffStatusRecordingOut(APIModel):
    """Represent handoff status recording out data and behavior."""

    recordingId: str
    status: str
    downloadUrl: str | None = None


class HandoffStatusTranscriptSegmentOut(APIModel):
    """Represent handoff status transcript segment out data and behavior."""

    id: str | None = None
    startMs: int | None = None
    endMs: int | None = None
    text: str


class HandoffStatusTranscriptOut(APIModel):
    """Represent handoff status transcript out data and behavior."""

    status: str
    progress: int | None = None
    text: str | None = None
    segments: list[HandoffStatusTranscriptSegmentOut] | None = None


class HandoffStatusResponse(APIModel):
    """Represent handoff status response data and behavior."""

    recording: HandoffStatusRecordingOut | None = None
    transcript: HandoffStatusTranscriptOut | None = None
