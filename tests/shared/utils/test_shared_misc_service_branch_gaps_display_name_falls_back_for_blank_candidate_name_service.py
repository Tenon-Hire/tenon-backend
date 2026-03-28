from __future__ import annotations

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


def test_display_name_falls_back_for_blank_candidate_name():
    resolved = candidates_compare._display_name("   ", position=27)
    assert resolved == "Candidate AB"
