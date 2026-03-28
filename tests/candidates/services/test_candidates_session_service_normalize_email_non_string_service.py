from __future__ import annotations

from tests.candidates.services.candidates_session_service_utils import *


def test_normalize_email_non_string():
    assert cs_service._normalize_email(123) == ""
