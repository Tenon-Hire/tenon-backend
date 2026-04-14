# Fix Trial detail, scenario preview, approval, and activation endpoints #280
Closes #280.

## 2. TL;DR
Trial detail is repaired end to end: `GET /api/trials/{id}` now returns the scenario/task/rubric/lifecycle payloads expected by the preview page, scenario generation produces a reviewable `ScenarioVersion`, approval locks that version, activation requires a locked scenario and moves the Trial to `active_inviting`, and generation failures are surfaced explicitly with retry affordance. Anthropic scenario-generation truncation was fixed so the happy path works live.

## 3. Problem
`GET /api/trials/{id}` was broken and incomplete, and the lifecycle around review, approval, and activation had drifted from the intended Trial flow. Some tests and helpers were masking parts of the real lifecycle, which made the endpoint behavior look more complete than it was. Live manual QA exposed a separate blocker in Anthropic structured output: scenario generation could truncate before completion, which prevented the primary-provider happy path from finishing cleanly.

## 4. What changed
- Updated the Trial detail payload and rendering so the preview page can consume scenario, task, rubric, and lifecycle data in one response.
- Tightened scenario selection and rendering rules so active and pending versions are handled explicitly instead of being inferred through helper shortcuts.
- Added generation failure visibility and retry metadata so failed scenario generation is shown as a real state, not as a silent degrade.
- Changed approval so it locks the `ScenarioVersion` and records the review decision on the version itself.
- Added a hard activation guard that rejects non-locked scenarios before the Trial can move forward.
- Updated candidate/invite/lifecycle tests to require explicit approval before activation.
- Fixed Anthropic scenario generation by compacting prestart prompt guidance, raising the scenario-generation-only Anthropic output cap, and validating the complete structured output path.

## 5. Why this approach
The lifecycle stays `generating -> ready_for_review -> active_inviting -> terminated`, because that is the clearest mapping to the product behavior and avoids inventing a new Trial state just for approval. Approval state belongs on `ScenarioVersion` locking, not on a separate Trial lifecycle state, and `generationStatus` stays distinct from the Trial lifecycle status so review, generation, and activation are not conflated. The explicit lifecycle is better than helper magic because it makes the tests and endpoint behavior match what operators and reviewers actually see. Provider failures must fail visibly rather than silently degrade into template success, and the Anthropic fix was kept narrow on purpose so it only changes the structured scenario-generation path.

## 6. Manual QA
### Final successful live QA
- Local backend and worker started successfully.
- A fresh Trial was created.
- Scenario generation completed successfully through Anthropic.
- A reviewable `ScenarioVersion` was observed.
- Approval succeeded and produced a non-null `lockedAt`.
- Activation succeeded and the Trial moved to `active_inviting`.
- Negative activation before approval returned `SCENARIO_LOCK_REQUIRED`.

### Runtime drift noted during QA
- An earlier local config drift caused readiness to report OpenAI.
- That local runtime issue was corrected during QA.
- The final approved QA was performed on the Anthropic happy path.

## 7. Test plan
- Focused Anthropic provider repro before the fix.
- Focused Anthropic provider verification after the fix.
- `pytest` for config/provider client schema payload tests.
- `pytest` for Anthropic provider integration tests.
- `pytest` for trial scenario generation service tests.
- `pytest` for trial scenario generation route success/failure tests.
- Final `./precommit.sh` result: `1763 passed`, `96.03%` coverage.

## 8. Acceptance criteria mapping
- `GET /api/trials/{id}` returns scenario/task/rubric/lifecycle payloads: repaired Trial detail payload and preview rendering.
- Scenario generation produces a reviewable `ScenarioVersion`: generation now reaches a reviewable version state.
- Scenario approval locks the version: approval now sets the version lock and records `lockedAt`.
- Trial activation moves status to `active_inviting`: activation now transitions the Trial into `active_inviting`.
- Only locked scenarios can be activated: activation now hard-fails with `SCENARIO_LOCK_REQUIRED` when the version is not locked.
- Generation failure shows retry option: generation failures are surfaced explicitly with retry metadata.

## 9. Risks / follow-ups
- The failure and retry affordance is well covered by tests, but the final manual QA intentionally focused on the happy path rather than re-breaking the provider flow.
- Future cleanup could further centralize public job-status naming if that starts to spread again.
- If prompt payloads grow materially again, the Anthropic output budget may need another pass.

## 10. Notes for reviewers
- Focus on the detail renderer and generation state semantics.
- Check the separation between approval and activation.
- Review the explicit lifecycle in the candidate/invite tests.
- Inspect the Anthropic structured-output fix and confirm why it is intentionally narrow.
