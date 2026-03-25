from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_process_parsed_output_empty_dict_returns_empty_tuple():
    parsed = process_parsed_output({}, include_output=True, max_output_chars=20)
    assert parsed == (None,) * 13
