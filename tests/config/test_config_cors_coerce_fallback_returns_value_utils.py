from __future__ import annotations

from tests.config.config_test_utils import *


def test_cors_coerce_fallback_returns_value():
    assert CorsSettings._coerce_origins(123) == 123
