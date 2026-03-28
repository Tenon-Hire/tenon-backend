from __future__ import annotations

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RECOMMENDATION_HIRE,
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
    EVALUATION_RECOMMENDATION_NO_HIRE,
    EVALUATION_RECOMMENDATION_STRONG_HIRE,
)
from app.evaluations.services import evaluator


def test_evaluator_helper_functions():
    assert evaluator._safe_repo_full_name(None) is None
    assert evaluator._safe_repo_full_name("bad repo name") is None
    assert evaluator._safe_repo_full_name(" acme/repo-1 ") == "acme/repo-1"
    assert evaluator._to_excerpt(None) is None
    assert evaluator._to_excerpt("   \n  ") is None
    assert evaluator._to_excerpt("hello\nworld") == "hello world"
    assert evaluator._to_excerpt("x" * 20, max_chars=5) == "xxxxx"
    assert evaluator._safe_int(True) is None
    assert evaluator._safe_int(7) == 7
    assert evaluator._safe_int(7.9) == 7
    assert evaluator._safe_int("7") is None
    assert evaluator._segment_start_ms({"startMs": 10}) == 10
    assert evaluator._segment_start_ms({"start_ms": -2}) == 0
    assert evaluator._segment_start_ms({"start": 3.5}) == 3
    assert evaluator._segment_start_ms({"unknown": 1}) is None
    assert evaluator._segment_end_ms({"endMs": 20}) == 20
    assert evaluator._segment_end_ms({"end_ms": -1}) == 0
    assert evaluator._segment_end_ms({"end": 4.9}) == 4
    assert evaluator._segment_end_ms({"unknown": 1}) is None
    assert evaluator._segment_text({"text": "hello"}) == "hello"
    assert evaluator._segment_text({"content": "world"}) == "world"
    assert evaluator._segment_text({"excerpt": "snippet"}) == "snippet"
    assert evaluator._segment_text({"text": "  "}) is None


def test_recommendation_thresholds():
    assert (
        evaluator._recommendation_from_score(0.9)
        == EVALUATION_RECOMMENDATION_STRONG_HIRE
    )
    assert evaluator._recommendation_from_score(0.7) == EVALUATION_RECOMMENDATION_HIRE
    assert (
        evaluator._recommendation_from_score(0.55)
        == EVALUATION_RECOMMENDATION_LEAN_HIRE
    )
    assert (
        evaluator._recommendation_from_score(0.54) == EVALUATION_RECOMMENDATION_NO_HIRE
    )
