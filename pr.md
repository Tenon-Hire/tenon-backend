# P0 Candidate Core: CandidateSession scheduling fields + simulation day windows + schedule endpoint (#198)

## TL;DR

- Added scheduling persistence on `candidate_sessions`: `scheduled_start_at`, `candidate_timezone`, `day_windows_json`, `schedule_locked_at`.
- Added simulation-level day window config: `day_window_start_local` (`09:00` default), `day_window_end_local` (`17:00` default), `day_window_overrides_enabled`, `day_window_overrides_json`.
- Added candidate-auth endpoint `POST /api/candidate/session/{token}/schedule` with schedule locking, timezone validation, and deterministic Day 1-5 UTC windows.
- Enriched candidate payloads (`resolve` + invite list + schedule response) with schedule fields and derived `currentDayWindow` where applicable.
- Triggered candidate + recruiter schedule confirmation emails via existing notification abstraction; dispatch is best-effort after DB commit.
- Implemented canonical/idempotent behavior: normalized timezone, second-precision UTC schedule timestamps, serialized `day_windows_json` in Zulu string format, and same-input retries return success.

## Problem / Why

- MVP1 requires five consecutive scheduled days with local-time windows (default 9AM-5PM), but previous progression had no scheduling semantics.
- Recruiters need confidence that artifacts are produced within declared availability windows.
- Persisting derived UTC windows at schedule-time makes enforcement deterministic across DST and later processing.
- A lock-once schedule model is needed to prevent candidate-side rescheduling drift.

## Changes (detailed)

### DB / Models

- `CandidateSession` fields added:
- `scheduled_start_at` (`DateTime(timezone=True)`, nullable)
- `candidate_timezone` (`String(255)`, nullable)
- `day_windows_json` (`JSON`, nullable)
- `schedule_locked_at` (`DateTime(timezone=True)`, nullable)

- `Simulation` fields added:
- `day_window_start_local` (`Time`, non-null, server default `'09:00:00'`)
- `day_window_end_local` (`Time`, non-null, server default `'17:00:00'`)
- `day_window_overrides_enabled` (`Boolean`, non-null, server default `false`)
- `day_window_overrides_json` (`JSON`, nullable)
- Per-day override payload keys are gated to days `9`-`21` when `TENON_SCHEDULE_DAY_WINDOW_OVERRIDES_ENABLED=true`.

- Migration:
- `alembic/versions/202603050001_add_candidate_schedule_and_sim_window_config.py`
- Adds all scheduling columns above and includes clean downgrade removal.

### API

- New endpoint: `POST /api/candidate/session/{token}/schedule`
- Auth: candidate bearer principal + token, with ownership checks (`invite email == auth email`), verified email, claimed invite, and expiry/termination checks.

- Request example:

```json
{
  "scheduledStartAt": "2026-03-10T13:00:00Z",
  "candidateTimezone": "America/New_York"
}
```

- Response example:

```json
{
  "candidateSessionId": 123,
  "scheduledStartAt": "2026-03-10T13:00:00Z",
  "candidateTimezone": "America/New_York",
  "dayWindows": [
    {
      "dayIndex": 1,
      "windowStartAt": "2026-03-10T13:00:00Z",
      "windowEndAt": "2026-03-10T21:00:00Z"
    }
  ],
  "scheduleLockedAt": "2026-03-02T17:00:00Z"
}
```

- Error codes and statuses:
- `409` `SCHEDULE_ALREADY_SET`
- `422` `SCHEDULE_INVALID_TIMEZONE`
- `422` `SCHEDULE_START_IN_PAST`
- `403` `SCHEDULE_NOT_CLAIMED`
- `410` `INVITE_TOKEN_EXPIRED` (repo convention for expired invite token paths)

### Behavior

- Row-level concurrency:
- Scheduling uses token lookup with `FOR UPDATE OF candidate_sessions` row lock semantics (`fetch_by_token_for_update`).

- Idempotency:
- If schedule is already locked and incoming schedule/timezone match normalized stored values, endpoint returns success (no conflict, no duplicate email send).
- If locked and values differ, returns `409 SCHEDULE_ALREADY_SET`.

- Canonicalization:
- Incoming timezone is trimmed and validated to a canonical IANA key before comparison/persistence.
- `scheduled_start_at` is normalized to UTC and truncated to second precision.
- Persisted `day_windows_json` stores UTC timestamps as canonical Zulu strings (`YYYY-MM-DDTHH:MM:SSZ`) for deterministic reads/comparisons.

- Payload enrichment:
- `resolve` and candidate invite list responses include `scheduledStartAt`, `candidateTimezone`, `dayWindows`, `scheduleLockedAt`, and derived `currentDayWindow`.

- Email confirmations:
- On first schedule set, candidate + recruiter confirmation emails are dispatched through notification service.
- Dispatch failures are logged and swallowed after commit (state remains persisted).

## Tests

Commands run:

- `poetry run ruff check .` -> PASS
- `poetry run pytest -q` -> PASS (`926 passed in 16.10s`, coverage gate met)
- `poetry run python -m compileall app tests` -> PASS

Notable tests:

- `tests/api/test_candidate_session_schedule.py`
- route registered once at `/api/candidate/session/{token}/schedule`
- happy path persistence + email send
- idempotent same-payload retry + conflict on changed payload
- expired token maps to `410` + `INVITE_TOKEN_EXPIRED`

- `tests/unit/test_scheduling_day_windows.py`
- DST-aware derivation
- timezone validation
- canonical serialization/deserialization (`Z` + second precision)

- `tests/unit/test_candidate_session_schedule_service.py`
- service-level lock/idempotency/conflict
- JSON day-window storage shape assertions
- token-expiry mapping behavior and ownership/claim validation paths

## Manual QA (Contract Examples)

Executed via manual runtime QA.
- `uvicorn` startup attempt in this sandbox failed to bind (`Operation not permitted`), so QA was executed through an in-process ASGI harness hitting real FastAPI routes end-to-end.
- Evidence bundle (local): `.qa/issue198/issue198_20260305_002451/...`
- Bundle is also zipped and attached externally to the PR as an artifact (not tracked in git).
- Initial harness run failed due to harness-side formatting/regex bug; no product code changes were required; final run PASS.

| Check | Result | Evidence |
|---|---|---|
| A Route exactness | PASS | `POST /api/candidate/session/{token}/schedule` |
| B Preconditions/security | PASS | `403 SCHEDULE_NOT_CLAIMED`; ownership mismatch; `email_verified` enforced |
| C Persistence/response | PASS | 5 windows; canonical `Z`; `schedule_locked_at` set |
| D Idempotency/email dedupe | PASS | same payload `200` no extra emails; changed payload `409` |
| E Resolve/invites enrichment | PASS | schedule fields + `currentDayWindow` present |
| F Expiry semantics | PASS | `410 INVITE_TOKEN_EXPIRED`; detail `Invite token expired` |

```bash
# 1) Claim invite
curl -X POST "http://localhost:8000/api/candidate/session/$TOKEN/claim" \
  -H "Authorization: Bearer $CANDIDATE_JWT"

# 2) Schedule
curl -X POST "http://localhost:8000/api/candidate/session/$TOKEN/schedule" \
  -H "Authorization: Bearer $CANDIDATE_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduledStartAt": "2026-03-10T13:00:00Z",
    "candidateTimezone": "America/New_York"
  }'

# 3) Resolve
curl "http://localhost:8000/api/candidate/session/$TOKEN" \
  -H "Authorization: Bearer $CANDIDATE_JWT"
```

## Risks / Rollout Notes

- `410` vs issue-text expectations: this repo consistently uses `410 Gone` for expired invite tokens; FE should branch primarily on `errorCode=INVITE_TOKEN_EXPIRED` for machine-stable handling.
- Email dispatch is best-effort after commit: schedule persistence remains authoritative even if notification delivery fails transiently (acceptable for MVP).
- Per-day overrides are guarded by `TENON_SCHEDULE_DAY_WINDOW_OVERRIDES_ENABLED`; when disabled, override payloads are rejected at schema validation.

## Demo Checklist

1. Invite candidate.
2. Candidate claims invite.
3. Candidate schedules start date/timezone.
4. Verify resolve payload exposes schedule fields plus `currentDayWindow` and schedule lock state.
5. Verify confirmation emails are emitted (Memory provider in tests captures both candidate and recruiter messages).
