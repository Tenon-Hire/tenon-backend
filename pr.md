# Day 5 reflection essay with 9 AM to 9 PM local extended window (#291)

## 1. Summary

This PR makes Day 5 canonical as `reflection`, keeps the Day 5 local window at 09:00-21:00, and aligns the backend create, detail, autosave, submission, and day-close flows with that contract.

## 2. Problem

Day 5 still needed the extended local window and the correct task type. Before this change, the backend could surface Day 5 as `documentation` in some paths, and the day-close flow did not consistently propagate candidate session completion when the final Day 5 text submission was finalized from draft.

## 3. What Changed

### Day 5 contract

- Canonicalized Day 5 to `reflection` in the trial blueprint and shared task type model.
- Added a Day 5 contract helper that normalizes the trial schedule to the canonical 09:00-21:00 local override.
- Kept Days 1-4 on the existing 09:00-17:00 local window.

### Trial creation and validation

- Trial creation now enforces the Day 5 window override during build and persistence.
- The live create-path contract rejects a noncanonical Day 5 override and keeps the persisted trial row aligned with the canonical window.
- Trial detail responses now surface Day 5 as `reflection` consistently.

### Submission and day-close behavior

- Day 5 reflection payload validation now accepts `reflection` as a text task type.
- The explicit Day 5 submit path completes the candidate session when that submission is the final outstanding task.
- The day-close finalize-from-draft handler now propagates completion through the shared submission progress path for both new and existing submissions.
- Day-close finalization remains idempotent and respects the extended Day 5 cutoff.

### Backend surfaces touched

- `app/trials/constants/trials_constants_trials_blueprints_constants.py`
- `app/trials/services/trials_services_trials_creation_builder_service.py`
- `app/trials/services/trials_services_trials_creation_service.py`
- `app/trials/services/trials_services_trials_day_five_contract_service.py`
- `app/shared/types/shared_types_types_model.py`
- `app/submissions/services/submissions_services_submissions_payload_validation_service.py`
- `app/shared/jobs/handlers/shared_jobs_handlers_day_close_finalize_text_submission_handler.py`
- `app/candidates/candidate_sessions/services/candidates_candidate_sessions_services_candidates_candidate_sessions_progress_service.py`

## 4. QA

### Live create-path verification

- `POST /api/trials` returns Day 5 as `reflection`.
- The persisted trial row shows Day 5 override enabled with `09:00`-`21:00`.
- The trial detail response also shows Day 5 as `reflection`.

### End-to-end Day 5 verification

- Draft save and fetch work in the open Day 5 window.
- Closed-window draft and submit attempts are rejected.
- Explicit submit persists Day 5 reflection content and marks the candidate session complete.
- Day-close finalize-from-draft creates the submission, is idempotent, and marks the candidate session complete.

### Test coverage

- Focused regression coverage passed with `--no-cov`.
- The repository-wide coverage gate blocks narrow targeted pytest runs under the default addopts, so the focused slice was run with `--no-cov` to complete the backend verification.

### Operational note

- One QA run hit `GITHUB_UNAVAILABLE`.
- Backend verification was completed using the repo-supported claimed-session fallback.

## 5. Risks / Follow-ups

- The main remaining risk is the known GitHub invite/preprovision instability. The backend path is verified, but the claimed-session fallback should stay available until that operational issue is removed.

## 6. Ready for PR

This issue is ready for PR.
