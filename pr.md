# Enforce immutable agent model and prompt snapshots per Trial for candidate fairness #297

## 1. Title

Enforce immutable agent model and prompt snapshots per Trial for candidate fairness

## 2. Summary

This change makes the Trial-level AI policy immutable so every candidate in the same Trial is evaluated against the same frozen snapshot set.

The implementation persists the snapshot before invitations, uses the persisted snapshot as the runtime source of truth, and rejects invalid or mismatched snapshot usage at protected route and evaluation time. It also records audit metadata so every evaluation run can be traced back to the exact provider, model, version, prompt version, rubric version, and snapshot fingerprint that was used.

The active snapshot contract covers exactly:

- `prestart`
- `designDocReviewer`
- `codeImplementationReviewer`
- `demoPresentationReviewer`
- `reflectionEssayReviewer`
- `winoeReport`

The retired Codespace Specializor / `codespace` agent is not part of the active fairness contract.

## 3. Problem

Before this fix, the Trial flow did not guarantee a single immutable AI policy snapshot across all candidates. That created a fairness gap because runtime agent resolution could drift from the Trial’s intended model, prompt, and rubric configuration.

This issue closes that gap by freezing the Trial snapshot ahead of invitations and making downstream evaluation and route handling fail closed on mismatch.

## 4. What Changed

- Persisted a Trial/scenario-level frozen AI policy snapshot before the invitation flow starts.
- Validated the stored snapshot contract before protected route access and again during evaluation generation.
- Rejected invalid or mismatched snapshots with `409` and preserved auditable failure metadata.
- Used the persisted frozen snapshot as the source of truth for runtime provider, model, prompt, and rubric resolution.
- Recorded audit fields for provider, model, model version, prompt version, rubric version, and snapshot digest/fingerprint.
- Persisted failed evaluation runs for invalid snapshot attempts so the rejection path remains observable in audit history.
- Excluded retired `codespace` from the active snapshot contract while allowing compatibility code paths to keep legacy configuration data isolated from the fairness contract.
- Corrected legacy stale IDs in the final runtime configuration.
- Updated the Anthropic adapter to remove the deprecated `temperature` request field.
- Kept the normal local runtime path on real mode by default for the active path.

## 5. Final Active Runtime Mapping

- Scenario generation -> `anthropic` / `claude-opus-4-7`
- Day 1 / design doc reviewer -> `anthropic` / `claude-opus-4-7`
- Day 2 / code implementation reviewer -> `openai` / `gpt-5.2-codex`
- Day 3 / code implementation reviewer -> `openai` / `gpt-5.2-codex`
- Day 4 / demo presentation reviewer -> `anthropic` / `claude-sonnet-4-6`
- Day 5 / reflection essay reviewer -> `anthropic` / `claude-sonnet-4-6`
- Winoe aggregator -> `openai` / `gpt-5.2`
- Transcription -> `openai` / `gpt-4o-transcribe`

## 6. Acceptance Criteria Checklist

- [x] Trial-level snapshot persisted before invitations
- [x] Each agent uses specified snapshot
- [x] Audit fields: model, version, prompt version, rubric version, provider
- [x] Reject evaluation on snapshot mismatch

## 7. QA / Verification

### Automated Coverage

- Focused tests and lint passed for the final changes.
- Full repo gate passed.
- Pre-commit passed.

### Manual End-to-End QA

- Verified the issue end to end for the stated scope.
- Real GitHub-backed invite flow succeeded.
- Valid active snapshot persisted and exposed the correct active agent set.
- Protected routes rejected invalid snapshots with `409`.
- Evaluation generation rejected invalid snapshots.
- Worker persisted auditable failed evaluation runs for invalid snapshot attempts.
- Restored valid snapshot path still worked after rejection cases.

### Real Provider Verification

- Anthropic Day 1 succeeded on `claude-opus-4-7`.
- OpenAI Day 2 / Day 3 succeeded on `gpt-5.2-codex`.
- OpenAI aggregator succeeded on `gpt-5.2`.

## 8. Risks / Non-Blocking Notes

- Some targeted pytest slices in this Python 3.14 environment still show a pre-existing `pytest_asyncio` teardown issue.
- This is not blocking #297 because the repo-level gate passed and the issue acceptance criteria were verified end to end.

## 9. Ready for Review

The Trial snapshot contract is now immutable, auditable, and enforced at runtime for candidate fairness.
