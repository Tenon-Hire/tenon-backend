# Docs: MVP1 Bias-Audit Readiness Pack (Rubric Transparency + Evidence Traceability + Disclosure Templates) (#220)

## TL;DR
- Adds a four-document MVP1 docs pack under `docs/mvp1/` for responsible AI demo/readiness conversations.
- Covers candidate disclosure, evidence traceability, rubric transparency, and internal operator controls.
- Wording is aligned to implemented backend models/routes/config keys and avoids speculative claims.
- Explicitly preserves human decision boundaries: AI assists evaluation; people make final hiring decisions.
- Keeps sensitive implementation details private (no proprietary prompt publication).

## Why
MVP1 includes AI-assisted evaluation, so demo and enterprise conversations need clear, conservative documentation for:
- Rubric transparency (what is evaluated across days 1-5).
- Evidence traceability (what evidence is stored and how runs are versioned).
- Candidate disclosure (what AI does, what humans do, what is recorded).
- Operator fairness/ops controls (pre-invite checks, cutoff controls, consent checks, rerun triggers, audit hygiene).

This pack improves trust without over-claiming fairness guarantees or compliance certification, and stays grounded in current backend behavior.

## What Changed
### `docs/mvp1/evaluation_disclosure.md`
- Adds candidate-facing plain-language disclosure for AI-assisted evaluation and human oversight.
- Documents day-level AI toggles and API-facing fields (`aiNoticeText`, `aiNoticeVersion`, `evalEnabledByDay`).
- Documents persisted notice/consent metadata (`ai_notice_version`, `ai_notice_text`, `ai_eval_enabled_by_day`, consent fields).
- States that AI does not make final hiring decisions and avoids bias/compliance automation claims.

### `docs/mvp1/evidence_traceability.md`
- Documents `EvaluationRun` and `EvaluationDayScore` storage model, lifecycle, and per-day evidence pointers.
- Describes pointer kinds and constraints (`commit`, `diff`, `test`, `transcript` with `startMs`/`endMs`, `reflection`).
- Explains cutoff integrity and immutable basis behavior (day-audit cutoff SHA capture, pinned basis refs, run fingerprinting, reruns as new records).
- Maps implementation to issue-linked migrations/models/routes for #213, #204, #205, #218, plus #215 and #214 alignment.

### `docs/mvp1/rubric_transparency.md`
- Provides high-level day-by-day rubric overview:
- Day 1 design reasoning.
- Day 2/3 code quality, correctness, tests.
- Day 4 communication/explanation.
- Day 5 reflection depth.
- Explains rubric versioning across scenario versions, evaluation runs, and fit-profile response metadata.
- Documents per-day AI disable behavior (`human_review_required`) and keeps proprietary prompt details undisclosed.

### `docs/mvp1/operator_checklist.md`
- Adds internal checklist for pre-invite controls, cutoff basis verification, and day-4 consent/media controls.
- Includes rerun triggers after scenario/cutoff changes and confirms latest fit-profile run usage.
- Adds manual override/audit controls to ensure operational traceability for admin/demo actions.

## Implementation Notes / Alignment
- The pack is aligned to implemented backend naming and behavior, including models, migrations, service logic, and API payload fields.
- Explicit issue alignment:
- #213 (evaluation schema and fit-profile run/day-score model)
- #204 (cutoff enforcement and day-audit write-once capture)
- #205 (scenario versioning)
- #218 (AI notice + per-day toggles)
- #215 (media consent + retention controls)
- #214 (fit-profile generation endpoints/pipeline)
- Conservative boundaries are explicit:
- No fairness-elimination or compliance-certification claims.
- No proprietary prompt/template disclosure.
- Final hiring decisions remain with people.

## Testing / Validation
Validation was performed with repository truth review plus shell sanity checks (manual, command-backed):
- Model/field alignment checks via `rg`:
- `EvaluationRun` / `EvaluationDayScore`, version fields, and run metadata in `app/repositories/evaluations/models.py`.
- Cutoff audit fields and write-once flow in `app/repositories/candidate_sessions/*` and `app/jobs/handlers/day_close_enforcement.py`.
- AI notice/toggle fields and API schema aliases in simulation/privacy routes and schemas.
- Fit-profile route/service presence for generate/fetch endpoints.
- Migration alignment checks via `ls alembic/versions | rg ...` for issue-linked migration IDs.
- Required-concept checks across `docs/mvp1/*.md` via `rg` (`ai_notice_version`, `evalEnabledByDay`, `human_review_required`, `startMs/endMs`, `rubric_version`, `cutoff_commit_sha`, `basis_fingerprint`).
- Prohibited-phrase sanity grep over docs (to catch accidental over-claims).
- Tabs/trailing-whitespace checks via `rg` over `docs/mvp1/*.md` and `pr.md`.
- Diff-scope check via `git diff --name-only` for this iteration.

Tooling note:
- `pre-commit` and `markdownlint` are not installed in this sandbox (`command not found`), so validation here is manual + grep/sanity checks.

## Risks / Limitations
- “Final hiring decisions are made by people” is a policy/process boundary and documentation statement; this service is not itself a full hiring-decision engine.
- “No manual overrides without audit entries” is primarily an operational control; out-of-band manual data edits are process-governed, not absolutely prevented by the docs alone.

## Rollout / Demo Notes
- Use `evaluation_disclosure.md` in candidate-facing AI usage explanations.
- Use `evidence_traceability.md` to explain evidence lineage, versioning, and cutoff integrity.
- Use `rubric_transparency.md` for day-by-day rubric framing without exposing prompts.
- Use `operator_checklist.md` as the internal pre-demo/pre-review runbook for scenario/toggle/cutoff/consent/audit checks.

## Status
Ready for PR raise.
