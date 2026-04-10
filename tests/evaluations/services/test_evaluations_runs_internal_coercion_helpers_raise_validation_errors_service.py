from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


def test_internal_coercion_helpers_raise_validation_errors():
    with pytest.raises(eval_service.EvaluationRunStateError, match="is required"):
        eval_service._coerce_unit_interval_score(
            None,
            field_name="overall_winoe_score",
            required=True,
        )
    with pytest.raises(eval_service.EvaluationRunStateError, match="must be numeric"):
        eval_service._coerce_unit_interval_score(
            "bad",
            field_name="overall_winoe_score",
            required=False,
        )
    with pytest.raises(eval_service.EvaluationRunStateError, match="must be finite"):
        eval_service._coerce_unit_interval_score(
            float("nan"),
            field_name="overall_winoe_score",
            required=False,
        )
    with pytest.raises(
        eval_service.EvaluationRunStateError, match="must be between 0 and 1"
    ):
        eval_service._coerce_unit_interval_score(
            2,
            field_name="overall_winoe_score",
            required=False,
        )

    with pytest.raises(
        eval_service.EvaluationRunStateError,
        match="recommendation is required",
    ):
        eval_service._coerce_recommendation(None, required=True)
    with pytest.raises(
        eval_service.EvaluationRunStateError,
        match="non-empty string",
    ):
        eval_service._coerce_recommendation(" ", required=False)
    with pytest.raises(
        eval_service.EvaluationRunStateError, match="invalid recommendation"
    ):
        eval_service._coerce_recommendation("maybe", required=False)

    with pytest.raises(eval_service.EvaluationRunStateError, match="must be an object"):
        eval_service._coerce_raw_report_json(["bad"])  # type: ignore[arg-type]
