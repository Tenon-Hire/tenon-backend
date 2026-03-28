from __future__ import annotations

from tests.config.config_test_utils import *


def test_cors_coercion_variants():
    settings = Settings(
        CORS_ALLOW_ORIGINS='["https://one.com", "https://two.com"]',
        CORS_ALLOW_ORIGIN_REGEX=None,
    )
    assert [
        "https://one.com",
        "https://two.com",
    ] == settings.cors.CORS_ALLOW_ORIGINS
    # Invalid JSON string falls back to comma split
    assert CorsSettings._coerce_origins("[bad") == ["[bad"]
    assert CorsSettings._coerce_origins("a.com, b.com") == ["a.com", "b.com"]
