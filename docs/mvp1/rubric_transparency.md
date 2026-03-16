# MVP1 Rubric Transparency (Recruiter / Enterprise)

This document explains the high-level rubric structure used in MVP1 fit-profile evaluation outputs.

## Day-by-day rubric overview

- Day 1: design reasoning
  - Focus: written/system reasoning quality and clarity of tradeoffs.
  - Typical evidence: reflection-style excerpts from submitted text.
- Day 2 and Day 3: code quality, correctness, and tests
  - Focus: code evidence and execution outcomes.
  - Typical evidence: commit reference, diff reference, and test summary evidence.
  - Cutoff-aware basis: day audits can pin the commit SHA used as evaluation basis.
- Day 4: communication and explanation
  - Focus: communication signals in handoff responses.
  - Typical evidence: transcript segments with `startMs` and `endMs`.
- Day 5: reflection depth
  - Focus: reflection quality in final written response.
  - Typical evidence: reflection-style excerpts from submitted text.

## Rubric versioning

Rubric criteria are versioned and traceable:

- Scenario version stores rubric metadata (`scenario_versions.rubric_version`).
- Evaluation runs store the applied rubric version (`evaluation_runs.rubric_version`).
- Fit-profile API responses include report version metadata (`report.version.rubricVersion`).

## Per-day AI toggles and human review path

AI evaluation can be enabled/disabled per day:

- Simulation config stores `ai_eval_enabled_by_day`.
- API payload shape uses `evalEnabledByDay`.
- If AI is disabled for a day, that day is marked `human_review_required` and excluded from AI scoring for that run.

## What is intentionally not published

To protect system integrity and proprietary implementation details, this document does not publish:

- Internal prompt text or prompt templates
- Full scoring heuristics/code internals beyond this high-level rubric summary
- Admin-only operational controls
