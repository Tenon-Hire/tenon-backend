#!/usr/bin/env python3
"""Smoke test the public compare contract against a running backend.

Usage:
  python scripts/compare_contract_smoke_test.py \
    --base-url http://127.0.0.1:8000 \
    --trial-id 123 \
    --auth-token talent_partner:alice@example.com
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_INTERNAL_RECOMMENDATIONS = {
    "hire",
    "lean_hire",
    "strong_hire",
    "no_hire",
    "reject",
    "pass",
    "fail",
    "Winoe recommends",
}

_PUBLIC_RECOMMENDATIONS = {
    "strong_signal",
    "positive_signal",
    "mixed_signal",
    "limited_signal",
}


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _assert_public_payload(payload: dict, *, expected_trial_id: int) -> None:
    required_keys = {"trialId", "cohortSize", "state", "message", "candidates"}
    if set(payload) != required_keys:
        _fail(f"unexpected top-level keys: {sorted(payload)}")
    if payload["trialId"] != expected_trial_id:
        _fail(f"trialId mismatch: {payload['trialId']} != {expected_trial_id}")
    if not isinstance(payload["candidates"], list):
        _fail("candidates must be a list")
    for row in payload["candidates"]:
        if set(row) != {
            "candidateSessionId",
            "candidateName",
            "candidateDisplayName",
            "status",
            "winoeReportStatus",
            "overallWinoeScore",
            "recommendation",
            "dayCompletion",
            "updatedAt",
        }:
            _fail(f"unexpected candidate keys: {sorted(row)}")
        recommendation = row["recommendation"]
        if recommendation is not None and recommendation not in _PUBLIC_RECOMMENDATIONS:
            _fail(f"unexpected public recommendation: {recommendation}")
        if recommendation in _INTERNAL_RECOMMENDATIONS:
            _fail(f"internal recommendation leaked: {recommendation}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--trial-id", required=True, type=int)
    parser.add_argument("--auth-token", required=True)
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/api/trials/{args.trial_id}/candidates/compare"
    request = Request(url, headers={"Authorization": f"Bearer {args.auth_token}"})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
    except HTTPError as exc:
        print(f"HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    _assert_public_payload(payload, expected_trial_id=args.trial_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
