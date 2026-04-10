from __future__ import annotations

from tests.trials.services.trials_core_service_utils import *


def test_extract_day_window_config_normalizes_overrides():
    class _ModelOverride:
        def model_dump(self, by_alias=True):
            assert by_alias is True
            return {"startLocal": "10:00", "endLocal": "19:00"}

    payload_with_overrides = SimpleNamespace(
        dayWindowStartLocal=time(hour=8, minute=0),
        dayWindowEndLocal=time(hour=16, minute=0),
        dayWindowOverridesEnabled=True,
        dayWindowOverrides={
            9: _ModelOverride(),
            "10": {"startLocal": "11:00", "endLocal": "20:00"},
            "bad": object(),
        },
    )
    (
        start_local,
        end_local,
        enabled,
        overrides,
    ) = sim_creation._extract_day_window_config(payload_with_overrides)
    assert start_local == time(hour=8, minute=0)
    assert end_local == time(hour=16, minute=0)
    assert enabled is True
    assert overrides == {
        "9": {"startLocal": "10:00", "endLocal": "19:00"},
        "10": {"startLocal": "11:00", "endLocal": "20:00"},
    }

    payload_defaults = SimpleNamespace()
    (
        start_default,
        end_default,
        enabled_default,
        overrides_default,
    ) = sim_creation._extract_day_window_config(payload_defaults)
    assert start_default == time(hour=9, minute=0)
    assert end_default == time(hour=17, minute=0)
    assert enabled_default is False
    assert overrides_default is None
