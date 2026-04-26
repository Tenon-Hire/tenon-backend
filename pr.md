# PR: Remove remaining legacy terminology from API routes, blueprints, and backend copy

## Summary

This PR stabilizes the Winoe AI v4 from-scratch Trial pivot cleanup.

It removes active template-catalog, template-key, and tech-stack public API exposure while keeping historical database compatibility explicit through narrow ORM mappings. Valuable from-scratch coverage was restored instead of deleting tests, and strict rejection remains in place for retired Trial create fields.

## Product / API contract notes

- Trial create/list/detail responses no longer expose `templateKey`, `techStack`, or `scenarioVersionSummary`.
- Trial creation accepts `preferredLanguageFramework` / `preferred_language_framework` as optional informational input.
- `techStack`, `tech_stack`, `templateKey`, and `template_repository` are rejected on create via strict schema validation.
- Frontend consumers must be aligned before relying on this backend branch in demo flows.

## DB compatibility notes

- `ScenarioVersion.project_brief_md` intentionally maps to the historical physical `codespace_spec_json` column.
- Workspace `bootstrap_commit_sha` intentionally maps to the historical physical `base_template_sha` column.
- These are compatibility mappings only; safe physical column renames should be handled in a separate migration issue.

## QA evidence

Passed:

```bash
poetry run python -m compileall -q app
```

Passed:

```bash
poetry run pytest --no-cov -q tests/static/test_issue_302_retired_terms.py
```

Passed:

```bash
poetry run pytest --no-cov -q tests/candidates/routes/test_candidates_candidate_flow_integration_routes.py::test_full_flow_invite_through_first_submission -vv
```

Passed:

```bash
poetry run pytest --no-cov -q
```

Result:

```text
1811 passed, 13 warnings in 137.18s
```

Passed:

```bash
./runBackend.sh migrate
```

Passed:

```bash
./precommit.sh
```

Result:

```text
1811 passed
Total coverage: 96.30%
```

## Risk / follow-up

Non-blocking follow-ups:

- Frontend contract alignment for removed retired fields.
- Optional future DB migration to rename historical physical columns.
- Optional future naming cleanup for remaining internal helper names that still carry old mental-model wording but are not public API.

## Final status

Fixes #302
