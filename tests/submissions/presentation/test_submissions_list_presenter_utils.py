from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.submissions.presentation import (
    submissions_presentation_submissions_list_presenter_utils as presenter,
)
from app.submissions.presentation.submissions_presentation_submissions_commit_basis_utils import (
    resolve_commit_basis,
)


def _submission(**overrides):
    base = {
        "id": 1,
        "candidate_session_id": 11,
        "task_id": 21,
        "submitted_at": datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        "test_output": None,
        "diff_summary_json": None,
        "code_repo_path": "org/repo",
        "workflow_run_id": "44",
        "commit_sha": "fallback-sha",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _task(**overrides):
    base = {"day_index": 2, "type": "code"}
    base.update(overrides)
    return SimpleNamespace(**base)


def test_present_list_item_commit_url_fallback_and_test_result_link_enrichment(
    monkeypatch,
):
    captured: dict[str, object] = {}

    def _build_test_results(*_args, **kwargs):
        captured.update(kwargs)
        return {"status": "passed"}

    monkeypatch.setattr(
        presenter.talent_partner_sub_service,
        "parse_test_output",
        lambda _output: {"status": "ok"},
    )
    monkeypatch.setattr(
        presenter, "parse_diff_summary", lambda _raw: {"base": "a", "head": "b"}
    )
    monkeypatch.setattr(
        presenter,
        "resolve_commit_basis",
        lambda _sub, _day_audit: ("basis-sha", None, None, None),
    )
    monkeypatch.setattr(
        presenter,
        "build_links",
        lambda _repo, _sha, _run: (None, "https://github.com/org/repo/actions/runs/44"),
    )
    monkeypatch.setattr(presenter, "build_diff_url", lambda _repo, _summary: None)
    monkeypatch.setattr(presenter, "build_test_results", _build_test_results)

    payload = presenter.present_list_item(_submission(), _task())

    assert payload["commitSha"] == "basis-sha"
    assert payload["commitUrl"] == "https://github.com/org/repo/commit/fallback-sha"
    assert payload["testResults"]["status"] == "passed"
    assert payload["testResults"]["commitUrl"] == payload["commitUrl"]
    assert payload["testResults"]["workflowUrl"] == payload["workflowUrl"]
    assert captured["commit_sha_override"] == "basis-sha"


def test_present_list_item_does_not_overwrite_existing_result_links(monkeypatch):
    monkeypatch.setattr(
        presenter.talent_partner_sub_service,
        "parse_test_output",
        lambda _output: {"status": "ok"},
    )
    monkeypatch.setattr(presenter, "parse_diff_summary", lambda _raw: None)
    monkeypatch.setattr(
        presenter,
        "resolve_commit_basis",
        lambda _sub, _day_audit: ("basis-sha", None, None, None),
    )
    monkeypatch.setattr(
        presenter,
        "build_links",
        lambda _repo, _sha, _run: (
            "https://github.com/org/repo/commit/new-sha",
            "https://github.com/org/repo/actions/runs/44",
        ),
    )
    monkeypatch.setattr(presenter, "build_diff_url", lambda _repo, _summary: None)
    monkeypatch.setattr(
        presenter,
        "build_test_results",
        lambda *_args, **_kwargs: {
            "status": "passed",
            "commitUrl": "https://custom/commit",
            "workflowUrl": "https://custom/workflow",
        },
    )

    payload = presenter.present_list_item(_submission(commit_sha="unused"), _task())

    assert payload["testResults"]["commitUrl"] == "https://custom/commit"
    assert payload["testResults"]["workflowUrl"] == "https://custom/workflow"


def test_resolve_commit_basis_prefers_cutoff_sha_over_mutable_head():
    submission = SimpleNamespace(commit_sha="mutable-head")
    day_audit = SimpleNamespace(
        cutoff_commit_sha="pinned-cutoff",
        cutoff_at=datetime(2026, 3, 20, 14, 0, tzinfo=UTC),
        eval_basis_ref="refs/heads/main@cutoff",
    )

    commit_sha, cutoff_commit_sha, cutoff_at, eval_basis_ref = resolve_commit_basis(
        submission, day_audit
    )

    assert commit_sha == "pinned-cutoff"
    assert cutoff_commit_sha == "pinned-cutoff"
    assert cutoff_at == day_audit.cutoff_at
    assert eval_basis_ref == "refs/heads/main@cutoff"
