# Replace Day 3 debugging with same-repo implementation wrap-up

## 1. Summary
Day 3 now reflects the product truth for Winoe AI v4:

- It seeds as `type: "code"`.
- Its title is `Implementation Wrap-Up`.
- It continues in the same repository and workspace used on Day 2.
- It persists `finalSha` on Day 3 submission.
- It treats the repository as candidate-owned work, not a debugging exercise.
- It removes debug-era framing from runtime Trial generation.
- It omits legacy `baseTemplateSha` and `precommitSha` from `/api/tasks/{task_id}/codespace/init` responses when those values are null.

The backend now tells the truth in seeded tasks, scenario payloads, rubric text, and candidate-facing API responses.

## 2. What Changed

### Day 3 blueprint / seeded task truth
- Updated the Day 3 seeded blueprint to `Implementation Wrap-Up`.
- Kept Day 3 as a code task.
- Kept Day 3 explicitly tied to the same repo/workspace used on Day 2.

### Scenario generation copy for Day 3
- Updated runtime Day 3 prompt copy to frame the day as continuation work in the same repository.
- Removed debugging language from the Day 3 prompt path.
- Kept the copy focused on finishing implementation details, tightening tests, improving docs, and polishing for handoff.

### Rubric summary and dimensions
- Updated the rubric summary to describe planning, implementation, wrap-up, demo presentation, and reflection in a from-scratch build.
- Renamed the Day 3-facing rubric dimension away from debugging and toward implementation completeness and handoff readiness.

### Runtime init response cleanup
- Cleaned up `/api/tasks/{task_id}/codespace/init` responses so null legacy fields are not emitted.
- The response now returns the workspace identity and repo identity needed by the candidate without exposing null `baseTemplateSha` / `precommitSha` fields.

### Test updates
- Updated trial creation and scenario-generation tests to assert Day 3 is `Implementation Wrap-Up`.
- Updated submission tests to verify Day 3 persists `finalSha` and reuses the Day 2 repository.
- Updated codespace-init tests to verify the legacy null fields are omitted.
- Added/kept the missing-workspace path test returning `WORKSPACE_NOT_INITIALIZED`.

### Deterministic precommit stabilization
- Stabilized `test_schedule_candidate_session_validation_errors` by moving the past timestamp farther into the past so `SCHEDULE_START_IN_PAST` is deterministic in precommit.

## 3. Why
Winoe AI v4 is from scratch. There is no precommit baseline to debug against, so Day 3 must be framed as same-repo implementation wrap-up.

That means the backend has to be truthful in every place candidates and reviewers see Day 3:

- seeded tasks
- runtime Trial generation
- rubric copy
- codespace init responses
- submission persistence

If those surfaces still talk about debugging or legacy baseline concepts, the product story is wrong.

## 4. Acceptance Criteria

- [x] Day 3 title is `Implementation Wrap-Up`
- [x] Day 3 uses the same repo/workspace as Day 2
- [x] Day 3 captures and persists `finalSha`
- [x] Runtime scenario/task/rubric payloads use wrap-up framing instead of debugging framing
- [x] `/codespace/init` omits `baseTemplateSha` and `precommitSha` when null
- [x] Missing Day 2 workspace returns `WORKSPACE_NOT_INITIALIZED`

## 5. Testing / QA

### Live QA evidence
- Trial create/detail showed Day 3:
  - `type: "code"`
  - `title: "Implementation Wrap-Up"`
  - scenario Day 3 prompt uses wrap-up framing
  - rubric summary uses wrap-up framing, not debugging framing
- Day 2 init and Day 3 init used the same repo/workspace:
  - `repoFullName: winoe-ai-repos/winoe-ws-82`
  - `workspaceId: 9988df21-aac5-4126-9885-f23efb643b67`
- Day 2 and Day 3 init payloads omitted:
  - `baseTemplateSha`
  - `precommitSha`
- Day 3 submit returned and persisted:
  - `finalSha: "abc123"`
- Missing-workspace path returned:
  - `errorCode: "WORKSPACE_NOT_INITIALIZED"`

### DB verification
- Day 2 submission repo matched Day 3 submission repo.
- Day 3 submission stored `finalSha`.
- A single workspace was reused for Day 2 and Day 3.

### Validation commands
- `./precommit.sh`
  - `1735 passed`
  - coverage `96.05%`
  - `✅ All pre-commit checks passed!`

## 6. Risks / Follow-ups
- Local live QA used demo/stubbed GitHub and Actions setup for deterministic validation.
- One legacy test filename may still contain `debug`, but shipped runtime behavior and assertions now reflect Implementation Wrap-Up.
