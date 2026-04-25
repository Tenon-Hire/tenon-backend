# Summary

Benchmarks now compare candidates only within the same Trial, preserving Winoe AI's fairness and evidence-trust guarantees.

The public response now includes `cohortSize`, `state`, `message`, and public-only signal values in `recommendation`.

# Changes

- Trial-scoped compare query/response path now filters Benchmarks to the requested Trial only.
- Cohort metadata and empty/partial/ready states are returned in the live API contract.
- Limited-comparison caveat is shown when cohort size is below 3.
- Stored-to-public signal mapping is enforced:
  - `strong_hire` -> `strong_signal`
  - `hire` -> `positive_signal`
  - `lean_hire` -> `mixed_signal`
  - `no_hire` -> `limited_signal`
- Public schema validation rejects internal hiring enums at the API boundary.
- Singular/plural caveat copy is corrected so the message reads naturally for 1, 2, or 3+ candidates.
- Route/API tests cover the contract behavior for 0, 1, 2, and 3+ candidate states.
- Refresh-after-Winoe-Report-generation regression coverage confirms Benchmarks updates after new completed evaluations land.
- Live-style smoke helper was added to exercise the contract against a running API instance.

# QA / Verification

- Focused compare tests:
  - `poetry run pytest --no-cov ...`
  - Result: pass, `17 passed`
- Full test suite:
  - `poetry run pytest`
  - Result: pass, `1846 passed`
- Pre-commit:
  - `poetry run pre-commit run --all-files` could not run because `pre-commit` was unavailable in the workspace.
  - `poetry run python -m pre_commit run --all-files` could not run because the module was unavailable.
  - The reported validation output showed coverage passing at `96.01%` with `1846 passed`.

# Live HTTP Verification

0 candidates:

```json
{"trialId":1,"cohortSize":0,"state":"empty","message":"No completed Winoe Reports are available for this Trial yet.","candidates":[]}
```

1 candidate:

```json
{"trialId":2,"cohortSize":1,"state":"partial","message":"Limited comparison — only 1 candidate completed this Trial.","candidates":[{"candidateSessionId":1,"recommendation":"positive_signal"}]}
```

2 candidates:

```json
{"trialId":3,"cohortSize":2,"state":"partial","message":"Limited comparison — only 2 candidates completed this Trial.","candidates":[{"candidateSessionId":2,"recommendation":"mixed_signal"},{"candidateSessionId":3,"recommendation":"positive_signal"}]}
```

3 candidates:

```json
{"trialId":4,"cohortSize":3,"state":"ready","message":null,"candidates":[{"candidateSessionId":4,"recommendation":"strong_signal"},{"candidateSessionId":5,"recommendation":"positive_signal"},{"candidateSessionId":6,"recommendation":"mixed_signal"}]}
```

Same-company/different-Trial isolation:

- Trial 2 returned candidate IDs `[1]`.
- Trial 5 returned candidate ID `[7]`.
- No cross-contamination between those Trials.

Different-company isolation:

```json
{"status":403,"payload":{"detail":"Trial access forbidden"}}
```

Authorization:

- Different-company access guard returned `403`.
- Candidate-email dev request returned `401` in the local seeded DB because that dev user was not present.

Refresh after Winoe Report generation:

- Before report generation, Trial 7 returned `empty`.
- After inserting the completed evaluation run, Trial 7 returned:

```json
{"trialId":7,"cohortSize":1,"state":"partial","message":"Limited comparison — only 1 candidate completed this Trial.","candidates":[{"candidateSessionId":9,"recommendation":"strong_signal"}]}
```

# Risk / Notes

- Live HTTP verification was performed against a local `uvicorn` instance with seeded sqlite data and dev-bypass auth.
- The prior QA failure was caused by runtime drift and live verification mismatch; the route now explicitly validates the response model at the API boundary.
- A live-style smoke helper was added to reduce the chance of this contract drifting again.

# Acceptance Criteria Mapping

- Compare only returns same-Trial candidates: covered by same-company/different-Trial and different-company checks.
- No-data state for new Trials: covered by the 0-candidate payload.
- Refreshes after report generation: covered by the Trial 7 before/after payload.
- Framing does not imply Winoe decides: public signal values only; internal hiring enums are rejected.
- 2+ same-Trial candidates: covered by the 2-candidate and 3-candidate payloads.
- Cohort size: `cohortSize` is present in all payloads.
- Limited caveat for cohort < 3: present for 1 and 2 candidates.
- 0 -> 1 -> 2+ transitions: covered by the live HTTP payloads and tests.

# Follow-ups

- Consider wiring `scripts/compare_contract_smoke_test.py` into CI or the backend smoke pipeline.

## Worker Report

- Summary
  - Benchmarks are now isolated to the requested Trial, with public contract fields and state handling that make the response predictable across 0, 1, 2, and 3+ candidate cohorts.
- Files changed
  - `pr.md`
- Commands run
  - `sed -n '1,240p' pr.md` - pass
  - `sed -n '1,240p' issue.md` - pass
  - `poetry run pytest --no-cov ...` - pass, `17 passed`
  - `poetry run pytest` - pass, `1846 passed`
  - `poetry run pre-commit run --all-files` - fail, `pre-commit` unavailable in the workspace
  - `poetry run python -m pre_commit run --all-files` - fail, module unavailable
- Risks / assumptions
  - The live HTTP verification reflects a local `uvicorn` instance with seeded sqlite data and dev-bypass auth.
  - The reported validation output is treated as the source of truth for the pre-commit/coverage status because the direct pre-commit commands could not execute.
- Open questions / blockers
  - None
