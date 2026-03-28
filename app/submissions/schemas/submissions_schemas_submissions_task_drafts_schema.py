"""Application module for submissions schemas submissions task drafts schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.shared.types.shared_types_base_model import APIModel


class TaskDraftUpsertRequest(BaseModel):
    """Request payload for candidate draft autosave."""

    contentText: str | None = Field(default=None)
    contentJson: dict[str, Any] | None = Field(default=None)


class TaskDraftUpsertResponse(APIModel):
    """Response metadata for a successful draft upsert."""

    taskId: int
    updatedAt: datetime


class TaskDraftResponse(APIModel):
    """Draft record for a task in a candidate session."""

    taskId: int
    contentText: str | None = None
    contentJson: dict[str, Any] | None = None
    updatedAt: datetime
    finalizedAt: datetime | None = None
    finalizedSubmissionId: int | None = None
