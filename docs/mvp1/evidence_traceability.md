# MVP1 Evidence Traceability (Talent Partner / Enterprise)

This document describes how MVP1 winoe-report outputs are traced to versioned inputs and stored evidence.

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

- Submission responses and talent_partner submission presenters resolve `commitSha` from cutoff when available, and expose `cutoffCommitSha` and `evalBasisRef`.
- Winoe Report generation uses day-audit cutoff SHAs first when building `day2_checkpoint_sha`, `day3_final_sha`, and run basis references.
- Run metadata stores `basisRefs`; `basis_fingerprint` hashes the complete basis payload.

Conservative interpretation: each run is a traceable snapshot of the evidence basis used at generation time. Re-runs create new `EvaluationRun` records instead of mutating prior run records.

## 4. Transcript traceability

Day 4 transcript data is persisted in `transcripts` (`text`, `segments_json`, `model_name`).

- Winoe Report evidence for transcript-based scoring uses segment windows (`startMs`, `endMs`) and transcript references.
- Talent Partner-facing submission detail exposes transcript metadata and segment payloads.

## 5. Winoe Report materialization model

`winoe_reports` is a marker table (`candidate_session_id`, `generated_at`).

- Full winoe-report report content is composed from `evaluation_runs` + `evaluation_day_scores` (plus run metadata and report JSON), not from a large blob in `winoe_reports`.
- API endpoints:
  - `POST /api/candidate_sessions/{candidate_session_id}/winoe_report/generate`
  - `GET /api/candidate_sessions/{candidate_session_id}/winoe_report`

## 6. Mapping to issue tracks

- #213 Evaluation schema
  - `alembic/versions/202603110002_add_evaluation_runs_and_day_scores.py`
  - `alembic/versions/202603120001_expand_evaluation_runs_for_winoe_report.py`
  - `app/evaluations/repositories/evaluations_repositories_evaluations_core_model.py`
- #204 Cutoff enforcement
  - `alembic/versions/202603080004_add_day_audit_and_github_username.py`
  - `app/shared/jobs/handlers/shared_jobs_handlers_day_close_enforcement_handler.py`
  - `app/candidates/candidate_sessions/repositories/candidates_candidate_sessions_repositories_candidates_candidate_sessions_day_audits_repository.py`
- #205 ScenarioVersion
  - `alembic/versions/202603090001_add_scenario_versions_and_locking.py`
  - `alembic/versions/202603090002_add_pending_scenario_version_and_generating_status.py`
  - `app/trials/repositories/scenario_versions/trials_repositories_scenario_versions_trials_scenario_versions_model.py`
- #218 AI notice + per-day toggles
  - `alembic/versions/202603040001_add_trial_context_columns.py`
  - `alembic/versions/202603120003_backfill_trial_ai_config_defaults.py`
  - `app/trials/repositories/trials_repositories_trials_trial_model.py`
  - `app/trials/schemas/trials_schemas_trials_core_schema.py`

Additional alignment dependencies:

- #215 Media consent + retention:
  - `alembic/versions/202603150002_add_media_privacy_controls.py`
  - `app/candidates/routes/candidate_sessions_routes/candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_privacy_routes.py`
  - `app/media/services/media_services_media_privacy_service.py`
  - `app/media/services/media_services_media_handoff_upload_service.py`
- #214 Winoe Report generation:
  - `app/evaluations/routes/evaluations_routes_evaluations_winoe_report_routes.py`
  - `app/evaluations/services/evaluations_services_evaluations_winoe_report_api_service.py`
  - `app/evaluations/services/evaluations_services_evaluations_winoe_report_pipeline_service.py`
