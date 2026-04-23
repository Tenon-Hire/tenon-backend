# AI Evaluation and Jobs Integration

This document describes how winoe-report generation uses durable jobs and evaluation services.

## Entry Points

- API trigger: `POST /api/candidate_sessions/{candidate_session_id}/winoe_report/generate`
  - route: `app/evaluations/routes/evaluations_routes_evaluations_winoe_report_routes.py`
  - service: `generate_winoe_report` in `app/evaluations/services/evaluations_services_evaluations_winoe_report_api_service.py`
- API status/read: `GET /api/candidate_sessions/{candidate_session_id}/winoe_report`
  - service: `fetch_winoe_report` in the same module

## Job Enqueue Path

- Job type constant: `evaluation_run` (`EVALUATION_RUN_JOB_TYPE`).
- Payload builder: `build_evaluation_job_payload(...)`.
- Idempotency key: `evaluation_run:{basis_fingerprint}` so repeated generates on the same basis reuse the same durable job.
- Enqueue function: `enqueue_evaluation_run(...)` persists a durable `jobs` row and stores `jobId` in payload.

## Worker Processing Path

- Worker handler: `handle_evaluation_run` in `app/shared/jobs/handlers/shared_jobs_handlers_evaluation_run_handler.py`.
- Handler delegates to: `winoe_report_pipeline.process_evaluation_run_job(payload_json)`.
- Failure behavior: if pipeline returns `status=failed`, handler raises permanent job error.

## Persistence Outputs

- `evaluation_runs` stores run lifecycle, model metadata, basis fingerprint, and final report fields.
- `evaluation_day_scores` stores per-day score/rubric/evidence payloads.
- `winoe_reports` stores generated marker rows per candidate session.
- `jobs` tracks queue/runtime state and serialized payload/result/error for polling/debugging.

## Read Model Behavior

`fetch_winoe_report(...)` resolves talent_partner/company access and returns:

- `ready`: latest successful run composed into response payload; this remains visible even if a newer rerun is pending, running, or failed.
- `running`: no successful run yet but active job exists.
- `not_started`: neither run data nor active job exists.
- latest run status mapping for other terminal/non-terminal states.

## Access and Safety Controls

- Talent Partner/company ownership enforcement via candidate-session evaluation context lookup.
- Candidate session not found -> 404.
- Unauthorized company access -> 403.
- Job payload includes candidate/company/requesting user IDs for auditability.

## Operational Notes

- Evaluation jobs are asynchronous by default; clients should poll winoe-report status endpoint.
- Worker registration must include the `evaluation_run` job handler.
- Downstream evaluator and composition services are modularized under `app/evaluations/services/*` for deterministic unit testing.
