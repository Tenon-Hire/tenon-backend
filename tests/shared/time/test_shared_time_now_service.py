from datetime import UTC, datetime

from app.shared.time import shared_time_now_service


def test_utcnow_prefers_explicit_test_clock_env(monkeypatch):
    monkeypatch.setenv("WINOE_TEST_NOW_UTC", "2026-04-03T13:00:00Z")
    monkeypatch.setenv("CONTRACT_LIVE_FAKE_TIME_UTC", "2026-04-01T09:00:00Z")
    monkeypatch.setenv("CONTRACT_LIVE_FAKE_TIME", "2026-04-02 09:00:00")

    assert shared_time_now_service.utcnow() == datetime(
        2026, 4, 3, 13, 0, 0, tzinfo=UTC
    )


def test_parse_test_now_accepts_legacy_naive_contract_live_format():
    assert shared_time_now_service._parse_test_now("2026-04-03 09:00:00") == datetime(
        2026, 4, 3, 9, 0, 0, tzinfo=UTC
    )
