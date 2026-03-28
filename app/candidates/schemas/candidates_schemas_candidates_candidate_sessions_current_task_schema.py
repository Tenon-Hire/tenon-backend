"""Application module for candidates schemas candidates candidate sessions current task schema workflows."""

from __future__ import annotations

from datetime import datetime

from app.shared.types.shared_types_base_model import APIModel
from app.shared.types.shared_types_progress_model import ProgressSummary
from app.shared.types.shared_types_types_model import CandidateSessionStatus
from app.tasks.schemas.tasks_schemas_tasks_public_schema import TaskPublic


class CurrentTaskWindow(APIModel):
    """Window metadata for the current task day."""

    windowStartAt: datetime | None = None
    windowEndAt: datetime | None = None
    nextOpenAt: datetime | None = None
    isOpen: bool
    now: datetime


class CurrentTaskResponse(APIModel):
    """Schema for the current task assigned to the candidate."""

    candidateSessionId: int
    status: CandidateSessionStatus
    currentDayIndex: int | None
    currentTask: TaskPublic | None
    completedTaskIds: list[int]
    progress: ProgressSummary
    isComplete: bool
    currentWindow: CurrentTaskWindow | None = None
