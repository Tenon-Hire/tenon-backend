# Candidate start-date proposal flow with Talent Partner notification

## 1. Summary
Candidate schedule requests now support start-date semantics correctly.

A candidate-proposed date or datetime is normalized to the Trial's Day 1 local open time in the candidate's timezone before persistence and day-window derivation. Past-date rejection now respects candidate-local scheduling semantics. Schedule confirmation emails go to both the candidate and the Talent Partner. Trial content stays locked before Day 1 opens.

Local greenfield QA is now deterministic because `runBackend.sh` defaults local runtime to `WINOE_SCENARIO_GENERATION_RUNTIME_MODE=demo` unless explicitly overridden.

## 2. Problem / Why
Issue #288 needed the scheduling contract to match product truth: candidates propose a start date, but the backend must normalize that proposal into the Trial's Day 1 open time in the candidate's timezone before storing it or deriving day windows.

The QA blocker was separate but related to greenfield provisioning. Fresh local Trial creation could dead-letter in scenario generation unless local runtime defaulted to deterministic demo mode, which made the local QA path unreliable.

## 3. What changed

### Candidate scheduling contract / normalization
- The schedule request now accepts either a date or a datetime.
- Both inputs normalize to the Trial's Day 1 local open time in the candidate's timezone before persistence.
- Day windows are derived from that normalized Day 1 local open time.

### Candidate-local past-date validation
- Past-date rejection now compares against the normalized candidate-local schedule semantics.
- This prevents false positives from timezone mismatches when the candidate proposes a local date that is still in the future for the candidate but not as a raw UTC timestamp.

### Existing schedule persistence + email flow retained
- The schedule is persisted on the candidate session.
- Schedule confirmation emails still go to both the candidate and the Talent Partner.
- Locked schedule behavior remains idempotent for the same payload and rejects conflicting resubmits.

### Local runtime default for deterministic greenfield provisioning
- `runBackend.sh` now defaults local runtime to `WINOE_SCENARIO_GENERATION_RUNTIME_MODE=demo`.
- The default only applies in local runtime paths and remains overrideable.
- Non-local behavior is unchanged.

### Automated tests added/updated
- Route coverage now verifies date-only input normalization to Day 1 open time.
- Service coverage now verifies local past-date rejection.
- Shell coverage now verifies local greenfield defaults and the deterministic demo mode export.

## 4. Behavioral details
- Date-only and datetime inputs both normalize to Day 1 local open time.
- `scheduledStartAt`, `candidateTimezone`, `githubUsername`, `dayWindows`, and `scheduleLockedAt` remain in the schedule response.
- Locked schedule behavior remains idempotent for the same payload and rejects conflicting resubmits.
- The local-only runtime default is overrideable and does not change non-local behavior.

## 5. Manual QA evidence
Final greenfield QA succeeded with a fresh Trial created in local greenfield flow.

- Trial ID: `56`
- Scenario version ID: `41`
- Candidate session ID: `59`
- Invite token: `q6uBK_Q4TL3CKBBn5LEZ1EAI93R_Ytn2Uc8FHEkEjbM`

Live scheduling evidence:

```http
POST /api/candidate/session/{token}/schedule
```

```json
{
  "scheduledStartAt": "2026-04-20T13:00:00Z",
  "candidateTimezone": "America/New_York",
  "githubUsername": "qa288-smtp-user"
}
```

- 200 response with `candidateSessionId: 59`
- 200 response with `scheduledStartAt: 2026-04-20T13:00:00Z`
- 200 response with `candidateTimezone: America/New_York`
- 200 response with `githubUsername: qa288-smtp-user`

Timezone and day-window evidence:

- `dayWindowsCount: 5`
- First window start: `2026-04-20T13:00:00Z`
- First window end: `2026-04-20T21:00:00Z`

Email evidence from the localhost SMTP sink:

- Invite email to the candidate
- Schedule confirmation email to the candidate
- Schedule confirmation email to the Talent Partner
- Captured subjects:
  - `You're invited: Issue 288 SMTP QA Trial`
  - `Schedule confirmed: Issue 288 SMTP QA Trial`
  - `Candidate scheduled: QA Candidate 288 SMTP`

Pre-Day-1 lock evidence:

- `GET /api/candidate/session/{candidate_session_id}/current_task`
- 409 response with `errorCode: SCHEDULE_NOT_STARTED`
- 409 response with `detail: Trial has not started yet.`
- 409 response with `details.startAt: 2026-04-20T13:00:00Z`

Past-date rejection evidence:

- Scheduling payload with `2026-04-17T13:00:00Z`
- 422 response with `errorCode: SCHEDULE_START_IN_PAST`

Persistence evidence:

- `candidateTimezone: America/New_York`
- `scheduledStartAt: 2026-04-20T13:00:00+00:00`
- `scheduleLockedAt: 2026-04-18T20:46:47.727923+00:00`
- `githubUsername: qa288-smtp-user`

## 6. Automated verification
- Local migrate/bootstrap passed.
- Backend and worker started successfully.
- Local readiness checks passed.
- Focused pytest slice passed:
  `./.venv/bin/pytest -q -o addopts='' tests/scripts/test_local_qa_backend_shell.py tests/scripts/test_run_backend_bootstrap_local_shell.py tests/scripts/test_run_backend_local_defaults_shell.py tests/trials/services/test_trials_scenario_generation_env_service.py tests/trials/services/test_trials_scenario_generation_generation_service.py`
- Pre-commit checks passed.
- Final worker report showed `1735 passed`.
- Final worker report showed coverage gate passing at `96.05%`.

## 7. Acceptance criteria mapping
- Candidate proposes start date via scheduling endpoint: the schedule endpoint now accepts candidate-proposed start dates and datetimes.
- Timezone-aware day windows computed: the proposed start normalizes to the candidate timezone before day-window derivation.
- Email notification to both parties: schedule confirmation emails go to the candidate and the Talent Partner.
- No Trial content before Day 1 opens: current-task access remains locked until the scheduled Day 1 start.
- Past dates rejected: candidate-local past dates return `SCHEDULE_START_IN_PAST`.
- Schedule persisted on candidate session: the candidate session row stores the normalized schedule, timezone, and lock timestamp.

## 8. Risks / Notes
- The local runtime default is local-only and overrideable.
- Production and live scenario-generation behavior outside local defaulted environments is unchanged.
- No migration was required.

