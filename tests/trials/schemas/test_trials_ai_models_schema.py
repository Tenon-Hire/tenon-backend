from __future__ import annotations

from app.ai import (
    PromptOverrideSet,
    merge_prompt_override_payloads,
    normalize_prompt_override_payload,
)
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
    assert TrialCompanyContext.model_validate(
        {"preferredLanguageFramework": "TypeScript/Node"}
    ).model_dump() == {"preferredLanguageFramework": "TypeScript/Node"}


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


def test_trial_ai_config_serializes_prompt_overrides():
    config = TrialAIConfig.model_validate(
        {
            "promptOverrides": {
                "prestart": {"instructionsMd": "Use a realistic storyline."},
                "codeImplementationReviewer": {
                    "rubricMd": "Prefer test-first implementation."
                },
            }
        }
    )
    assert config.model_dump() == {
        "promptOverrides": {
            "prestart": {"instructionsMd": "Use a realistic storyline."},
            "codeImplementationReviewer": {
                "rubricMd": "Prefer test-first implementation."
            },
        }
    }


def test_trial_ai_config_accepts_legacy_code_implementation_override_key():
    config = TrialAIConfig.model_validate(
        {"promptOverrides": {"day23": {"rubricMd": "Legacy alias still validates."}}}
    )
    assert config.model_dump() == {
        "promptOverrides": {
            "codeImplementationReviewer": {"rubricMd": "Legacy alias still validates."}
        }
    }


def test_prompt_override_helpers_normalize_and_merge_stable_reviewer_keys():
    overrides = PromptOverrideSet.model_validate(
        {
            "prestart": {"instructionsMd": "Use a realistic storyline."},
            "codeImplementationReviewer": {
                "rubricMd": "Prefer test-first implementation."
            },
        }
    )
    assert normalize_prompt_override_payload(overrides) == {
        "prestart": {"instructionsMd": "Use a realistic storyline."},
        "codeImplementationReviewer": {"rubricMd": "Prefer test-first implementation."},
    }
    assert normalize_prompt_override_payload("not-a-payload") is None

    merged = merge_prompt_override_payloads(
        incoming={"codeImplementationReviewer": {"rubricMd": "Updated rubric."}},
        fallback={
            "prestart": {"instructionsMd": "Use a realistic storyline."},
            "codeImplementationReviewer": {
                "rubricMd": "Prefer test-first implementation."
            },
        },
    )
    assert merged == {
        "prestart": {"instructionsMd": "Use a realistic storyline."},
        "codeImplementationReviewer": {"rubricMd": "Updated rubric."},
    }

    cleared = merge_prompt_override_payloads(
        incoming={"codeImplementationReviewer": None},
        fallback={
            "codeImplementationReviewer": {
                "rubricMd": "Prefer test-first implementation."
            }
        },
    )
    assert cleared is None
