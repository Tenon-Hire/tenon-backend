from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config.config_settings_validators_config import SettingsValidationMixin
from tests.config.config_test_utils import *


def test_coerce_demo_allowlist_talent_partner_ids_handles_scalar_and_mixed_values():
    assert Settings._coerce_demo_allowlist_talent_partner_ids(7) == [7]
    assert Settings._coerce_demo_allowlist_talent_partner_ids(
        [True, 5, " 9 ", "abc", ""]
    ) == [
        5,
        9,
    ]


def test_coerce_perf_span_sample_rate_invalid_defaults_to_one():
    assert Settings._coerce_perf_span_sample_rate("not-a-number") == 1.0
    assert Settings._coerce_perf_span_sample_rate(None) == 1.0


def test_validate_cors_posture_accepts_non_empty_string_origin():
    dummy = SimpleNamespace(
        ENV="prod",
        cors=SimpleNamespace(
            CORS_ALLOW_ORIGINS=" https://frontend.winoe.ai ",
            CORS_ALLOW_ORIGIN_REGEX=None,
        ),
    )
    assert SettingsValidationMixin._validate_cors_posture(dummy) is dummy


def test_validate_cors_posture_non_iterable_origins_fails_as_empty():
    dummy = SimpleNamespace(
        ENV="prod",
        cors=SimpleNamespace(
            CORS_ALLOW_ORIGINS=123,
            CORS_ALLOW_ORIGIN_REGEX=None,
        ),
    )
    with pytest.raises(ValueError, match="CORS_ALLOW_ORIGINS must be configured"):
        SettingsValidationMixin._validate_cors_posture(dummy)
