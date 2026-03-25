from __future__ import annotations

from pydantic import BaseModel, Field

from app.shared.types.shared_types_base_model import APIModel


class HandoffUploadInitRequest(BaseModel):
    contentType: str
    sizeBytes: int = Field(gt=0)
    filename: str | None = None


class HandoffUploadInitResponse(APIModel):
    recordingId: str
    uploadUrl: str
    expiresInSeconds: int


class HandoffUploadCompleteRequest(BaseModel):
    recordingId: str


class HandoffUploadCompleteResponse(APIModel):
    recordingId: str
    status: str


class HandoffStatusRecordingOut(APIModel):
    recordingId: str
    status: str
    downloadUrl: str | None = None


class HandoffStatusTranscriptSegmentOut(APIModel):
    id: str | None = None
    startMs: int | None = None
    endMs: int | None = None
    text: str


class HandoffStatusTranscriptOut(APIModel):
    status: str
    progress: int | None = None
    text: str | None = None
    segments: list[HandoffStatusTranscriptSegmentOut] | None = None


class HandoffStatusResponse(APIModel):
    recording: HandoffStatusRecordingOut | None = None
    transcript: HandoffStatusTranscriptOut | None = None
