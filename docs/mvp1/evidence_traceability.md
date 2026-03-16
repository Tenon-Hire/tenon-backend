# MVP1 Evidence Traceability (Recruiter / Enterprise)

This document describes how MVP1 fit-profile outputs are traced to versioned inputs and stored evidence.

## 1. Evaluation run model and lifecycle

Each evaluation attempt is persisted as one `EvaluationRun` row plus per-day `EvaluationDayScore` rows.

- `EvaluationRun` stores run header and version metadata, including:
  - `scenario_version_id`
  - `model_version`
  - `prompt_version`
  - `rubric_version`
  - `day2_checkpoint_sha`
  - `day3_final_sha`
  - `cutoff_commit_sha`
  - `transcript_reference`
  - `basis_fingerprint`
  - `metadata_json` (includes `basisRefs`, `disabledDayIndexes`, and related run metadata)
- `EvaluationDayScore` stores day-level outputs:
  - `day_index`
  - `score`
  - `rubric_results_json`
  - `evidence_pointers_json`

Run-state transitions are monotonic in service logic:

- `pending -> running` or `pending -> failed`
- `running -> completed` or `running -> failed`
- `completed` / `failed` are terminal

## 2. Day-level evidence pointer structure

`evidence_pointers_json` supports structured evidence pointers. Current pipeline-generated kinds include:

- `commit` (with commit `ref`; may include URL)
- `diff` (compare reference; may include URL)
- `test` (workflow/test reference; may include URL)
- `transcript` (with `startMs` and `endMs`, plus optional excerpt)
- `reflection` (text excerpt for reflection-style prompts)

Validation enforces:

- `transcript` pointers must include non-negative `startMs` and `endMs`, and `endMs >= startMs`.
- `commit` pointers must include a non-empty `ref`.

## 3. Cutoff integrity and immutable evidence basis

For coding days (2 and 3), cutoff evidence is write-once at day close:

- `candidate_day_audits` stores:
  - `cutoff_at`
  - `cutoff_commit_sha`
  - `eval_basis_ref`
- The table is unique on (`candidate_session_id`, `day_index`) and limited to day 2/3.
- `create_day_audit_once(...)` enforces write-once semantics (returns existing row on retry/race).
- Day-close enforcement captures branch head SHA and writes cutoff audit data once.

Consumer behavior uses pinned cutoff basis:

- Submission responses and recruiter submission presenters resolve `commitSha` from cutoff when available, and expose `cutoffCommitSha` and `evalBasisRef`.
- Fit-profile generation uses day-audit cutoff SHAs first when building `day2_checkpoint_sha`, `day3_final_sha`, and run basis references.
- Run metadata stores `basisRefs`; `basis_fingerprint` hashes the complete basis payload.

Conservative interpretation: each run is a traceable snapshot of the evidence basis used at generation time. Re-runs create new `EvaluationRun` records instead of mutating prior run records.

## 4. Transcript traceability

Day 4 transcript data is persisted in `transcripts` (`text`, `segments_json`, `model_name`).

- Fit-profile evidence for transcript-based scoring uses segment windows (`startMs`, `endMs`) and transcript references.
- Recruiter-facing submission detail exposes transcript metadata and segment payloads.

## 5. Fit-profile materialization model

`fit_profiles` is a marker table (`candidate_session_id`, `generated_at`).

- Full fit-profile report content is composed from `evaluation_runs` + `evaluation_day_scores` (plus run metadata and report JSON), not from a large blob in `fit_profiles`.
- API endpoints:
  - `POST /api/candidate_sessions/{candidate_session_id}/fit_profile/generate`
  - `GET /api/candidate_sessions/{candidate_session_id}/fit_profile`

## 6. Mapping to issue tracks

- #213 Evaluation schema
  - `alembic/versions/202603110002_add_evaluation_runs_and_day_scores.py`
  - `alembic/versions/202603120001_expand_evaluation_runs_for_fit_profile.py`
  - `app/repositories/evaluations/models.py`
- #204 Cutoff enforcement
  - `alembic/versions/202603080004_add_day_audit_and_github_username.py`
  - `app/jobs/handlers/day_close_enforcement.py`
  - `app/repositories/candidate_sessions/repository_day_audits.py`
- #205 ScenarioVersion
  - `alembic/versions/202603090001_add_scenario_versions_and_locking.py`
  - `alembic/versions/202603090002_add_pending_scenario_version_and_generating_status.py`
  - `app/repositories/scenario_versions/models.py`
- #218 AI notice + per-day toggles
  - `alembic/versions/202603040001_add_simulation_context_columns.py`
  - `alembic/versions/202603120003_backfill_simulation_ai_config_defaults.py`
  - `app/repositories/simulations/simulation.py`
  - `app/schemas/simulations.py`

Additional alignment dependencies:

- #215 Media consent + retention:
  - `alembic/versions/202603150002_add_media_privacy_controls.py`
  - `app/api/routers/candidate_sessions_routes/privacy.py`
  - `app/services/media/privacy.py`
  - `app/services/media/handoff_upload.py`
- #214 Fit profile generation:
  - `app/api/routers/fit_profile.py`
  - `app/services/evaluations/fit_profile_api.py`
  - `app/services/evaluations/fit_profile_pipeline.py`
