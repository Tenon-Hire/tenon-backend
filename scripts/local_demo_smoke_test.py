#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class SmokeTestConfig:
    base_url: str
    email: str
    timeout_seconds: int
    poll_interval_seconds: float


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Winoe local demo smoke test for Trial generation"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the local API server.",
    )
    parser.add_argument(
        "--email",
        default="talent_partner1@local.test",
        help="Local Talent Partner email to use with DEV auth bypass.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="Maximum time to wait for the scenario to become ready.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Delay between readiness and trial polling requests.",
    )
    return parser


def _headers(email: str) -> dict[str, str]:
    return {"x-dev-user-email": email}


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _pretty_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _payload_or_raw(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        return {"raw": response.text}
    if isinstance(payload, dict):
        return payload
    return {"raw": payload}


def _request_or_fail(
    request: Callable[[], httpx.Response],
    *,
    failure_message: str,
) -> dict[str, object]:
    try:
        response = request()
    except httpx.HTTPError as exc:
        _fail(failure_message + f"\nHTTP error: {exc}")
    payload = _payload_or_raw(response)
    return {"response": response, "payload": payload}


def _check_ready(client: httpx.Client) -> dict[str, object]:
    result = _request_or_fail(
        lambda: client.get("/ready"),
        failure_message="Readiness request failed before smoke test:",
    )
    response = result["response"]
    payload = result["payload"]
    if response.status_code != 200:
        _fail("Readiness failed before smoke test:\n" + _pretty_payload(payload))
    print(f"Readiness ok: {payload.get('status', 'unknown')}")
    return payload


def _create_trial(client: httpx.Client, *, email: str) -> dict[str, object]:
    result = _request_or_fail(
        lambda: client.post(
            "/api/trials",
            headers=_headers(email),
            json={
                "title": "Local Demo Smoke Test",
                "role": "Backend Engineer",
                "preferredLanguageFramework": "Python, FastAPI, PostgreSQL",
                "seniority": "Mid",
                "focus": "Prove Trial generation reaches a ready scenario state",
            },
        ),
        failure_message="Trial creation request failed:",
    )
    response = result["response"]
    payload = result["payload"]
    if response.status_code != 201:
        _fail("Trial creation failed:\n" + _pretty_payload(payload))
    print(
        "Trial created: id={trial_id} scenarioJobId={job_id}".format(
            trial_id=payload.get("id"), job_id=payload.get("scenarioGenerationJobId")
        )
    )
    return payload


def _wait_for_scenario_ready(
    client: httpx.Client,
    *,
    trial_id: int,
    email: str,
    timeout_seconds: int,
    poll_interval_seconds: float,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    headers = _headers(email)
    last_payload: dict[str, object] | None = None
    while time.monotonic() < deadline:
        result = _request_or_fail(
            lambda: client.get(f"/api/trials/{trial_id}", headers=headers),
            failure_message=f"Trial detail request failed for trial {trial_id}:",
        )
        response = result["response"]
        payload = result["payload"]
        if response.status_code != 200:
            _fail(
                f"Trial detail lookup failed for trial {trial_id}:\n"
                + _pretty_payload(payload)
            )
        last_payload = payload
        scenario = payload.get("scenario") if isinstance(payload, dict) else None
        if (
            isinstance(scenario, dict)
            and payload.get("status") == "ready_for_review"
            and scenario.get("status") == "ready"
            and scenario.get("versionIndex") == 1
        ):
            print(
                "Scenario ready: trialId={trial_id} scenarioId={scenario_id} "
                "version={version}".format(
                    trial_id=trial_id,
                    scenario_id=scenario.get("id"),
                    version=scenario.get("versionIndex"),
                )
            )
            return payload
        time.sleep(max(0.1, poll_interval_seconds))
    _fail(
        "Timed out waiting for a ready scenario.\n"
        + _pretty_payload(last_payload or {"trialId": trial_id})
    )


def run_smoke_test(config: SmokeTestConfig) -> None:
    with httpx.Client(base_url=config.base_url, timeout=30.0) as client:
        _check_ready(client)
        created = _create_trial(client, email=config.email)
        _wait_for_scenario_ready(
            client,
            trial_id=int(created["id"]),
            email=config.email,
            timeout_seconds=config.timeout_seconds,
            poll_interval_seconds=config.poll_interval_seconds,
        )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = SmokeTestConfig(
        base_url=args.base_url.rstrip("/"),
        email=args.email.strip(),
        timeout_seconds=max(1, int(args.timeout_seconds)),
        poll_interval_seconds=max(0.1, float(args.poll_interval_seconds)),
    )

    run_smoke_test(config)
    print("Smoke test completed successfully.")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - direct script execution
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
