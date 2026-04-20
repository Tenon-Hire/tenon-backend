from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.media.services.media_services_media_handoff_upload_storage_checks_service import (
    MAX_HANDOFF_RECORDING_DURATION_SECONDS,
    assert_uploaded_recording_duration_within_limit,
)


@pytest.mark.parametrize(
    ("actual_duration_seconds", "expected_detail"),
    [
        (None, "Uploaded recording is missing duration metadata"),
        (0, "Uploaded recording duration metadata is invalid"),
        (-1, "Uploaded recording duration metadata is invalid"),
        (
            MAX_HANDOFF_RECORDING_DURATION_SECONDS + 1,
            "Uploaded recording exceeds the 15 minute limit",
        ),
    ],
)
def test_assert_uploaded_recording_duration_within_limit_rejects_invalid_values(
    actual_duration_seconds, expected_detail
):
    with pytest.raises(HTTPException) as exc_info:
        assert_uploaded_recording_duration_within_limit(
            actual_duration_seconds=actual_duration_seconds
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == expected_detail


def test_assert_uploaded_recording_duration_within_limit_accepts_limit_boundary():
    assert_uploaded_recording_duration_within_limit(
        actual_duration_seconds=MAX_HANDOFF_RECORDING_DURATION_SECONDS
    )
