from __future__ import annotations

from tests.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_utils import *


def test_parse_positive_int_variants():
    assert handler._parse_positive_int(True) is None
    assert handler._parse_positive_int(False) is None
    assert handler._parse_positive_int(0) is None
    assert handler._parse_positive_int(-1) is None
    assert handler._parse_positive_int(7) == 7
    assert handler._parse_positive_int("5") == 5
    assert handler._parse_positive_int("0") is None
    assert handler._parse_positive_int("x5") is None
