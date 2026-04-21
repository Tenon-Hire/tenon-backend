# Add auth isolation regressions for Talent Partner, candidate session, and invite-token routes

## 1. Summary

This PR adds auth isolation regressions for Talent Partner, Candidate, and invite-token resources. No production auth logic changes were needed; the existing ownership and auth guards already enforced the required boundaries. Existing CSRF posture and production dev-bypass guards were validated.

## 2. Problem

Login worked, but cross-tenant and cross-session isolation needed explicit regression coverage. Issue #292 required proof that:

- Talent Partner A cannot read Talent Partner B's candidates
- Candidate A cannot read Candidate B's session
- Invite-token resources are properly scoped
- CSRF posture is verified
- Dev bypasses are disabled in production

## 3. What Changed

### Talent Partner isolation

- Added regression coverage for the Talent Partner candidate-list route to confirm a Talent Partner cannot read another Talent Partner's candidates.

### Candidate session isolation

- Added regression coverage for candidate session read and current-task routes to confirm Candidate A cannot access Candidate B's session data.

### Invite-token isolation

- Added regression coverage for invite-token read and claim surfaces to confirm mismatched-email requests are rejected.

### Security posture coverage

- Added/updated regressions that verify CSRF origin enforcement on logout.
- Added/updated regressions that confirm production dev-bypass behavior remains disabled.

## 4. QA

### Live verification

- `GET /api/trials/19/candidates` as Talent Partner A against Talent Partner B's Trial -> `404 {"detail":"Trial not found"}`
- `POST /api/auth/logout` with hostile origin + cookie -> `403 {"error":"CSRF_ORIGIN_MISMATCH","message":"Request origin not allowed."}`
- `GET /api/candidate/session/20/current_task` as candidate A against candidate B session -> `403 CANDIDATE_INVITE_EMAIL_MISMATCH`
- `GET /api/candidate/session/2lBOgydRX_1WeKPNvFqb9w` as candidate A -> `403 CANDIDATE_INVITE_EMAIL_MISMATCH`
- `POST /api/candidate/session/2lBOgydRX_1WeKPNvFqb9w/claim` as candidate A -> `403 CANDIDATE_INVITE_EMAIL_MISMATCH`

### Database evidence

- Target session row remained unchanged across denied candidate requests:
  - `candidate_auth0_sub`
  - `candidate_auth0_email`
  - `candidate_email`
  - `claimed_at`
  - `status`
- Unrelated session row remained unchanged as well.

### Focused tests

- `8 passed, 16 deselected in 0.61s`

### QA notes

- Manual QA was completed on a repo-owned local server with local/dev-bypass posture enabled for localhost shorthand auth testing.
- The issue acceptance criteria were verified live and by focused tests.

## 5. Risk / notes

- The local QA database had duplicate candidate-email rows from earlier attempts, so the final evidence pinned specific scenario row IDs.
- No blocker remains for this issue.
