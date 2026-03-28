from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


def test_is_code_task_and_branch_validation():
    assert svc.is_code_task(SimpleNamespace(type="code")) is True
    assert svc.is_code_task(SimpleNamespace(type="design")) is False
    with pytest.raises(HTTPException):
        svc.validate_branch("~weird")
    assert svc.validate_branch(None) is None
