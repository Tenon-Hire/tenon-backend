from __future__ import annotations

from tests.evaluations.services.evaluations_fit_profile_composer_utils import *


def test_fit_profile_composer_helper_normalizers():
    assert fit_profile_composer._normalize_datetime(None) is None
    normalized = fit_profile_composer._normalize_datetime(datetime(2026, 3, 12, 10, 0))
    assert normalized is not None
    assert normalized.tzinfo is not None
    aware = datetime(2026, 3, 12, 10, 0, tzinfo=timezone(timedelta(hours=-5)))
    utc_value = fit_profile_composer._normalize_datetime(aware)
    assert utc_value is not None
    assert utc_value.tzinfo == UTC

    assert fit_profile_composer._normalize_unit_interval(True) is None
    assert fit_profile_composer._normalize_unit_interval("0.3") is None
    assert fit_profile_composer._normalize_unit_interval(1.2) is None
    assert fit_profile_composer._normalize_unit_interval(0.33333) == 0.3333

    assert (
        fit_profile_composer._normalize_recommendation(None)
        == EVALUATION_RECOMMENDATION_LEAN_HIRE
    )
    assert fit_profile_composer._normalize_recommendation(" no_hire ") == "no_hire"
    assert (
        fit_profile_composer._normalize_recommendation("not-valid")
        == EVALUATION_RECOMMENDATION_LEAN_HIRE
    )
