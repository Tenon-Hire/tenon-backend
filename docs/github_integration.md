# GitHub Integration

This document describes implemented GitHub integration behavior in the backend.

## Components

- Client transport and operation modules: `app/integrations/github/client/*`
- Actions runner: `app/integrations/github/actions_runner/*`
- Artifact parsing: `app/integrations/github/artifacts/*`
- Template health checks: `app/integrations/github/template_health/*`
- Webhook handling: `app/integrations/github/webhooks/*`

## Candidate Workspace Flow

1. Candidate initializes codespace route (`POST /api/tasks/{task_id}/codespace/init`).
2. Backend provisions or resolves workspace repository metadata.
3. Candidate polls codespace status (`GET /api/tasks/{task_id}/codespace/status`).
4. Candidate triggers workflow run (`POST /api/tasks/{task_id}/run`).
5. Candidate polls run result (`GET /api/tasks/{task_id}/run/{run_id}`).
6. Candidate submits task (`POST /api/tasks/{task_id}/submit`) with persisted run/test/diff data.

## Workflow and Artifact Contract

- Workflow file configured by `WINOE_GITHUB_ACTIONS_WORKFLOW_FILE`.
- Artifact parser prefers `winoe-test-results` style artifacts and extracts normalized test summary payloads.
- Submission/workspace models persist:
  - workflow run IDs/status/conclusion/timestamps
  - commit and checkpoint SHAs
  - parsed test counts/output summary
  - diff summary metadata

## Webhook Ingestion

- Endpoint: `POST /api/github/webhooks`
- Signature header verification: `X-Hub-Signature-256`
- Delivery/event headers consumed:
  - `X-GitHub-Delivery`
  - `X-GitHub-Event`
- Current accepted processing path:
  - `workflow_run` events with `action=completed`
- Endpoint returns `202 accepted` for handled/ignored deliveries.

## Template Health Checks

- Admin static check: `GET /api/admin/templates/health?mode=static`
- Admin live run check: `POST /api/admin/templates/health/run`
- Validates repo accessibility, workflow presence, and artifact expectations.

## Required Configuration

- `WINOE_GITHUB_TOKEN`
- `WINOE_GITHUB_API_BASE`
- `WINOE_GITHUB_ORG`
- `WINOE_GITHUB_TEMPLATE_OWNER`
- `WINOE_GITHUB_ACTIONS_WORKFLOW_FILE`
- `WINOE_GITHUB_WEBHOOK_SECRET`
- `WINOE_GITHUB_WEBHOOK_MAX_BODY_BYTES`

## Operational Caveats

- Webhook processing depends on configured webhook secret; otherwise route returns service unavailable.
- Cleanup flags/settings exist for workspace retention but deletion behavior is controlled by runtime mode and cleanup job handlers.
- GitHub rate limiting should be considered for high-frequency polling scenarios.
