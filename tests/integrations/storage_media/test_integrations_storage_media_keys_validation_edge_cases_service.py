from __future__ import annotations

import pytest

from tests.integrations.storage_media.test_integrations_storage_media_service_utils import *


def test_keys_validation_edge_cases():
    with pytest.raises(ValueError):
        parse_recording_public_id("rec_0")
    with pytest.raises(ValueError):
        normalize_extension("")
    with pytest.raises(ValueError):
        normalize_extension("m-p4")
    with pytest.raises(ValueError):
        build_recording_storage_key(
            candidate_session_id=0,
            task_id=1,
            extension="mp4",
        )
