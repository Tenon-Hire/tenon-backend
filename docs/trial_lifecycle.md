# Trial Lifecycle

This document describes implemented trial lifecycle states, transitions, and guardrails.

## Lifecycle States

Defined in trial status constants:

- `draft`
- `generating`
- `ready_for_review`
- `active_inviting`
- `terminated`

Legacy value `active` is normalized to `active_inviting`.

## Allowed Transitions

Primary transition rules (`_ALLOWED_TRANSITIONS`):

- `draft -> generating`
- `generating -> ready_for_review`
- `ready_for_review -> active_inviting`
- `active_inviting -> ready_for_review`
- `terminated -> (no forward transitions)`

Special rule:

- Any valid status can transition to `terminated` via termination flow.

## Timestamps Updated by Transition

- Entering `generating` sets `generating_at` if empty.
- Entering `ready_for_review` sets `ready_for_review_at` if empty.
- Entering `active_inviting` sets `activated_at` if empty.
- Entering `terminated` sets `terminated_at` if empty.

## API Operations

- `POST /api/trials/{trial_id}/activate`
  - Requires `confirm=true` in payload.
  - Enforces talent_partner ownership.
  - Blocks activation when `pending_scenario_version_id` exists.

- `POST /api/trials/{trial_id}/terminate`
  - Requires `confirm=true` in payload.
  - Enforces talent_partner ownership.
  - Persists termination metadata and enqueues cleanup jobs.

- Scenario routes that influence lifecycle readiness:
  - `POST /api/trials/{trial_id}/scenario/regenerate`
  - `POST /api/trials/{trial_id}/scenario/{scenario_version_id}/approve`
  - `PATCH /api/trials/{trial_id}/scenario/active`
  - `PATCH /api/trials/{trial_id}/scenario/{scenario_version_id}`

## Invite Guardrails

Invites require trial to be invitable:

- Terminated trials are rejected.
- Trials with pending scenario approvals are rejected.
- Status must be `active_inviting`.

## Error Semantics

Lifecycle/service checks use structured API errors for:

- invalid transition attempts (409)
- missing confirmation fields (400)
- pending scenario approval conflicts (409)
- non-invitable status conflicts (409)
- ownership/access violations (403/404 depending dependency path)
