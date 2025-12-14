from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionCreateRequest(BaseModel):
    """Schema for creating a submission."""

    contentText: str | None = Field(default=None)
    codeBlob: str | None = Field(default=None)
    files: dict[str, str] | None = Field(default=None)


class ProgressSummary(BaseModel):
    """Schema for summarizing progress."""

    completed: int
    total: int


class SubmissionCreateResponse(BaseModel):
    """Schema for submission creation response."""

    submissionId: int
    taskId: int
    candidateSessionId: int
    submittedAt: datetime
    progress: ProgressSummary
    isComplete: bool
