"""Application module for types model workflows."""

from typing import Literal

CandidateSessionStatus = Literal["not_started", "in_progress", "completed", "expired"]
TaskType = Literal["design", "code", "debug", "handoff", "documentation"]
TrialStatus = Literal[
    "draft",
    "generating",
    "ready_for_review",
    "active_inviting",
    "terminated",
]

CANDIDATE_SESSION_STATUS_COMPLETED: CandidateSessionStatus = "completed"
