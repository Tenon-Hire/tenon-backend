## 1. Title

Stabilize Winoe Report generation, Evidence Trail integrity, and duplicate job prevention for #295

## 2. Problem

Winoe Report had three reliability issues on the active Winoe-facing path:

- duplicate jobs and duplicate active work
- hollow scored output, including empty rubric breakdowns and Evidence Trail loss risk
- Day 4 being scored from failed transcript state

The read path also needed tightening:

- the active report contract still exposed determinative recommendation language
- the ready report needed to remain visible while a newer rerun was running or had failed

## 3. Root Causes Fixed

- evaluation job idempotency was keyed off per-request uniqueness instead of a stable evaluation basis
- run reuse and status handling did not fully prevent duplicate active work
- aggregation and composition could lose reviewer day truth during report assembly
- finalization tolerated hollow scored-day persistence
- the active report contract still surfaced deterministic hire/no_hire-style labels
- Day 4 needed strict non-scoring behavior whenever transcript state was not ready

## 4. What Changed

### API / orchestration

- the generate path now computes a basis fingerprint and reuses the same durable job for unchanged basis
- the fetch path keeps the latest successful ready Winoe Report visible even if a newer rerun is running or failed

### Evaluation pipeline

- run state logic now reuses existing terminal and same-basis runs correctly
- changed-basis reruns create a new durable job/run
- failed transcript state does not produce a Day 4 score

### Report integrity

- scored days now persist non-empty rubric breakdowns and evidence
- reviewer day evidence remains authoritative and is not clobbered by aggregation
- the final report preserves Evidence Trail payloads for scored days

### Recommendation / output contract

- the Winoe-facing report output now uses non-determinative signal labels:
  - `strong_signal`
  - `positive_signal`
  - `mixed_signal`
  - `limited_signal`
- legacy storage compatibility remains tolerated internally where needed, while the active API/report surface stays signal-based

### Tests

- restored and added coverage for:
  - same-basis idempotency
  - changed-basis reruns
  - worker re-execution and run reuse behavior
  - read-path stability
  - Day 4 failed-transcript gating
  - provider and recommendation contract updates

## 5. Scope Note About Persona Governance

- #295 now satisfies the non-determinative recommendation/output requirement and evidence-first report behavior on the active Winoe-facing path.
- Full `SOUL.md`-based persona governance is not claimed in this PR and remains tracked separately in #298.

## 6. QA Evidence

- local runtime was started with the worker
- duplicate generate on unchanged basis returned the same `jobId`
- unchanged-basis path produced one active job/run
- the ready payload contained `overallWinoeScore`, populated day scores, rubric breakdowns, and evidence pointers
- the failed transcript case returned Day 4 as non-scored / `human_review_required`
- a valid changed-basis rerun created a different `jobId` and completed successfully
- the ready payload remained visible even when a newer rerun was running or failed
- focused tests passed
- pre-commit checks and the full suite passed

## 7. Risks / Follow-ups

- #298 for direct `SOUL.md` persona governance and prompt wiring
- separate repo/setup follow-up for `bootstrap-local` and Alembic multi-head hygiene if needed

## 8. Final Result

Fixes #295
