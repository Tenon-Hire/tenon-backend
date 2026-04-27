## Title

Support contract-live Day 2/3 verification for Codespace-only candidate QA

## Summary

This backend patch stays narrow for frontend issue #194 contract-live support.

It does two things:

- Keeps the candidate day-window admin operation local/test-only, while also updating the associated day audit and workspace revocation state for the day 2/3 contract-live proof.
- Lets scenario generation treat demo mode as env-controlled, so local QA can fall back without hard-coding runtime behavior into `runBackend.sh`.

## Final Scope

In scope:

- `app/talent_partners/services/talent_partners_services_talent_partners_admin_ops_candidate_day_window_service.py`
- `app/trials/services/trials_services_trials_scenario_generation_env_service.py`
- `tests/talent_partners/services/test_talent_partners_admin_ops_set_candidate_session_day_window_updates_schedule_and_jobs_service.py`
- `tests/trials/services/test_trials_scenario_generation_env_service.py`

Out of scope:

- compare-summary behavior
- production auth behavior
- Winoe Report scoring/evaluation behavior
- hard-coded credentials
- committed prod env files
- dev-auth bypass changes
- production runtime/provider/model default changes
- migration-smoke / precommit QA-gate changes

## QA Evidence

Frontend contract-live evidence bundle:

- `winoe-frontend/qa_verifications/Contract-Live-QA/contract_live_qa_latest/artifacts/20260426T201813`
- sequence: `talent_partner-fresh,candidate-schedule,candidate-day:1,candidate-day:2,candidate-day:3,talent_partner-review`
- `trialId=1`
- `candidateSessionId=1`

Observed browser coverage:

- Day 2 reached in browser.
- Day 3 reached in browser.
- Talent Partner submissions/review page reached in browser.
- Dev-auth bypass was not used.
- Prod env files were not sourced.

## Backend Checks

```bash
python3 -m py_compile app/talent_partners/services/talent_partners_services_talent_partners_admin_ops_candidate_day_window_service.py app/trials/services/trials_services_trials_scenario_generation_env_service.py tests/talent_partners/services/test_talent_partners_admin_ops_set_candidate_session_day_window_updates_schedule_and_jobs_service.py tests/trials/services/test_trials_scenario_generation_env_service.py

poetry run pytest tests/talent_partners/services/test_talent_partners_admin_ops_set_candidate_session_day_window_updates_schedule_and_jobs_service.py -q --no-cov
# 3 passed

poetry run pytest tests/trials/services/test_trials_scenario_generation_env_service.py -q --no-cov
# 6 passed

git diff --check
# passed
```

## Changed Files

- `app/talent_partners/services/talent_partners_services_talent_partners_admin_ops_candidate_day_window_service.py`
  - local/test-only day-window control now also updates day audit and workspace revocation state for the relevant day 2/3 window
- `app/trials/services/trials_services_trials_scenario_generation_env_service.py`
  - demo-mode detection now honors env-driven flags before falling back to runtime config
- `tests/talent_partners/services/test_talent_partners_admin_ops_set_candidate_session_day_window_updates_schedule_and_jobs_service.py`
  - covers retiming existing day audits and creating/revoking the matching workspace state
- `tests/trials/services/test_trials_scenario_generation_env_service.py`
  - covers settings/env-driven demo mode and existing LLM-availability paths

## Final Confirmation

- [x] No compare-summary behavior is included in this backend diff.
- [x] No hard-coded credentials are included.
- [x] No prod env files are committed.
- [x] No dev-auth bypass changes are included.
- [x] Demo fallback remains env-controlled only.
- [x] Day-window support remains local/test-only gated.
- [x] No production runtime/provider/model defaults were changed.
- [x] Migration-smoke and precommit QA-gate changes were reverted.
- [x] Conflict marker scan found only fixture/log strings, not merge markers.

## Risk / Rollback

Risk is low if the local/test-only gates remain intact.

Rollback is to revert the four backend support files above.
