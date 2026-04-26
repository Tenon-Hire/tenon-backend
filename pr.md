# PR: Update Day 2/3 Code Implementation Reviewer for from-scratch evaluation

## Summary

This PR updates the Day 2/3 Code Implementation Reviewer path for the v4 from-scratch Tech Trial model. The reviewer now evaluates the candidate’s complete repository and development process instead of treating Days 2/3 as a diff against pre-existing code.

The Day 2/3 rubric now scores from-scratch implementation work across project scaffolding, architecture, code quality, testing discipline, development process, documentation/handoff readiness, and requirements coverage. The reviewer prompt now receives structured repository/process evidence, including populated commit history, file creation timeline, and test coverage progression when persisted evidence exists.

## What changed

- Rewrote `app/ai/prompt_assets/v1/winoe-day-2&3-rubric.md` for from-scratch Tech Trial evaluation.
- Added scored rubric dimensions:
  - Project scaffolding quality — 18 points
  - Architectural coherence — 18 points
  - Code quality and maintainability — 17 points
  - Testing discipline — 15 points
  - Development process and commit history — 12 points
  - Documentation and handoff readiness — 10 points
  - Requirements coverage and product completeness — 10 points
- Added explicit rubric guidance that:
  - the complete repository is the candidate’s work
  - there is no pre-existing application code to compare against
  - evaluation is tech-stack-agnostic
  - AI coding assistants are allowed and not penalized by themselves
  - AI-bulk-generation concerns must be evidence-backed
- Added `CodeImplementationEvidenceContext` to the evaluator input bundle.
- Threaded `reviewContext.codeImplementationEvidence` into the live Day 2/3 reviewer payload.
- Integrated with the #296 artifact-parse path through persisted `Submission.test_output` evidence artifacts.
- Populated reviewer evidence from persisted Day 2/3 artifacts:
  - repository snapshot/reference
  - commit history
  - file creation timeline
  - test coverage progression
  - dependency metadata
  - documentation evolution
- Added honest evidence-status semantics:
  - `available:` when persisted evidence exists
  - `partial:` when repo identity exists but deeper snapshot artifacts are missing
  - `unavailable:` when evidence is truly absent
- Fixed report finalization validation so provider results with empty evidence arrays do not dead-letter the full evaluation run when scores and rubric breakdown are valid.
- Added regression tests for rubric content, prompt rendering, evidence serialization, malformed evidence parsing, repository status semantics, and real route/worker completion behavior.

## #296 integration

#296 has landed, so this PR now fully wires #318 into the persisted evidence path instead of leaving evidence fields as prompt-only expectations.

The Day 2/3 evidence builder hydrates `CodeImplementationEvidenceContext` from persisted submission evidence produced by the GitHub workflow artifact parse path:

- `submission.test_output.summary.evidenceArtifacts.commitMetadata` → `commitHistory`
- `submission.test_output.summary.evidenceArtifacts.fileCreationTimeline` → `fileCreationTimeline`
- `submission.test_output.summary.testResults` + `coveragePath` → `testCoverageProgression`
- `submission.test_output.summary.evidenceArtifacts.dependencyManifests` → `dependencyMetadata`
- commit entries touching `README` or `docs/` paths → `documentationEvolution`

This means the Code Implementation Reviewer now receives actual populated Day 2/3 repository/process evidence when it exists, not just empty placeholder fields.

## Evidence semantics

The evidence contract is intentionally conservative:

- If persisted evidence exists, the reviewer payload marks the field `available:`.
- If only repository identity exists, repository snapshot status is `partial:`.
- If evidence is missing, the field remains empty and status is explicit `unavailable:`.
- The reviewer prompt instructs the model not to infer process quality when commit history, file creation timeline, or test coverage progression are unavailable.

This preserves Winoe AI’s evidence-first trust bar and prevents overclaiming.

## Acceptance criteria

- [x] `winoe-day-2&3-rubric.md` updated with from-scratch evaluation dimensions.
- [x] No references to `precommit baseline`, `delta from precommit`, or `Specializor` in the Day 2/3 rubric.
- [x] Project scaffolding quality is a scored dimension weighted 18 points.
- [x] Development process / commit history analysis is a scored dimension weighted 12 points.
- [x] Rubric is tech-stack-agnostic and does not penalize framework/language choice by itself.
- [x] Rubric explicitly states AI tool usage is allowed and not penalized by itself.
- [x] Rubric notes bulk AI generation without engineering judgment only when evidence supports it.
- [x] Code Implementation Reviewer Sub-Agent prompt path uses the updated from-scratch rubric.
- [x] Reviewer receives structured full repository/process evidence.
- [x] Reviewer receives populated commit history, file creation timeline, and test coverage progression when persisted #296 evidence exists.
- [x] Missing/partial evidence is marked honestly and does not cause the reviewer to overclaim.

## QA evidence

### Focused tests

Passed:

```bash
poetry run pytest --no-cov -q tests/evaluations/services/test_evaluations_evaluator_runner_service.py tests/evaluations/services/test_evaluations_winoe_report_pipeline_rubric_snapshots_service.py tests/ai/test_ai_prompt_pack_code_implementation_reviewer_service.py
```

Passed:

```bash
poetry run pytest --no-cov -q tests/evaluations/routes/test_evaluations_winoe_report_api_worker_completion_returns_ready_and_evidence_routes.py
```

Passed:

```bash
poetry run pytest --no-cov -q tests/ai/test_ai_prompt_pack_soul_service.py tests/ai/test_ai_prompt_pack_code_implementation_reviewer_service.py tests/evaluations/services/test_evaluations_winoe_rubric_snapshots_service.py
```

### Full test suite

Passed:

```bash
poetry run pytest -q
```

Result:

```text
1876 passed, 13 warnings
Required test coverage of 96% reached.
Total coverage: 96.03%
```

### Compile check

Passed:

```bash
poetry run python -m compileall app/evaluations/services/evaluations_services_evaluations_winoe_report_pipeline_day_inputs_service.py tests/evaluations/services/test_evaluations_winoe_report_pipeline_rubric_snapshots_service.py tests/evaluations/services/test_evaluations_evaluator_runner_service.py
```

### Terminology checks

Passed:

```bash
rg -n "precommit baseline|delta from precommit|Specializor" app/ai/prompt_assets/v1/winoe-day-2\&3-rubric.md tests/ai/test_ai_prompt_pack_code_implementation_reviewer_service.py
```

Passed:

```bash
rg -n "template catalog|Fit Profile|Fit Score|simulation|recruiter|Tenon" app/ai/prompt_assets/v1/winoe-day-2\&3-rubric.md
```

### Pre-commit

`pre-commit` was unavailable in the local environment, so it was not claimed as a pass.

## Real end-to-end runtime QA

Real local backend + worker QA passed.

* Backend PID: `22463`
* Worker PID: `22959`
* Health check:

```bash
curl -sS http://127.0.0.1:8000/health
```

Response:

```json
{"status":"ok"}
```

Triggered Winoe Report generation through the real API:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/candidate_sessions/6/winoe_report/generate \
  -H 'x-dev-user-email: winoe-report-qa-iteration8b@test.com'
```

Response:

```json
{"jobId":"053c8a38-93b6-4ba9-bd26-d3f941ffaf0d","status":"queued"}
```

Final report fetch:

```bash
curl -sS http://127.0.0.1:8000/api/candidate_sessions/6/winoe_report \
  -H 'x-dev-user-email: winoe-report-qa-iteration8b@test.com'
```

Result:

* report status: `ready`
* evaluation run ID: `4`
* evaluation run status: `completed`
* job ID: `053c8a38-93b6-4ba9-bd26-d3f941ffaf0d`
* report score: `0.5759`

## Runtime payload proof

For the populated Day 2/3 evidence case, the live reviewer payload included:

```json
{
  "dayIndex": 2,
  "reviewContext": {
    "instructions": "Use codeImplementationEvidence as primary evidence for Days 2 and 3. If commit history, file creation timeline, or test coverage progression are unavailable, say so explicitly and do not infer process quality.",
    "codeImplementationEvidence": {
      "repositoryReference": "winoe-ai/report-qa-repo",
      "commitHistoryCount": 4,
      "fileCreationTimelineCount": 8,
      "testCoverageProgressionCount": 2,
      "evidenceStatus": {
        "repository_snapshot": "available: derived from day 2/3 repository and submission evidence",
        "commit_history": "available: derived from persisted submission.test_output summary evidenceArtifacts.commitMetadata",
        "file_creation_timeline": "available: derived from persisted submission.test_output summary evidenceArtifacts.fileCreationTimeline",
        "test_coverage_progression": "available: derived from persisted submission.test_output summary evidenceArtifacts.testResults and coveragePath"
      }
    }
  }
}
```

For the repository-reference-only case, the payload correctly distinguishes partial evidence:

```json
{
  "candidateSessionId": 7,
  "repositoryReference": "winoe-ai/partial-repo",
  "repositorySnapshotStatus": "partial: repository reference available; persisted repository snapshot artifacts not found for day 2/3 evidence",
  "commitHistoryCount": 0,
  "fileCreationTimelineCount": 0,
  "testCoverageProgressionCount": 0,
  "commitHistoryStatus": "unavailable: persisted submission.test_output summary evidenceArtifacts.commitMetadata not found for day 2/3 evidence",
  "fileCreationTimelineStatus": "unavailable: persisted submission.test_output summary evidenceArtifacts.fileCreationTimeline not found for day 2/3 evidence",
  "testCoverageProgressionStatus": "unavailable: persisted submission.test_output summary evidenceArtifacts.testResults coveragePath not found for day 2/3 evidence"
}
```

## Notes / risks

* Local QA used deterministic test runtime snapshots to exercise the full backend + worker path without external LLM flakiness.
* Evidence parsing now uses persisted `Submission.test_output` artifact summaries as the current #296-backed source of truth.
* If a future evidence persistence schema introduces dedicated artifact tables for commit/file/coverage data, this builder should get a small adapter layer, not a redesign.

Fixes #318