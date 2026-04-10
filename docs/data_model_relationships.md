# Data Model Relationships

This document summarizes the core relational structure from SQLAlchemy metadata (`app/shared/database/shared_database_models_model.py`).

## Core Entity Graph

- `companies`
  - 1:N `users`
  - 1:N `trials`
  - 1:N `jobs`
- `users`
  - 1:N `trials` (`created_by`, `terminated_by_talent partner_id`)
  - 1:N `scenario_edit_audit`
  - optional link from `candidate_sessions.candidate_user_id`
- `trials`
  - N:1 `companies`
  - 1:N `tasks`
  - 1:N `candidate_sessions`
  - 1:N `scenario_versions`
  - optional FK to active/pending scenario versions
- `scenario_versions`
  - N:1 `trials`
  - 1:N `candidate_sessions`
  - 1:N `evaluation_runs`
  - 1:N `precommit_bundles`
  - 1:N `scenario_edit_audit`
- `candidate_sessions`
  - N:1 `trials`
  - N:1 `scenario_versions`
  - optional N:1 `users`
  - 1:N `submissions`
  - 1:N `task_drafts`
  - 1:N `workspaces` and `workspace_groups`
  - 1:N `candidate_day_audits`
  - 1:N `evaluation_runs`
  - 1:N `winoe_reports`
  - optional N:1 from `jobs`
- `tasks`
  - N:1 `trials`
  - 1:N `submissions`
  - 1:N `task_drafts`
  - 1:N `recording_assets`
  - 1:N `workspaces`
- `submissions`
  - N:1 `candidate_sessions`
  - N:1 `tasks`
  - optional N:1 `recording_assets`
  - optional 1:N from `task_drafts.finalized_submission_id`
- `recording_assets`
  - N:1 `candidate_sessions`
  - N:1 `tasks`
  - 1:1/N `transcripts`
  - optional 1:N from `submissions.recording_id`
- `evaluation_runs`
  - N:1 `candidate_sessions`
  - N:1 `scenario_versions`
  - 1:N `evaluation_day_scores`
- `jobs`
  - N:1 `companies`
  - optional N:1 `candidate_sessions`

## Workspace Subgraph

- `workspace_groups`
  - N:1 `candidate_sessions`
  - 1:N `workspaces`
- `workspaces`
  - optional N:1 `workspace_groups`
  - N:1 `candidate_sessions`
  - N:1 `tasks`

## Evaluation / Reporting Subgraph

- `evaluation_runs` is the canonical run-level record for winoe report generation.
- `evaluation_day_scores` stores day-level rubric/evidence snapshots per run.
- `winoe_reports` tracks generated profile marker timestamps per candidate session.

## Data Integrity Patterns

- Lifecycle and status constraints are enforced in model/service layers (for example trial status transitions and invite gating).
- Candidate ownership and company-scoped access checks are enforced at service boundaries before repository mutations.
- Job processing persists payload/result/error metadata on durable job rows to support retry/debug workflows.
