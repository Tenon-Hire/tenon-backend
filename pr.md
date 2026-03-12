# Issue #218: Store AI-eval notices + per-day toggles per simulation and expose in APIs

## Title
Persist simulation AI notice + per-day evaluation toggles, expose them in recruiter/candidate APIs, and enforce disabled-day evaluation behavior.

## TL;DR
- Added persisted simulation AI config fields: `ai_notice_version`, `ai_notice_text`, `ai_eval_enabled_by_day`.
- Added defaults and migration backfill so existing/new simulations resolve safely (`mvp1`, default notice text, all days enabled).
- Exposed AI config in recruiter simulation APIs and candidate session payloads.
- Kept simulation update behavior AI-config-focused with partial-merge semantics and no-op when `ai` is omitted.
- Enforced strict day-key/boolean validation and recruiter-only mutation boundaries.
- Evaluation/reporting now honor day toggles: disabled days are emitted as human-review-required placeholders and excluded from AI score denominator.

## Problem / Why
Issue #218 requires durable AI notice disclosure and per-day AI evaluation controls per simulation so recruiters can configure compliance behavior and candidates can consistently see AI-use notice context. Without persistence + API exposure + evaluator enforcement, the compliance/demo posture is unreliable.

## What changed
### Data model / migration
- Added simulation-level persistence fields:
  - `ai_notice_version`
  - `ai_notice_text`
  - `ai_eval_enabled_by_day`
- Added defaults:
  - notice version: `"mvp1"`
  - default AI notice text
  - day toggles default to all enabled (`"1"`..`"5"` => `true`)
- Added backfill migration for existing rows and enforced `NOT NULL`/server defaults.

### API contract
- `POST /api/simulations` and `PUT /api/simulations/{id}` accept optional `ai` payload.
- Recruiter simulation read APIs expose normalized `ai` block.
- Update path behavior is AI-config-focused:
  - omitted `ai` => no AI-config mutation
  - provided `ai` => field-level merge/update
  - provided `evalEnabledByDay` => merge by provided day keys

### Candidate session exposure
- Candidate session payload now includes:
  - `aiNoticeText`
  - `aiNoticeVersion`
  - `evalEnabledByDay`
- Candidate exposure is read-only.

### Evaluation pipeline / fit-profile reporting
- Evaluator reads per-day toggles before LLM scoring.
- If AI is disabled for a day, LLM scoring is skipped for that day.
- Disabled day is written/reported as placeholder:
  - `status: "human_review_required"`
  - `reason: "ai_eval_disabled_for_day"`
  - `score: null`
- Recruiter-visible fit-profile/reporting includes disabled-day placeholder entries.
- Overall fit score excludes disabled placeholder days from denominator.

### Validation / auth
- Strict validation for `evalEnabledByDay`:
  - object shape required
  - only day keys `"1"`..`"5"`
  - values must be booleans
  - invalid payload rejected with `422`
- Recruiter-only mutation enforced on create/update paths.
- Candidate cannot mutate AI config; candidate endpoints remain read-only.

### Observability / logging
- Logs record AI notice-version and toggle-change events.
- Logs do not include full AI notice text content.

## Detailed implementation notes
- Field names persisted on simulation:
  - `ai_notice_version`
  - `ai_notice_text`
  - `ai_eval_enabled_by_day`
- Default behavior:
  - if AI config is omitted at create, defaults are applied
  - migration backfills legacy null/blank AI values to defaults
  - post-migration rows keep AI columns non-null with server-side defaults
- Merge semantics for update (`PUT /api/simulations/{id}`):
  - omitted `ai` block is a no-op for AI config
  - provided `ai.noticeVersion` / `ai.noticeText` update only those fields
  - provided `ai.evalEnabledByDay` merges only specified day keys into stored map
- Day-key validation is strict and bounded to simulation days `1`-`5`; arbitrary keys/types are rejected (`422`).
- Candidate exposure is read-only: candidate session payload returns AI notice/toggles but no candidate mutation route can set them.
- Disabled-day placeholder behavior is recruiter-visible in evaluation outputs with `human_review_required` + `ai_eval_disabled_for_day`.
- Fit-profile response explicitly preserves `score: null` for disabled-day placeholders.

## API examples
### Simulation create/update `ai` payload
```json
{
  "ai": {
    "noticeVersion": "mvp1",
    "noticeText": "We use AI to assist in evaluation...",
    "evalEnabledByDay": {
      "1": true,
      "2": true,
      "3": true,
      "4": false,
      "5": true
    }
  }
}
```

### Recruiter simulation detail `ai` block
```json
{
  "id": 42,
  "ai": {
    "noticeVersion": "mvp1",
    "noticeText": "We use AI to assist in evaluation...",
    "evalEnabledByDay": {
      "1": true,
      "2": true,
      "3": true,
      "4": false,
      "5": true
    }
  }
}
```

### Candidate session payload
```json
{
  "candidateSessionId": 101,
  "aiNoticeText": "We use AI to help evaluate submitted work artifacts...",
  "aiNoticeVersion": "mvp1",
  "evalEnabledByDay": {
    "1": true,
    "2": true,
    "3": true,
    "4": false,
    "5": true
  }
}
```

### Disabled-day fit-profile/report entry
```json
{
  "dayIndex": 4,
  "status": "human_review_required",
  "reason": "ai_eval_disabled_for_day",
  "score": null
}
```

## Testing
- Unit/integration coverage validates:
  - simulation AI config serialization/default fallback
  - create with omitted/custom AI payload
  - AI-focused update merge behavior and omitted-`ai` no-op
  - validation failures (`422`) for invalid `evalEnabledByDay`
  - recruiter simulation read APIs exposing AI block
  - candidate session exposure of `aiNoticeText`, `aiNoticeVersion`, `evalEnabledByDay`
  - evaluation/report behavior for AI-disabled day placeholders
  - overall fit-score denominator excludes disabled days
  - logging hygiene for version/toggle change events
- Final automated validation:
  - `./precommit.sh`: PASS
  - coverage: `99.01%`
- Final manual/runtime QA:
  - verdict: PASS
  - verified on real Postgres 15 with real migration path from `202603120002` to `202603120003`
  - verified via real localhost HTTP runtime (`uvicorn`) across API/service/repository/worker behavior
- Evidence bundle:
  - `.qa/issue218/manual_qa_full_pass_20260312T140450Z`
- Final verified runtime scenarios include:
  - create with omitted AI defaults
  - create with custom AI config
  - partial update merge
  - omitted `ai` no-op
  - invalid config returns `422`
  - recruiter read APIs expose `ai`
  - candidate session exposes AI notice + toggles
  - disabled-day evaluation/report behavior
  - overall score denominator behavior
  - logging hygiene
  - auth boundary enforcement

## QA evidence
- Evidence bundle:
  - `.qa/issue218/manual_qa_full_pass_20260312T140450Z`
- Key artifacts and what they prove:
  - `QA_REPORT.md`: end-to-end QA execution summary and final PASS verdict.
  - `legacy_rows_pre_migration_null_check.txt`: legacy null/blank AI state exists pre-migration.
  - `legacy_rows_post_migration.txt`: legacy rows backfilled after migration.
  - `legacy_rows_post_default_assertions.txt`: defaults/assertions hold after backfill.
  - `schema_post_ai_columns_info_schema.txt`: AI columns present with expected nullability/default metadata.
  - `schema_post_ai_columns_pg_catalog.txt`: catalog-level confirmation of column defaults/constraints.
  - `post_migration_insert_without_ai_row.txt`: insert without explicit AI config safely receives defaults.
  - `scenario_jk_evaluation_flow.json`: disabled-day placeholder behavior and overall-score denominator checks.
  - `scenario_l_logging_hygiene.json`: version/toggle logs present without full notice text leakage.
  - `scenario_m_auth_boundary_responses.json`: recruiter/candidate/auth boundary enforcement.

## Risks / follow-ups
- No blocking risk identified for this issue scope.
- Follow-up (narrow): if simulation day ranges become dynamic beyond `1`-`5`, extend validation/default toggle map accordingly.

## Rollout / demo checklist
- Create a simulation with Day 4 AI disabled.
- Candidate sees AI notice (`aiNoticeText`/`aiNoticeVersion`) in session payload.
- Generate evaluation.
- Recruiter sees Day 4 marked human-review-only in fit-profile/report output.

## Final status
Issue #218 is complete, fully QA-verified (manual/runtime PASS), and ready for PR raise.
