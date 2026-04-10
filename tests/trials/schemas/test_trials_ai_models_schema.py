from __future__ import annotations

from app.trials.schemas.trials_schemas_trials_ai_models_schema import (
    TrialAIConfig,
    TrialCompanyContext,
)


def test_trial_company_context_serializer_omits_none_fields():
    assert TrialCompanyContext.model_validate({}).model_dump() == {}
    assert TrialCompanyContext.model_validate({"domain": "fintech"}).model_dump() == {
        "domain": "fintech"
    }
    assert TrialCompanyContext.model_validate(
        {"productArea": "payments"}
    ).model_dump() == {"productArea": "payments"}


def test_trial_ai_config_serializer_omits_none_fields():
    assert TrialAIConfig.model_validate({}).model_dump() == {}
    assert TrialAIConfig.model_validate({"noticeVersion": "mvp1"}).model_dump() == {
        "noticeVersion": "mvp1"
    }
    assert TrialAIConfig.model_validate({"noticeText": "notice"}).model_dump() == {
        "noticeText": "notice"
    }
    assert TrialAIConfig.model_validate(
        {"evalEnabledByDay": {"1": True}}
    ).model_dump() == {"evalEnabledByDay": {"1": True}}
