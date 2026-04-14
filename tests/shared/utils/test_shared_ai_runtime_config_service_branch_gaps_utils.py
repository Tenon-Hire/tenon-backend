from __future__ import annotations

from app.ai import ai_runtime_config_service as runtime_config_service


def test_require_real_mode_covers_real_and_non_real_branches():
    assert (
        runtime_config_service.require_real_mode(
            runtime_config_service.AI_RUNTIME_MODE_REAL
        )
        is True
    )
    assert (
        runtime_config_service.require_real_mode(
            runtime_config_service.AI_RUNTIME_MODE_DEMO
        )
        is False
    )
