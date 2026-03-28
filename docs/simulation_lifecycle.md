# Simulation Lifecycle

This document describes implemented simulation lifecycle states, transitions, and guardrails.

## Lifecycle States

Defined in simulation status constants:

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

- `POST /api/simulations/{simulation_id}/activate`
  - Requires `confirm=true` in payload.
  - Enforces recruiter ownership.
  - Blocks activation when `pending_scenario_version_id` exists.

- `POST /api/simulations/{simulation_id}/terminate`
  - Requires `confirm=true` in payload.
  - Enforces recruiter ownership.
  - Persists termination metadata and enqueues cleanup jobs.

- Scenario routes that influence lifecycle readiness:
  - `POST /api/simulations/{simulation_id}/scenario/regenerate`
  - `POST /api/simulations/{simulation_id}/scenario/{scenario_version_id}/approve`
  - `PATCH /api/simulations/{simulation_id}/scenario/active`
  - `PATCH /api/simulations/{simulation_id}/scenario/{scenario_version_id}`

## Invite Guardrails

Invites require simulation to be invitable:

- Terminated simulations are rejected.
- Simulations with pending scenario approvals are rejected.
- Status must be `active_inviting`.

## Error Semantics

Lifecycle/service checks use structured API errors for:

- invalid transition attempts (409)
- missing confirmation fields (400)
- pending scenario approval conflicts (409)
- non-invitable status conflicts (409)
- ownership/access violations (403/404 depending dependency path)
