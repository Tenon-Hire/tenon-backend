from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import HTTPException

from app.integrations.github import GithubError
from app.integrations.github.actions_runner import ActionsRunResult
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as svc,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _valid_day5_reflection_sections() -> dict[str, str]:
    return {
        "challenges": "Handled ambiguous requirements with explicit assumptions.",
        "decisions": "Chose stable contracts with machine-readable validation errors.",
        "tradeoffs": "Accepted stricter validation to improve talent_partner scoring consistency.",
        "communication": "Documented progress and open risks during each handoff checkpoint.",
        "next": "Would add evaluator evidence pointers and richer rubric alignment.",
    }


__all__ = [name for name in globals() if not name.startswith("__")]
