from __future__ import annotations

import pytest

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


def test_parse_recording_public_id_rejects_zero_digit_form():
    with pytest.raises(ValueError, match="recordingId"):
        media_keys.parse_recording_public_id("0")
