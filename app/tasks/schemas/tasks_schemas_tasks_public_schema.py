"""Application module for tasks schemas tasks public schema workflows."""

from datetime import datetime

from app.shared.types.shared_types_base_model import APIModel


class TaskPublic(APIModel):
    """Public-facing task schema for candidates. Keeps only what the candidate needs to see."""

    id: int
    dayIndex: int
    title: str
    type: str
    description: str
    cutoffCommitSha: str | None = None
    cutoffAt: datetime | None = None
