## Summary

- Added `app/ai/prompt_assets/v1/SOUL.md` as the source of truth for Winoe persona governance.
- Wired `SOUL.md` into the `winoeReport` prompt-pack entry so Winoe Report generation receives persona governance through the existing snapshot/runtime prompt flow.
- Added focused tests proving `SOUL.md` exists, includes required governance sections, and is included in the Winoe Report prompt path.

## Why

Winoe’s persona rules were not codified in the backend. Report generation needed explicit governance for Winoe’s identity, voice, evaluation philosophy, boundaries, discovery language, and retired terminology bans.

This change makes Winoe Report generation more consistent, evidence-first, and aligned with Winoe AI’s product language.

## Implementation Details

### SOUL.md

Added `app/ai/prompt_assets/v1/SOUL.md` with these sections:

- Identity
- Archetype
- Voice
- Evaluation Philosophy
- Boundaries
- Required Language
- Retired Terminology Ban
- Winoe Report Rules

The file codifies that:

- Winoe is the Talent Intelligence Agent.
- Winoe is AI and never claims to be human.
- Winoe uses Caregiver + Sage voice: warm, careful, honest, evidence-driven.
- Winoe evaluates work, not a person’s worth.
- Winoe never makes hiring decisions.
- The Talent Partner decides.
- Every material claim should connect to Evidence Trail artifacts.
- Winoe uses discovery/revelation language, not elimination language.
- Retired terminology must not appear in generated Winoe Report output.

### Prompt-pack wiring

Updated `app/ai/ai_prompt_pack_service.py` to:

- Load text prompt assets deterministically.
- Fail loudly if `SOUL.md` is missing.
- Inject `SOUL.md` only into the `winoeReport` prompt-pack entry.
- Preserve scope by not injecting Winoe persona governance into reviewer sub-agent prompts.

Runtime path verified:

- `build_prompt_pack_entry("winoeReport")` prepends `## Persona Governance` and `SOUL.md` content.
- `build_ai_policy_snapshot(...)` stores the resolved Winoe Report instructions in the frozen snapshot.
- `build_required_snapshot_prompt(...)` retrieves the resolved prompt.
- The evaluator runtime calls `build_required_snapshot_prompt(...)` with `agent_key="winoeReport"` during Winoe Report generation.

### Tests

Added `tests/ai/test_ai_prompt_pack_soul_service.py` to verify:

- `SOUL.md` exists.
- `SOUL.md` includes required sections.
- `build_prompt_pack_entry("winoeReport")` includes persona governance.
- The frozen snapshot/runtime prompt builder includes `SOUL.md` content.
- The Winoe Report prompt includes discovery language, non-decision boundaries, and retired terminology restrictions.
- `SOUL.md` injection remains scoped to `winoeReport`.

## QA Evidence

### Commit / repo state

- Commit SHA: `5691b74bb40a0c633d20166a5dc707fd706160f8`
- Working tree was clean after QA.
- Expected files were tracked:
  - `app/ai/ai_prompt_pack_service.py`
  - `app/ai/prompt_assets/v1/SOUL.md`
  - `tests/ai/test_ai_prompt_pack_soul_service.py`

### Automated tests

```bash
poetry run pytest -o addopts='' tests/ai/test_ai_prompt_pack_soul_service.py -q
```

Result:

```text
3 passed
```

```bash
poetry run pytest -o addopts='' tests/ai/test_ai_prompt_pack_soul_service.py tests/trials/services/test_trials_ai_policy_snapshot_contract_service.py tests/evaluations/services/test_evaluations_winoe_report_composer_service.py -q
```

Result:

```text
16 passed
```

```bash
./precommit.sh
```

Result:

```text
1836 passed
Required test coverage of 96% reached. Total coverage: 96.10%
All pre-commit checks passed
```

### Runtime prompt-path verification

Direct runtime prompt proof confirmed:

```text
PROMPT_PACK_HAS_PERSONA_GOVERNANCE=True
PROMPT_PACK_HAS_I_AM_WINOE=True
PROMPT_PACK_HAS_TALENT_INTELLIGENCE_AGENT=True
PROMPT_PACK_HAS_TALENT_PARTNER_DECIDES=True
PROMPT_PACK_HAS_RETIRED_TERMINOLOGY_BAN=True
PROMPT_PACK_HAS_DISCOVERY_LANGUAGE=True
PROMPT_PACK_HAS_NON_DECISION_BOUNDARY=True
SNAPSHOT_HAS_PERSONA_GOVERNANCE=True
SNAPSHOT_HAS_I_AM_WINOE=True
SNAPSHOT_HAS_TALENT_INTELLIGENCE_AGENT=True
SNAPSHOT_HAS_TALENT_PARTNER_DECIDES=True
SNAPSHOT_HAS_RETIRED_TERMINOLOGY_BAN=True
SNAPSHOT_HAS_DISCOVERY_LANGUAGE=True
SNAPSHOT_HAS_NON_DECISION_BOUNDARY=True
SNAPSHOT_RUNTIME_CONTEXT_PRESENT=True
AGENT_KEY=winoeReport
```

### Local backend / worker QA

Commands succeeded:

```bash
./runBackend.sh migrate
./runBackend.sh bootstrap-local
nohup ./runBackend.sh > /tmp/winoe-backend-qa-298.log 2>&1 &
```

Runtime verified:

- API process was running:
  - `uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Worker process was running:
  - `python -m app.shared.jobs.shared_jobs_worker_service`
- API was listening on:
  - `127.0.0.1:8000`

Cleanup completed successfully:

- No backend/worker processes remained.
- No listener remained on port `8000`.

### Static scans

Retired terminology scan:

```bash
rg -n -i "Tenon|Tenon AI|SimuHire|recruiter|simulation|Fit Profile|Fit Score|template catalog|precommit|Specializor" app/ai app/evaluations tests/ai tests/evaluations
```

Result:

- Matches only in `SOUL.md` explicit retired-terminology ban list.
- Classification: acceptable guardrail text, not active output language.

Elimination-language scan:

```bash
rg -n -i "reject|rejected|eliminate|eliminated|screen out|pass/fail|not a fit|recommend proceeding|recommend not proceeding" app/ai app/evaluations tests/ai tests/evaluations
```

Result:

- Matches only in `SOUL.md` guardrail/avoid sections and unrelated internal test names.
- Classification: acceptable.
- No unacceptable active report prompt/output language found.

## Scope Control

This PR does not implement unrelated Phase 5 work:

- Does not change #318 rubric dimensions.
- Does not change #301 GitHub provisioning.
- Does not change #297 snapshot agent lists.
- Does not change public API contracts.
- Does not alter Trial/candidate workflows.

## Risk / Notes

- `SOUL.md` is injected only for `winoeReport`, not reviewer sub-agents. This matches issue scope: report-generation persona governance.
- Retired terminology appears in `SOUL.md` only as explicit banned-term guardrail text.
- Backend runtime QA verified API and worker startup, but no paid/external LLM invocation was required for this issue.

## Checklist

- [x] `SOUL.md` added under `app/ai/prompt_assets/v1/`
- [x] `SOUL.md` defines identity, archetype, voice, philosophy, and boundaries
- [x] Winoe Report prompts load `SOUL.md`
- [x] Discovery language enforced
- [x] Elimination language banned
- [x] Retired terminology banned in generated output
- [x] Focused tests pass
- [x] Nearby contract/report tests pass
- [x] Full precommit passes
- [x] Local backend/worker startup verified

Fixes #298