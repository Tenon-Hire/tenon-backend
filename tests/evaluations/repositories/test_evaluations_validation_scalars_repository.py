from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.evaluations.repositories import (
    evaluations_repositories_evaluations_validation_scalars_repository as scalars,
)


def test_normalize_non_empty_and_optional_strings():
    assert scalars.normalize_non_empty_str("  ok  ", field_name="name") == "ok"
    assert scalars.normalize_optional_non_empty_str(None, field_name="note") is None
    assert (
        scalars.normalize_optional_non_empty_str("  value ", field_name="note")
        == "value"
    )

    with pytest.raises(ValueError):
        scalars.normalize_non_empty_str("", field_name="name")
    with pytest.raises(ValueError):
        scalars.normalize_non_empty_str(123, field_name="name")


def test_normalize_datetime_behaviors():
    now_value = scalars.normalize_datetime(
        None, field_name="started_at", default_now=True
    )
    assert isinstance(now_value, datetime)
    assert now_value.tzinfo == UTC
    assert now_value.microsecond == 0

    assert (
        scalars.normalize_datetime(None, field_name="started_at", default_now=False)
        is None
    )

    naive = datetime(2026, 3, 20, 9, 0, 0)
    assert (
        scalars.normalize_datetime(
            naive, field_name="started_at", default_now=False
        ).tzinfo
        == UTC
    )

    aware = datetime(2026, 3, 20, 9, 0, 0, tzinfo=UTC)
    assert (
        scalars.normalize_datetime(aware, field_name="started_at", default_now=False)
        is aware
    )

    with pytest.raises(ValueError):
        scalars.normalize_datetime("bad", field_name="started_at", default_now=False)


def test_status_and_object_coercion():
    assert scalars.normalize_status(" pending ") == "pending"
    with pytest.raises(ValueError):
        scalars.normalize_status("unknown")

    assert scalars.coerce_object(None, field_name="rubric") is None
    assert scalars.coerce_object({"a": 1}, field_name="rubric") == {"a": 1}
    with pytest.raises(ValueError):
        scalars.coerce_object([], field_name="rubric")


def test_unit_interval_score_and_recommendation_validation():
    assert (
        scalars.coerce_unit_interval_score(0.5, field_name="score", required=True)
        == 0.5
    )
    assert (
        scalars.coerce_unit_interval_score(None, field_name="score", required=False)
        is None
    )

    with pytest.raises(ValueError):
        scalars.coerce_unit_interval_score(None, field_name="score", required=True)
    with pytest.raises(ValueError):
        scalars.coerce_unit_interval_score(True, field_name="score")
    with pytest.raises(ValueError):
        scalars.coerce_unit_interval_score(float("inf"), field_name="score")
    with pytest.raises(ValueError):
        scalars.coerce_unit_interval_score(-0.1, field_name="score")
    with pytest.raises(ValueError):
        scalars.coerce_unit_interval_score(1.1, field_name="score")

    assert scalars.coerce_recommendation(" No_Hire ", required=True) == "no_hire"
    assert scalars.coerce_recommendation(None, required=False) is None
    with pytest.raises(ValueError):
        scalars.coerce_recommendation("   ", required=False)
    with pytest.raises(ValueError):
        scalars.coerce_recommendation(None, required=True)
    with pytest.raises(ValueError):
        scalars.coerce_recommendation("invalid-choice", required=True)


def test_day_index_score_and_rubric_coercion():
    assert scalars.coerce_day_index(3, field_path="day.index") == 3
    with pytest.raises(ValueError):
        scalars.coerce_day_index(True, field_path="day.index")
    with pytest.raises(ValueError):
        scalars.coerce_day_index(0, field_path="day.index")
    with pytest.raises(ValueError):
        scalars.coerce_day_index(6, field_path="day.index")

    assert scalars.coerce_score(0.25, field_path="day.score") == 0.25
    with pytest.raises(ValueError):
        scalars.coerce_score(False, field_path="day.score")
    with pytest.raises(ValueError):
        scalars.coerce_score(float("nan"), field_path="day.score")

    assert scalars.coerce_rubric_results_json({"a": 1}, field_path="day.rubric") == {
        "a": 1
    }
    with pytest.raises(ValueError):
        scalars.coerce_rubric_results_json([], field_path="day.rubric")
