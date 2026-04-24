## Title

Materialize per-Trial Winoe and company rubric snapshots for all five days

## Summary

This PR materializes immutable rubric snapshots per `ScenarioVersion` so every candidate in the same Trial is evaluated against the same Winoe baseline and any optional company-specific rubric content.

Once snapshots exist, the pipeline consumes persisted snapshot content instead of mutable static rubric files. That freezes the evaluation inputs used by the Winoe Report and keeps Trial-level evaluation consistent over time.

## What changed

- Added the `winoe_rubric_snapshots` persistence model and migration.
- Added the `ScenarioVersion` relationship to rubric snapshots.
- Added Trial-level `company_rubric_json` attachment support.
- Added a Winoe rubric registry with explicit versions.
- Added a snapshot materialization service with idempotency.
- Materialized snapshots at the successful `ScenarioVersion` lifecycle boundary.
- Added a lock-time deterministic backstop for legacy or incomplete rows.
- Updated pipeline loading to use persisted rubric snapshot content.
- Updated Winoe Report metadata to include rubric snapshot IDs, versions, hashes, and source paths.
- Added tests covering persistence, idempotency, company rubric immutability, pipeline loading, report metadata, same-Trial reuse, fingerprint stability, and the scenario-generation failure regression.

## Acceptance Criteria Coverage

1. **Winoe rubrics versioned and referenced by `ScenarioVersion`**

   The new `winoe_rubric_snapshots` table stores versioned baseline rubric material and is linked to `ScenarioVersion`. The registry carries explicit rubric versions, and snapshot materialization occurs at the successful `ScenarioVersion` lifecycle boundary so the frozen snapshot set is tied to that version, not to mutable source files.

2. **Company-specific rubrics attachable per Trial**

   `Trial.company_rubric_json` now carries optional company-specific rubric content. Company snapshots are materialized in the Trial scope, validated, and treated as immutable after materialization so the same Trial cannot drift between candidates.

3. **Version IDs in Winoe Report metadata**

   `report.version.rubricSnapshots` now includes the full snapshot metadata needed for auditability:

   - `snapshotId`
   - `scenarioVersionId`
   - `rubricScope`
   - `rubricKind`
   - `rubricKey`
   - `rubricVersion`
   - `contentHash`
   - `sourcePath`

4. **Pipeline loads correct versions**

   The effective AI policy snapshot now persists `resolvedRubricMd`, and the evaluator bundle consumes that persisted snapshot content. This ensures the pipeline uses the exact rubric versions that were materialized for the Trial instead of rereading static files.

## QA Evidence

Manual QA from Iteration 6:

- `./runBackend.sh migrate` passed.
- Schema verified:
  - `winoe_rubric_snapshots`
  - FK to `scenario_versions`
  - uniqueness constraint on `(scenario_version_id, scope, rubric_kind, rubric_key, rubric_version)`
  - `trials.company_rubric_json`
- ScenarioVersion snapshot evidence:
  - live `scenario_version_id = 7`
  - 5 baseline snapshots
  - snapshot IDs `[1, 2, 3, 4, 5]`
- Idempotency:
  - before first materialization: `0`
  - after first: `5`
  - after second: `5`
  - IDs stable: `[1, 2, 3, 4, 5]`
- Company rubric immutability:
  - company `scenario_version_id = 8`
  - company snapshot `id = 7`
  - original hash: `a9fe9259f952749e8bf470065aa56e6174eb6ec3673f7bc276b798554f5bf80b`
  - edited hash: `e0684b38150aca57fa0a46e1cf47d19234b05d3e9777171c116f49febf2885c8`
  - persisted snapshot hash stayed unchanged: `a9fe9259f952749e8bf470065aa56e6174eb6ec3673f7bc276b798554f5bf80b`
- Pipeline loading:
  - `_read_text_file` patched to raise if static rubrics were reread
  - report pipeline still completed for candidate sessions `7` and `8`
  - effective bundle contained persisted `resolvedRubricMd`
  - bundle snapshot IDs `[1, 2, 3, 4, 5]`
- Winoe Report metadata:
  - `fetch_winoe_report` returned `status: ready`
  - metadata included `scenarioVersionId: 7`
  - `rubricSnapshots` had 5 entries with required snapshot/version/hash/source fields
- Same-Trial reuse:
  - candidate sessions `7` and `8`
  - shared `scenario_version_id = 7`
  - both used snapshot IDs `[1, 2, 3, 4, 5]`
- Scenario generation failure regression:
  - focused tests passed functionally
  - job failure/dead-letter behavior intact
  - Trial remains `generating`
  - retry still works

## Automated Checks

- `./precommit.sh` passed
- `1843 passed`
- coverage: `96.04%`
- `./runBackend.sh migrate` passed
- forbidden terminology scan:
  - newly introduced forbidden terms: `0`
  - existing unrelated legacy matches remain outside the scope

## Risks / Notes

- Local QA rows for Trial and candidate test data remained in the local database because cleanup hit FK/check-constraint edges. This is local-only residue, not a code or migration issue.
- Pipeline QA used a fake evaluator at the final scoring step to avoid external AI/provider dependence, while still exercising persisted snapshot loading and report metadata paths.
- Existing unrelated legacy terminology remains in older repo areas and was not broadened by this PR.

## Final Checklist

- [x] Winoe baseline rubrics snapshotted per `ScenarioVersion`
- [x] Company rubric attachment supported
- [x] Snapshot materialization is idempotent
- [x] Same Trial candidates reuse same rubric snapshots
- [x] Evaluation pipeline consumes persisted snapshot content
- [x] Winoe Report metadata includes snapshot/version/hash identifiers
- [x] Scenario generation failure behavior preserved
- [x] `./precommit.sh` passes

Fixes #299