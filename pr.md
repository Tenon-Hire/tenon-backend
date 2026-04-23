## 2. Summary

This branch fixes the gap where reviewer sub-agent output stayed buried in raw JSON instead of being stored as first-class report artifacts.

That mattered because Winoe Report needed structured reviewer history that could be queried, rendered, and drilled into without depending on raw evaluator payloads. It also needed those reviewer artifacts to stay aligned with the same Evidence Trail pointer contract used by the day score path.

The branch now persists reviewer sub-reports in a dedicated table, exposes them through `reviewerReports` on the Winoe Report API, and normalizes reviewer identity and evidence so the report surface can reliably drill down into Day 1 through Day 5 review output.

## 3. Scope of Implementation

- Added a first-class persisted reviewer sub-report model and repository layer for `evaluation_reviewer_reports`.
- Persisted structured reviewer fields instead of only keeping raw provider output:
  - reviewer agent key
  - day index
  - submission kind
  - score
  - dimensional scores
  - evidence citations
  - assessment text
  - strengths
  - risks
  - raw output as secondary/internal context
- Wired Winoe Report composition to surface persisted reviewer rows through `reviewerReports`.
- Normalized reviewer evidence citations through the shared Evidence Trail pointer contract so reviewer drill-down uses the same evidence semantics as day scores.
- Stabilized reviewer identities across the evaluator and composer layers:
  - `designDocReviewer`
  - `codeImplementationReviewer`
  - `demoPresentationReviewer`
  - `reflectionEssayReviewer`
- Kept Day 2 and Day 3 as separate persisted reviewer rows while mapping both to `codeImplementationReviewer`.
- Added idempotent persistence behavior so reprocessing the same run content reuses existing reviewer-report rows rather than creating duplicates.
- Cleaned up recommendation translation so internal storage can remain `lean_hire` while the Winoe Report API intentionally surfaces `mixed_signal`.
- Preserved the existing from-scratch evaluation posture and the Winoe-facing signal vocabulary on the public report surface.

## 4. Files / Surfaces Changed

### Migrations and schema

- Added the database migration for `evaluation_reviewer_reports`.
- Added the ORM model and repository exports for the new reviewer-report artifact.
- Extended the Winoe Report response schema to include `reviewerReports`.

### Repositories

- Added reviewer-report normalization, insert-or-reuse persistence, and list/query helpers.
- Added uniqueness protection on `(run_id, reviewer_agent_key, day_index)` to keep persisted reviewer rows stable.

### Evaluator runtime / completion flow

- Captured evaluator reviewer sub-agent output during run finalization.
- Persisted reviewer reports alongside day scores when a run completes.
- Kept raw provider output secondary to the structured persisted artifact.

### Composer / normalization services

- Composed `reviewerReports` from persisted rows for the ready Winoe Report payload.
- Normalized evidence pointers with the shared Evidence Trail sanitization path.
- Normalized recommendation values for the public Winoe signal vocabulary.

### Schemas / API response shape

- Added typed `reviewerReports` response objects with structured reviewer fields.
- Kept the generate and fetch endpoints stable while expanding the ready payload.

### Tests

- Added repository tests for reviewer-report persistence, queryability, and idempotency.
- Added composer tests for persisted reviewer report drill-down and recommendation translation.
- Added route tests covering generate, running, ready, failed, and auth surfaces.
- Added migration smoke coverage for the new table.

### AI config / manifest

- Kept reviewer identities stabilized through the AI prompt/config surface so the evaluator and the persisted rows use the same canonical reviewer keys.

## 5. Acceptance Criteria Mapping

- [x] Day 1-5 sub-reports persisted as structured artifacts
- [x] Each includes dimensional scores, evidence citations, assessment
- [x] Winoe Report can drill down to sub-reports

## 6. Technical Design Notes

- Persisted reviewer rows are now first-class artifacts. They are not just a copy of raw JSON, and the repository layer owns their shape, validation, and uniqueness rules.
- Raw provider output remains available only as secondary/internal context. The structured columns are the source of truth for the Winoe Report drill-down path.
- Reviewer evidence uses the shared normalized Evidence Trail pointer contract so reviewer citations and day-score citations stay consistent.
- Stable reviewer identities are canonicalized as:
  - `designDocReviewer`
  - `codeImplementationReviewer`
  - `demoPresentationReviewer`
  - `reflectionEssayReviewer`
- Day 2 and Day 3 remain separate persisted rows, but both map to `codeImplementationReviewer` in the public report surface.
- The recommendation translation is intentional:
  - internal storage can keep `lean_hire`
  - Winoe Report intentionally surfaces `mixed_signal`
- That translation is documented in the normalization layer so the API contract stays explicit rather than accidental.

## 7. QA Evidence

### Commands run

- `./scripts/local_qa_backend.sh up`
- `./qa_verifications/Database-Protocol-QA/run_db_protocol_qa.sh`
- `./qa_verifications/API-Endpoints-QA/run_api_qa.sh`
- `./qa_verifications/Service-Logic-QA/run-service-logic-qa.sh`

### Routes exercised

- `POST /api/candidate_sessions/{candidateSessionId}/winoe_report/generate`
- `GET /api/candidate_sessions/{candidateSessionId}/winoe_report`

### QA outcomes

- Database QA: `PASS`
  - Applied migrations successfully.
  - Verified the new reviewer-report table and related integrity rules.
  - Ran 15 positive checks and 1 negative check; all passed.
- API QA: `PASS`
  - `93/93` requests passed.
  - `312/312` assertions passed.
- Service-logic QA: `PASS`
  - `1583 passed` in the existing-tests step.
  - `1583 passed` in the existing-coverage step.
  - `1583 passed` in the combined-coverage step.
  - Strict validation passed with branch minimum `99`.

### Key payload evidence

- Ready report payload included `overallWinoeScore`, `confidence`, `dayScores`, `reviewerReports`, and `version`.
- Reviewer drill-down returned structured reviewer rows with stable keys such as `codeImplementationReviewer`.
- Evidence items in the ready payload included normalized `commit`, `diff`, `tests`, `transcript`, and `submission` pointers.
- Transcript evidence retained `startMs` and `endMs` bounds.
- The public recommendation surfaced `mixed_signal` for an internally stored `lean_hire` value.

### Final QA verdict

- `PASS`

## 8. Idempotency Proof

- Duplicate generate requests reused the same durable job id for the same basis fingerprint.
- The Winoe Report worker path produced exactly one durable evaluation run for the candidate session on rerun:
  - before rerun: `1` run
  - after rerun: `1` run
- Reviewer-report persistence remained stable across repeat writes in repository-level QA:
  - before rerun: `2` reviewer-report rows
  - after rerun: `2` reviewer-report rows
- No duplicate reviewer-report rows or duplicate runs were created by the rerun path.

## 9. Tests

- Focused evaluation tests were added and rerun for the reviewer-report repository, composer, jobs service, and Winoe Report route surfaces.
- Precommit checks passed in the final worker QA flow.
- Service-logic QA finished cleanly with `1583` passing tests per step and strict coverage validation passing at the branch minimum.
- API contract coverage passed with `93/93` requests and `312/312` assertions.
- Database protocol coverage passed against the migrated schema, including the reviewer-report table.

## 10. Risks / Follow-ups

- The new reviewer-report table is now part of the persisted contract, so future evaluator changes must keep the canonical reviewer keys and day-to-day mapping stable.
- If evaluator output shape expands again, the repository normalization rules will need to stay in lockstep so the structured artifact remains the source of truth.

## 11. Terminology / Pivot Compliance

- From-scratch evaluation posture is preserved.
- No precommit-baseline logic was introduced for reviewer persistence.
- No legacy reviewer shorthand is exposed in the final API surface.
- No retired terminology was added to product-facing output.

## 12. Final Result

Fixes #296
