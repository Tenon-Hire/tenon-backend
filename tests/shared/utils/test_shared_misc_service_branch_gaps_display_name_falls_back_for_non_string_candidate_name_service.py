from __future__ import annotations

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


def test_display_name_falls_back_for_non_string_candidate_name():
    resolved = candidates_compare._display_name(None, position=0)
    assert resolved == "Candidate A"
