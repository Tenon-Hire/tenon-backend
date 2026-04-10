from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


def test_validate_helpers_raise():
    cs = SimpleNamespace(trial_id=1)
    task = SimpleNamespace(id=2, trial_id=2)
    with pytest.raises(HTTPException):
        svc.ensure_task_belongs(task, cs)

    with pytest.raises(HTTPException):
        svc.ensure_in_order(SimpleNamespace(id=999), target_task_id=1)

    design_task = SimpleNamespace(type="design")
    with pytest.raises(HTTPException):
        svc.validate_submission_payload(design_task, SimpleNamespace(contentText=""))

    unknown_task = SimpleNamespace(type="mystery")
    with pytest.raises(HTTPException):
        svc.validate_submission_payload(unknown_task, SimpleNamespace(contentText="x"))

    with pytest.raises(HTTPException):
        svc.validate_github_username("bad user")

    with pytest.raises(HTTPException):
        svc.validate_repo_full_name("invalid")

    with pytest.raises(HTTPException):
        svc.validate_branch({"branch": "dict"})

    with pytest.raises(HTTPException):
        svc.validate_branch("../etc")
