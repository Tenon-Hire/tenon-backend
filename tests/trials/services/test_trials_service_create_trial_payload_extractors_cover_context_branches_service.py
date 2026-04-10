from __future__ import annotations

from tests.trials.services.trials_core_service_utils import *


def test_create_trial_payload_extractors_cover_context_branches():
    payload_with_dicts = SimpleNamespace(
        companyContext={"domain": "social"},
        ai={
            "noticeVersion": "mvp1",
            "noticeText": "Notice",
            "evalEnabledByDay": {"1": True},
        },
    )
    assert sim_creation._extract_company_context(payload_with_dicts) == {
        "domain": "social"
    }
    assert sim_creation._extract_ai_fields(payload_with_dicts) == (
        "mvp1",
        "Notice",
        {"1": True},
        None,
    )

    payload_with_object = SimpleNamespace(
        company_context={"productArea": "creator tools"},
        ai=SimpleNamespace(
            notice_version=None,
            noticeVersion="mvp2",
            notice_text=None,
            noticeText="Fallback",
            eval_enabled_by_day=None,
            evalEnabledByDay={"2": False},
        ),
    )
    assert sim_creation._extract_company_context(payload_with_object) == {
        "productArea": "creator tools"
    }
    assert sim_creation._extract_ai_fields(payload_with_object) == (
        "mvp2",
        "Fallback",
        {"2": False},
        None,
    )

    payload_with_unsupported_company_context = SimpleNamespace(
        companyContext=object(),
    )
    assert (
        sim_creation._extract_company_context(payload_with_unsupported_company_context)
        is None
    )
