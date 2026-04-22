# Phase 3 backend ship set

## Summary

This backend PR supports the Phase 3 Talent Partner golden path and the local verification bootstrap path.

It does four things:

- Makes the GitHub workflow default point to `evidence-capture.yml`.
- Makes GitHub Actions dispatch handling treat a queued run as `running` instead of a hard failure.
- Plumbs `jobId` through worker payloads so scenario-generation logs and handler context are traceable.
- Hardens candidate workspace bootstrap and local seeding so the live stack is deterministic enough to verify end to end.

## Why

Phase 3 depends on a real local stack that can bootstrap a Trial, create an empty candidate repo, provision or degrade Codespace setup safely, and survive queued GitHub Actions behavior without false failures.

The previous state was not reliable enough for founder-grade verification:

- the workflow default was not aligned with the evidence-capture path,
- queued GitHub Actions runs were treated as errors,
- worker handlers did not consistently receive the originating job id,
- candidate workspace bootstrap lacked enough actor-access and timing resilience,
- local demo seeding was not deterministic enough for repeated verification.

## Implementation Notes

### GitHub workflow and dispatch behavior

- Changed the default workflow file to `evidence-capture.yml`.
- Updated dispatch/poll handling so a queued run now returns `running` and caches that state instead of being treated as a failure.
- Added logging around observed runs and terminal-state outcomes so dispatch behavior is auditable.

### Worker and scenario-generation plumbing

- Worker runtime now injects `jobId` into handler payloads.
- Scenario-generation handler now logs start, failure, and completion with runtime/provider/model context.
- Failures are logged with sanitized error details rather than raw exception text.

### Candidate workspace bootstrap

- Workspace bootstrap now looks up the authenticated GitHub user before provisioning.
- When a username is available, the bootstrap flow adds collaborator access if needed before Codespace creation.
- Codespace provisioning now has a short retry window to absorb brief repo-readiness lag.
- If direct Codespace provisioning is not ready, the flow degrades to a `codespaces.new` URL instead of pretending bootstrap is blocked.
- Bootstrap timings are logged per phase so repo creation, collaborator access, and Codespace attempts can be traced independently.
- The seeded candidate repo remains intentionally minimal: `.devcontainer/devcontainer.json`, `.gitignore`, `.github/workflows/evidence-capture.yml`, and `README.md` with the Project Brief.

### Local bootstrap and verification support

- Added a migration bridge revision to restore the missing Alembic chain.
- `runBackend.sh` local bootstrap now:
  - sets `PYTHONPATH`,
  - runs `alembic upgrade head`,
  - runs `scripts/seed_local_talent_partners.py --reset`.
- The seed script now supports `--reset` for deterministic local reseeding.
- The seed data includes the exact verification Talent Partner account used by Phase 3.

## Test / Verification

- Backend-focused tests were added and updated for:
  - GitHub config merging and validation,
  - canonical workflow dispatch behavior,
  - queued-run `running` return behavior,
  - GitHub client helper methods,
  - worker payload handling,
  - scenario-generation failure preservation,
  - workspace bootstrap behavior,
  - local bootstrap shell behavior,
  - local trial bootstrap and seed routes.
- Local verification was performed against the real local backend stack as part of the Phase 3 workflow.

## Risks / Limitations

- Archive-style cleanup behavior is still what exists.
- The cleanup payload anomaly is documented, not hidden.
- Candidate auth-policy changes were intentionally kept out of this backend scope.
- Global scenario-generation default changes were intentionally kept out of this backend scope.
- This PR improves local bootstrap determinism, but it does not claim production parity for GitHub or Codespaces timing.
