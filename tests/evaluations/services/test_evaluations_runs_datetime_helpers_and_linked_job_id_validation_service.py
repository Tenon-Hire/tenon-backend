from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


def test_datetime_helpers_and_linked_job_id_validation():
    with pytest.raises(
        eval_service.EvaluationRunStateError, match="must be a datetime"
    ):
        eval_service._normalize_datetime("not-a-datetime", field_name="completed_at")  # type: ignore[arg-type]
    with pytest.raises(
        eval_service.EvaluationRunStateError, match="must be a datetime"
    ):
        eval_service._normalize_stored_datetime(123, field_name="started_at")  # type: ignore[arg-type]

    naive = datetime(2026, 3, 11, 12, 0)
    normalized = eval_service._normalize_datetime(naive, field_name="completed_at")
    assert normalized.tzinfo is not None
    assert eval_service._linked_job_id("not-a-mapping") is None
