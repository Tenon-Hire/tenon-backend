# P0 AI pipeline: generate from-scratch project briefs instead of codespace specifications #317

## Title
P0 AI pipeline: generate from-scratch project briefs instead of codespace specifications #317

## TL;DR
- Prestart now generates a from-scratch project brief plus rubric.
- Trial detail / preview exposes `projectBriefMd`.
- Candidate repo bootstrap uses the canonical project brief as `README.md`.
- The canonical contract no longer emits `codespaceSpecJson`.

## Problem
Winoe v4 pivots trials to from-scratch candidate builds in empty repos. That removes the old template-specialization path and makes codespace-spec output the wrong artifact for this stage of the product.

Before this change, Prestart was still oriented around a future specializer agent and produced codespace instructions instead of a candidate-facing project brief. For v4, Prestart needed to generate a buildable project brief that gives the candidate enough business context, requirements, constraints, and deliverables to start from nothing in Days 2-3.

## What changed
- Updated the Prestart brain document to describe from-scratch project brief generation.
- Updated the AI output / schema contract to produce `project_brief_md` and rubric output, without codespace-spec fields.
- Updated the scenario generation pipeline to build project brief markdown for the candidate repo README.
- Added a centralized canonical project-brief normalization helper so preview, bootstrap, and downstream consumers all resolve the same brief.
- Updated trial detail / preview serialization to return `projectBriefMd`.
- Updated README/bootstrap sourcing so provisioned candidate repos are seeded from the canonical project brief.
- Added and updated focused tests around brief generation, preview serialization, and bootstrap seeding.

## Decisions / implementation notes
- `project_brief_md` is the canonical exposed field now.
- Legacy compatibility is preserved through one shared normalization helper.
- No database migration was introduced in this issue.
- `preferred_language_framework` is treated as context-only, not binding.

## QA / test plan
Automated:
- `bash precommit.sh`
- Result: `1702 passed, 13 warnings`
- Coverage gate: `96.16%`
- Coverage report line: `TOTAL 18520 711 96%`

Manual QA:
- Verified the local end-to-end scenario flow with the demo runtime mode: `WINOE_SCENARIO_GENERATION_RUNTIME_MODE=demo`.
- Create trial.
- Scenario generation completes.
- Preview / detail returns `projectBriefMd`.
- Approve scenario.
- Activate trial.
- Invite candidate.
- Candidate repo README matches the canonical project brief content.

Concrete QA findings:
- No blocking defects found.
- The generated project brief stayed tech-stack-agnostic.
- `preferred_language_framework` remained optional context only.
- `codespaceSpecJson` was absent from the updated trial detail payload.

## Acceptance criteria mapping
- Brain document updated for from-scratch project brief generation -> updated `winoe-prestart-background-information-creator-brain.md`.
- Prestart output includes project brief and evaluation rubric -> AI output contract now emits `project_brief_md` and rubric data.
- Prestart output does not include codespace-specializer output -> canonical contract no longer emits `codespaceSpecJson`.
- Generated project brief describes a system buildable from scratch in 2 days -> scenario generation now frames the trial as an empty-repo build with a two-day implementation window.
- Project brief is tech-stack-agnostic -> brief generation avoids prescribing framework, language, or database.
- `preferred_language_framework` is context only -> helper includes it as optional Talent Partner context, not a requirement.
- Generated project brief stored as `README.md` content -> repo bootstrap seeds the README from the canonical brief.
- Scenario generation job succeeds end to end with new brief format -> scenario generation flow passed and detail/bootstrap paths consumed the new brief.
- Talent Partner can preview the project brief before approving -> trial detail / preview serializes `projectBriefMd`.

## Non-blocking follow-ups
- Local QA used `WINOE_SCENARIO_GENERATION_RUNTIME_MODE=demo`.
- Scenario AI snapshot metadata still contains a `codespace` runtime entry.

These are non-blocking and out of scope for #317.

## Notes
This PR intentionally does not perform the broader retired-code cleanup tracked in the separate cleanup issue.
