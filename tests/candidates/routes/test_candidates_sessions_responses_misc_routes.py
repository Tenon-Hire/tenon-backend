from __future__ import annotations

from types import SimpleNamespace

from app.candidates.routes.candidate_sessions_routes import responses as cs_responses
from app.submissions.services.task_drafts import (
    submissions_services_task_drafts_submissions_task_drafts_finalization_service as finalization,
)


def test_resolve_trial_summary_includes_content_sections_branch():
    summary = cs_responses._resolve_trial_summary(
        SimpleNamespace(
            trial=SimpleNamespace(id=1, title="Demo Trial", role="Backend")
        ),
        include_content_sections=True,
    )
    assert summary.id == 1
    assert summary.title == "Demo Trial"
    assert summary.role == "Backend"


def test_task_draft_finalization_payload_builder():
    payload = finalization.build_submission_payload(
        content_text="draft content", content_json={"delta": 1}
    )
    assert payload.contentText == "draft content"
    assert payload.contentJson == {"delta": 1}
