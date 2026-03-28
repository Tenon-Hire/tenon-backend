from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.evaluations.repositories import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
)
from app.evaluations.repositories import (
    evaluations_repositories_evaluations_create_run_helpers_repository as run_helpers,
)


@pytest.mark.parametrize(
    "status",
    [EVALUATION_RUN_STATUS_PENDING, EVALUATION_RUN_STATUS_RUNNING],
)
def test_normalize_run_time_fields_rejects_generated_at_for_non_terminal_statuses(
    status: str,
):
    started_at = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
    generated_at = datetime(2026, 3, 11, 12, 5, tzinfo=UTC)

    with pytest.raises(ValueError, match="generated_at is not allowed"):
        run_helpers.normalize_run_time_fields(
            status=status,
            started_at=started_at,
            completed_at=None,
            generated_at=generated_at,
        )


def test_normalize_run_time_fields_rejects_generated_at_before_started_at():
    started_at = datetime(2026, 3, 11, 12, 10, tzinfo=UTC)
    completed_at = datetime(2026, 3, 11, 12, 20, tzinfo=UTC)
    generated_at = datetime(2026, 3, 11, 12, 9, tzinfo=UTC)

    with pytest.raises(ValueError, match="generated_at must be greater than or equal"):
        run_helpers.normalize_run_time_fields(
            status=EVALUATION_RUN_STATUS_COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            generated_at=generated_at,
        )
