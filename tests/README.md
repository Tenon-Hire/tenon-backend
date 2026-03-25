## Test architecture

- Layout mirrors `app/` domain-first packages: `tests/recruiters/*`, `tests/candidates/*`, `tests/simulations/*`, `tests/tasks/*`, `tests/submissions/*`, `tests/evaluations/*`, `tests/media/*`, `tests/notifications/*`, plus shared slices under `tests/shared/*`.
- Fixtures: `async_client` wires FastAPI with dependency overrides; `db_session`/`async_session` share a truncated DB per test; `auth_header_factory` builds recruiter headers; `candidate_header_factory` builds candidate headers for task submissions.
- Factories: shared async factories live in `tests/shared/factories/*` (companies, recruiters, simulations + tasks, candidate sessions, submissions).
- Progress helpers and related utilities are under `app/candidates/*`, `app/submissions/*`, and `app/shared/types/*`, with mirrored coverage under `tests/candidates/*`, `tests/submissions/*`, and `tests/shared/*`.

## Running tests

- Standard run: `poetry run pytest`
- With coverage (CI default): `poetry run pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=99`
- To scope by domain, target a package directly (for example `poetry run pytest tests/candidates/routes -q`).
