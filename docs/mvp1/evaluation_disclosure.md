# Tenon MVP1 Candidate Disclosure: AI-Assisted Evaluation

This simulation uses AI-assisted evaluation for submitted work. The AI helps summarize evidence and score specific day outputs, but people oversee the process.

## What AI is used for

- AI-assisted scoring may be applied to simulation days 1 through 5.
- The system evaluates evidence from submitted artifacts, including:
  - Written responses (for example day 1 and day 5 reflections)
  - Code evidence (for example commit, diff, and test references for days 2 and 3)
  - Transcript segments for day 4 handoff responses (`startMs` / `endMs`)

## What humans do

- Human reviewers oversee AI-generated findings.
- Final hiring decisions are made by people.
- This is a policy/process boundary: the backend stores AI notice/toggle configuration and evaluation evidence for evaluation workflows; final hiring decisions are made by people outside this service.

## How day-level AI controls work

- AI usage is configurable per day using per-day toggles.
- If AI is disabled for a day, that day is marked as `human_review_required` in fit-profile reporting.
- Candidate session responses include the current AI config fields:
  - `aiNoticeText`
  - `aiNoticeVersion`
  - `evalEnabledByDay`

## What notice/consent versions are stored

- Simulation configuration stores:
  - `ai_notice_version`
  - `ai_notice_text`
  - `ai_eval_enabled_by_day`
- For day 4 media consent, the candidate consent record stores:
  - `consent_version`
  - `consent_timestamp`
  - `ai_notice_version`

## Plain-language disclosure template

Use this text for candidate-facing communication:

> Tenon uses AI to help evaluate submitted work artifacts, coding outputs, and communication signals across this simulation. Human reviewers oversee AI-generated findings, and final hiring decisions are made by people. AI usage can be enabled or disabled by simulation day.

## Important boundaries

- This disclosure does not claim bias elimination.
- This disclosure does not claim legal or compliance certification.
- This disclosure does not describe end-to-end automated hiring decisions.
