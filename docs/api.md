# API Reference

Generated from FastAPI OpenAPI plus dependency-based auth mapping.
Generated at: 2026-03-27T14:41:43.988295+00:00
Total endpoints: 46

## Endpoint Index

- `POST /api/admin/candidate_sessions/{candidate_session_id}/reset`: Reset Candidate Session
- `POST /api/admin/jobs/{job_id}/requeue`: Requeue Job
- `POST /api/admin/media/purge`: Purge Media Retention
- `POST /api/admin/trials/{trial_id}/scenario/use_fallback`: Use Trial Fallback
- `GET /api/admin/templates/health`: Get Template Health
- `POST /api/admin/templates/health/run`: Run Template Health
- `POST /api/auth/logout`: Logout
- `GET /api/auth/me`: Read Me
- `GET /api/candidate/invites`: List Candidate Invites
- `GET /api/candidate/session/{candidate_session_id}/current_task`: Get Current Task
- `POST /api/candidate/session/{candidate_session_id}/privacy/consent`: Record Candidate Privacy Consent
- `GET /api/candidate/session/{token}`: Resolve Candidate Session
- `POST /api/candidate/session/{token}/claim`: Claim Candidate Session
- `POST /api/candidate/session/{token}/schedule`: Schedule Candidate Session
- `GET /api/candidate_sessions/{candidate_session_id}/winoe_report`: Get Winoe Report Route
- `POST /api/candidate_sessions/{candidate_session_id}/winoe_report/generate`: Generate Winoe Report Route
- `POST /api/github/webhooks`: Receive Github Webhook
- `GET /api/jobs/{job_id}`: Get Job Status
- `POST /api/recordings/{recording_id}/delete`: Delete Recording Route
- `GET /api/trials`: List Trials
- `POST /api/trials`: Create Trial
- `GET /api/trials/{trial_id}`: Get Trial Detail
- `PUT /api/trials/{trial_id}`: Update Trial
- `POST /api/trials/{trial_id}/activate`: Activate Trial
- `GET /api/trials/{trial_id}/candidates`: List Trial Candidates
- `GET /api/trials/{trial_id}/candidates/compare`: List Trial Candidates Compare
- `POST /api/trials/{trial_id}/candidates/{candidate_session_id}/invite/resend`: Resend Candidate Invite
- `POST /api/trials/{trial_id}/invite`: Create Candidate Invite
- `PATCH /api/trials/{trial_id}/scenario/active`: Update Active Scenario Version
- `POST /api/trials/{trial_id}/scenario/regenerate`: Regenerate Scenario Version
- `PATCH /api/trials/{trial_id}/scenario/{scenario_version_id}`: Patch Scenario Version
- `POST /api/trials/{trial_id}/scenario/{scenario_version_id}/approve`: Approve Scenario Version
- `POST /api/trials/{trial_id}/terminate`: Terminate Trial
- `GET /api/submissions`: List Submissions Route
- `GET /api/submissions/{submission_id}`: Get Submission Detail Route
- `POST /api/tasks/{task_id}/codespace/init`: Init Codespace Route
- `GET /api/tasks/{task_id}/codespace/status`: Codespace Status Route
- `GET /api/tasks/{task_id}/draft`: Get Task Draft Route
- `PUT /api/tasks/{task_id}/draft`: Put Task Draft Route
- `GET /api/tasks/{task_id}/handoff/status`: Handoff Status Route
- `POST /api/tasks/{task_id}/handoff/upload/complete`: Complete Handoff Upload Route
- `POST /api/tasks/{task_id}/handoff/upload/init`: Init Handoff Upload Route
- `POST /api/tasks/{task_id}/run`: Run Task Tests Route
- `GET /api/tasks/{task_id}/run/{run_id}`: Get Run Result Route
- `POST /api/tasks/{task_id}/submit`: Submit Task Route
- `GET /health`: Health Check

## Endpoint Details

### `POST /api/admin/candidate_sessions/{candidate_session_id}/reset`
- Summary: Reset Candidate Session
- Description: Reset a candidate session state during demo-mode operations for controlled QA or replay flows.
- Auth: Bearer token for demo admin allowlist (requires `WINOE_DEMO_MODE=true`)
- Operation ID: `reset_candidate_session_api_admin_candidate_sessions__candidate_session_id__reset_post`
- Dependency auth signals: `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils.require_demo_mode_admin`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `candidate_session_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `CandidateSessionResetRequest`
- Request example:
```json
{
  "targetState": "not_started",
  "reason": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `CandidateSessionResetResponse`)
- Error responses:
  - `400`: Invalid reset request payload. (schema: `-`)
  - `403`: Admin access required. (schema: `-`)
  - `404`: Demo mode disabled or target session not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "candidateSessionId": 1,
  "status": "ok",
  "resetTo": "not_started"
}
```

### `POST /api/admin/jobs/{job_id}/requeue`
- Summary: Requeue Job
- Description: Force a durable background job back to queued state for demo-mode recovery/testing.
- Auth: Bearer token for demo admin allowlist (requires `WINOE_DEMO_MODE=true`)
- Operation ID: `requeue_job_api_admin_jobs__job_id__requeue_post`
- Dependency auth signals: `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils.require_demo_mode_admin`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `job_id` | yes | `string` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `JobRequeueRequest`
- Request example:
```json
{
  "reason": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `JobRequeueResponse`)
- Error responses:
  - `400`: Job cannot be requeued. (schema: `-`)
  - `403`: Admin access required. (schema: `-`)
  - `404`: Demo mode disabled or target job not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "jobId": "example",
  "previousStatus": "example",
  "newStatus": "example",
  "auditId": "example"
}
```

### `POST /api/admin/media/purge`
- Summary: Purge Media Retention
- Description: Run retention cleanup for recording assets and mark expired media as purged in demo environments.
- Auth: Bearer token for demo admin allowlist (requires `WINOE_DEMO_MODE=true`)
- Operation ID: `purge_media_retention_api_admin_media_purge_post`
- Dependency auth signals: `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils.require_demo_mode_admin`, `app.shared.http.dependencies.shared_http_dependencies_storage_media_utils.get_media_storage_provider`, `fastapi.security.http.unknown`
- Path params: 
  - None
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `MediaRetentionPurgeRequest`
- Request example:
```json
{
  "retentionDays": 1,
  "batchLimit": 1
}
```
- Success responses:
  - `200`: Successful Response (schema: `MediaRetentionPurgeResponse`)
- Error responses:
  - `400`: Retention inputs are invalid. (schema: `-`)
  - `403`: Admin access required. (schema: `-`)
  - `404`: Demo mode disabled. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "status": "example",
  "scannedCount": 1,
  "purgedCount": 1,
  "failedCount": 1,
  "purgedRecordingIds": [
    1
  ]
}
```

### `POST /api/admin/trials/{trial_id}/scenario/use_fallback`
- Summary: Use Trial Fallback
- Description: Apply a fallback scenario version to a trial when generated content must be overridden in demo mode.
- Auth: Bearer token for demo admin allowlist (requires `WINOE_DEMO_MODE=true`)
- Operation ID: `use_trial_fallback_api_admin_trials__trial_id__scenario_use_fallback_post`
- Dependency auth signals: `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils.require_demo_mode_admin`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `TrialFallbackRequest`
- Request example:
```json
{
  "scenarioVersionId": 1,
  "reason": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `TrialFallbackResponse`)
- Error responses:
  - `400`: Fallback request is invalid. (schema: `-`)
  - `403`: Admin access required. (schema: `-`)
  - `404`: Demo mode disabled or trial not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "trialId": 1,
  "activeScenarioVersionId": 1,
  "applyTo": "example"
}
```

### `GET /api/admin/templates/health`
- Summary: Get Template Health
- Description: Check template repos against the Actions artifact contract (admin-only).
- Auth: Admin API key via `X-Admin-Key` header
- Operation ID: `get_template_health_api_admin_templates_health_get`
- Dependency auth signals: `app.shared.auth.shared_auth_admin_api_key_utils.require_admin_key`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_github_client`
- Path params: 
  - None
- Query params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `mode` | no | `string` | `'static'` | - |
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `X-Admin-Key` | no | `X-Admin-Key` | `-` | - |
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `TemplateHealthResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "ok": true,
  "templates": [
    {
      "templateKey": "example",
      "repoFullName": "example",
      "workflowFile": "example",
      "defaultBranch": "example",
      "ok": true,
      "errors": [
        "example"
      ],
      "checks": {
        "repoReachable": true,
        "defaultBranch": "example",
        "defaultBranchUsable": true
      }
    }
  ]
}
```

### `POST /api/admin/templates/health/run`
- Summary: Run Template Health
- Description: Execute live template health checks by dispatching workflow runs and validating artifact contracts.
- Auth: Admin API key via `X-Admin-Key` header
- Operation ID: `run_template_health_api_admin_templates_health_run_post`
- Dependency auth signals: `app.shared.auth.shared_auth_admin_api_key_utils.require_admin_key`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_github_client`
- Path params: 
  - None
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `X-Admin-Key` | no | `X-Admin-Key` | `-` | - |
- Request schema: `TemplateHealthRunRequest`
- Request example:
```json
{
  "templateKeys": [
    "example"
  ]
}
```
- Success responses:
  - `200`: Successful Response (schema: `TemplateHealthResponse`)
- Error responses:
  - `404`: Invalid or missing admin key. (schema: `-`)
  - `422`: Live check payload validation failed. (schema: `-`)
- Success example (`200`):
```json
{
  "ok": true,
  "templates": [
    {
      "templateKey": "example",
      "repoFullName": "example",
      "workflowFile": "example",
      "defaultBranch": "example",
      "ok": true,
      "errors": [
        "example"
      ],
      "checks": {
        "repoReachable": true,
        "defaultBranch": "example",
        "defaultBranchUsable": true
      }
    }
  ]
}
```

### `POST /api/auth/logout`
- Summary: Logout
- Description: Stateless logout acknowledgment endpoint; client clears local auth state.
- Auth: None
- Operation ID: `logout_api_auth_logout_post`
- Dependency auth signals: None
- Path params: 
  - None
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `204`: Successful Response (schema: `-`)
- Error responses:
  - `500`: Unexpected logout response failure. (schema: `-`)

### `GET /api/auth/me`
- Summary: Read Me
- Description: Return the authenticated talent_partner profile for the caller.
- Auth: Talent Partner bearer token
- Operation ID: `read_me_api_auth_me_get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_authenticated_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - None
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `UserRead`)
- Error responses:
  - `401`: Authentication required. (schema: `-`)
  - `429`: Rate limit exceeded. (schema: `-`)
- Success example (`200`):
```json
{
  "id": 1,
  "name": "example",
  "email": "example",
  "role": "example"
}
```

### `GET /api/candidate/invites`
- Summary: List Candidate Invites
- Description: List all invites for the authenticated candidate email.
- Auth: Candidate bearer token with `candidate:access`
- Operation ID: `list_candidate_invites_api_candidate_invites_get`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - None
- Query params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `includeTerminated` | no | `boolean` | `False` | - |
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `Response List Candidate Invites Api Candidate Invites Get`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
[
  {
    "candidateSessionId": 1,
    "trialId": 1,
    "trialTitle": "example",
    "role": "example",
    "companyName": "example",
    "status": "not_started",
    "progress": {
      "completed": 1,
      "total": 1
    },
    "lastActivityAt": "2026-01-01T00:00:00Z",
    "inviteCreatedAt": "2026-01-01T00:00:00Z",
    "expiresAt": "2026-01-01T00:00:00Z",
    "isExpired": true
  }
]
```

### `GET /api/candidate/session/{candidate_session_id}/current_task`
- Summary: Get Current Task
- Description: Return the current task for a candidate session.
- Auth: Candidate bearer token with `candidate:access`
- Operation ID: `get_current_task_api_candidate_session__candidate_session_id__current_task_get`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `candidate_session_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `CurrentTaskResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "candidateSessionId": 1,
  "status": "not_started",
  "currentDayIndex": 1,
  "currentTask": {
    "id": 1,
    "dayIndex": 1,
    "title": "example",
    "type": "example",
    "description": "example"
  },
  "completedTaskIds": [
    1
  ],
  "progress": {
    "completed": 1,
    "total": 1
  },
  "isComplete": true
}
```

### `POST /api/candidate/session/{candidate_session_id}/privacy/consent`
- Summary: Record Candidate Privacy Consent
- Description: Persist candidate consent acknowledgements for recording/privacy notices tied to a claimed session.
- Auth: Candidate bearer token with `candidate:access`
- Operation ID: `record_candidate_privacy_consent_api_candidate_session__candidate_session_id__privacy_consent_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `candidate_session_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `CandidatePrivacyConsentRequest`
- Request example:
```json
{
  "noticeVersion": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `CandidatePrivacyConsentResponse`)
- Error responses:
  - `401`: Candidate authentication required. (schema: `-`)
  - `403`: Candidate does not own session. (schema: `-`)
  - `404`: Candidate session not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "status": "example"
}
```

### `GET /api/candidate/session/{token}`
- Summary: Resolve Candidate Session
- Description: Claim an invite token for the authenticated candidate.
- Auth: Candidate bearer token with `candidate:access`
- Operation ID: `resolve_candidate_session_api_candidate_session__token__get`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `token` | yes | `string` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `CandidateSessionResolveResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "candidateSessionId": 1,
  "status": "not_started",
  "claimedAt": "2026-01-01T00:00:00Z",
  "startedAt": "2026-01-01T00:00:00Z",
  "completedAt": "2026-01-01T00:00:00Z",
  "candidateName": "example",
  "trial": {
    "id": 1,
    "title": "example",
    "role": "example"
  },
  "aiNoticeText": "example",
  "aiNoticeVersion": "example",
  "evalEnabledByDay": {
    "key": true
  }
}
```

### `POST /api/candidate/session/{token}/claim`
- Summary: Claim Candidate Session
- Description: Idempotent claim endpoint for authenticated candidates (no email body required).
- Auth: Candidate bearer token with `candidate:access`
- Operation ID: `claim_candidate_session_api_candidate_session__token__claim_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `token` | yes | `string` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `CandidateSessionResolveResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "candidateSessionId": 1,
  "status": "not_started",
  "claimedAt": "2026-01-01T00:00:00Z",
  "startedAt": "2026-01-01T00:00:00Z",
  "completedAt": "2026-01-01T00:00:00Z",
  "candidateName": "example",
  "trial": {
    "id": 1,
    "title": "example",
    "role": "example"
  },
  "aiNoticeText": "example",
  "aiNoticeVersion": "example",
  "evalEnabledByDay": {
    "key": true
  }
}
```

### `POST /api/candidate/session/{token}/schedule`
- Summary: Schedule Candidate Session
- Description: Persist candidate-proposed schedule details and send confirmation notifications for the session token.
- Auth: Candidate bearer token with `candidate:access`
- Operation ID: `schedule_candidate_session_api_candidate_session__token__schedule_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_notifications_utils.get_email_service`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `token` | yes | `string` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `CandidateSessionScheduleRequest`
- Request example:
```json
{
  "scheduledStartAt": "2026-01-01T00:00:00Z",
  "candidateTimezone": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `CandidateSessionScheduleResponse`)
- Error responses:
  - `401`: Candidate authentication required. (schema: `-`)
  - `403`: Token does not match principal. (schema: `-`)
  - `404`: Candidate session not found. (schema: `-`)
  - `410`: Candidate invite token is expired. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "candidateSessionId": 1,
  "scheduledStartAt": "2026-01-01T00:00:00Z",
  "candidateTimezone": "example",
  "dayWindows": [
    {
      "dayIndex": 1,
      "windowStartAt": "2026-01-01T00:00:00Z",
      "windowEndAt": "2026-01-01T00:00:00Z"
    }
  ],
  "scheduleLockedAt": "2026-01-01T00:00:00Z"
}
```

### `GET /api/candidate_sessions/{candidate_session_id}/winoe_report`
- Summary: Get Winoe Report Route
- Description: Return winoe-report generation status and latest report payload for a talent_partner-visible candidate session.
- Auth: Talent Partner bearer token
- Operation ID: `get_winoe_report_route_api_candidate_sessions__candidate_session_id__winoe_report_get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `candidate_session_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `WinoeReportStatusResponse`)
- Error responses:
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Candidate session not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "status": "not_started"
}
```

### `POST /api/candidate_sessions/{candidate_session_id}/winoe_report/generate`
- Summary: Generate Winoe Report Route
- Description: Queue or compute winoe-report artifacts for a candidate session visible to the authenticated talent_partner.
- Auth: Talent Partner bearer token
- Operation ID: `generate_winoe_report_route_api_candidate_sessions__candidate_session_id__winoe_report_generate_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `candidate_session_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `202`: Successful Response (schema: `WinoeReportGenerateResponse`)
- Error responses:
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Candidate session not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`202`):
```json
{
  "jobId": "example",
  "status": "example"
}
```

### `POST /api/github/webhooks`
- Summary: Receive Github Webhook
- Description: Validate GitHub webhook deliveries, process completed workflow_run events, and enqueue artifact parse jobs.
- Auth: GitHub webhook signature (`X-Hub-Signature-256`) when configured
- Operation ID: `receive_github_webhook_api_github_webhooks_post`
- Dependency auth signals: `app.shared.database.get_session`
- Path params: 
  - None
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `202`: Successful Response (schema: `Response Receive Github Webhook Api Github Webhooks Post`)
- Error responses:
  - `401`: Webhook signature is invalid. (schema: `-`)
  - `413`: Webhook payload exceeded configured max size. (schema: `-`)
  - `503`: Webhook secret not configured. (schema: `-`)
- Success example (`202`):
```json
{
  "key": "example"
}
```

### `GET /api/jobs/{job_id}`
- Summary: Get Job Status
- Description: Return a single durable job status if visible to the authenticated principal.
- Auth: Bearer token (principal-scoped access)
- Operation ID: `get_job_status_api_jobs__job_id__get`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `job_id` | yes | `string` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `JobStatusResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "jobId": "example",
  "jobType": "example",
  "status": "example",
  "attempt": 1,
  "maxAttempts": 1,
  "pollAfterMs": 1,
  "result": {},
  "error": "example"
}
```

### `POST /api/recordings/{recording_id}/delete`
- Summary: Delete Recording Route
- Description: Soft-delete a recording asset owned by the authenticated candidate session and revoke access links.
- Auth: Candidate bearer token with `candidate:access`
- Operation ID: `delete_recording_route_api_recordings__recording_id__delete_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `recording_id` | yes | `string` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `RecordingDeleteResponse`)
- Error responses:
  - `401`: Candidate authentication required. (schema: `-`)
  - `403`: Candidate does not own session. (schema: `-`)
  - `404`: Recording asset not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "status": "example"
}
```

### `GET /api/trials`
- Summary: List Trials
- Description: List trials for talent_partner dashboard (scoped to current user).
- Auth: Talent Partner bearer token
- Operation ID: `list_trials_api_trials_get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - None
- Query params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `includeTerminated` | no | `boolean` | `False` | - |
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `Response List Trials Api Trials Get`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
[
  {
    "id": 1,
    "title": "example",
    "role": "example",
    "techStack": "example",
    "templateKey": "example",
    "status": "draft",
    "createdAt": "2026-01-01T00:00:00Z",
    "numCandidates": 1
  }
]
```

### `POST /api/trials`
- Summary: Create Trial
- Description: Create a trial and seed default tasks.
- Auth: Talent Partner bearer token
- Operation ID: `create_trial_api_trials_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - None
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `TrialCreate`
- Request example:
```json
{
  "title": "example",
  "role": "example",
  "techStack": "example",
  "seniority": "example",
  "focus": "example"
}
```
- Success responses:
  - `201`: Successful Response (schema: `TrialCreateResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`201`):
```json
{
  "id": 1,
  "title": "example",
  "role": "example",
  "techStack": "example",
  "seniority": "example",
  "focus": "example",
  "templateKey": "example",
  "status": "draft",
  "scenarioGenerationJobId": "example",
  "tasks": [
    {
      "id": 1,
      "day_index": 1,
      "type": "design",
      "title": "example"
    }
  ]
}
```

### `GET /api/trials/{trial_id}`
- Summary: Get Trial Detail
- Description: Return a trial detail view for talent_partners.
- Auth: Talent Partner bearer token
- Operation ID: `get_trial_detail_api_trials__trial_id__get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `TrialDetailResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "id": 1,
  "status": "draft",
  "tasks": [
    {
      "dayIndex": 1
    }
  ]
}
```

### `PUT /api/trials/{trial_id}`
- Summary: Update Trial
- Description: Update mutable trial configuration.
- Auth: Talent Partner bearer token
- Operation ID: `update_trial_api_trials__trial_id__put`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `TrialUpdate`
- Request example:
```json
{
  "ai": {
    "noticeVersion": "example",
    "noticeText": "example",
    "evalEnabledByDay": {
      "key": true
    }
  }
}
```
- Success responses:
  - `200`: Successful Response (schema: `TrialDetailResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "id": 1,
  "status": "draft",
  "tasks": [
    {
      "dayIndex": 1
    }
  ]
}
```

### `POST /api/trials/{trial_id}/activate`
- Summary: Activate Trial
- Description: Transition a trial into the active state once talent_partner confirms readiness.
- Auth: Talent Partner bearer token
- Operation ID: `activate_trial_api_trials__trial_id__activate_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `TrialLifecycleRequest`
- Request example:
```json
{
  "confirm": true
}
```
- Success responses:
  - `200`: Successful Response (schema: `TrialActivateResponse`)
- Error responses:
  - `400`: Activation confirmation missing. (schema: `-`)
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Trial not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "trialId": 1,
  "status": "draft"
}
```

### `GET /api/trials/{trial_id}/candidates`
- Summary: List Trial Candidates
- Description: List candidate sessions for a trial (talent_partner-only).
- Auth: Talent Partner bearer token
- Operation ID: `list_trial_candidates_api_trials__trial_id__candidates_get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `includeTerminated` | no | `boolean` | `False` | - |
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `Response List Trial Candidates Api Trials  Trial Id  Candidates Get`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
[
  {
    "candidateSessionId": 1,
    "inviteEmail": "user@example.com",
    "candidateName": "example",
    "status": "not_started",
    "startedAt": "2026-01-01T00:00:00Z",
    "completedAt": "2026-01-01T00:00:00Z",
    "hasWinoeReport": true
  }
]
```

### `GET /api/trials/{trial_id}/candidates/compare`
- Summary: List Trial Candidates Compare
- Description: Return side-by-side candidate progress and scoring signals for a talent_partner-owned trial.
- Auth: Talent Partner bearer token
- Operation ID: `list_trial_candidates_compare_api_trials__trial_id__candidates_compare_get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `TrialCandidatesCompareResponse`)
- Error responses:
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Trial not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "trialId": 1
}
```

### `POST /api/trials/{trial_id}/candidates/{candidate_session_id}/invite/resend`
- Summary: Resend Candidate Invite
- Description: Resend an existing candidate invite email for a talent_partner-owned trial session.
- Auth: Talent Partner bearer token
- Operation ID: `resend_candidate_invite_api_trials__trial_id__candidates__candidate_session_id__invite_resend_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_notifications_utils.get_email_service`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
  - | `candidate_session_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `-`)
- Error responses:
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Trial or candidate session not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
"example"
```

### `POST /api/trials/{trial_id}/invite`
- Summary: Create Candidate Invite
- Description: Create a candidate_session invite token for a trial (talent_partner-only).
- Auth: Talent Partner bearer token
- Operation ID: `create_candidate_invite_api_trials__trial_id__invite_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_github_client`, `app.shared.http.dependencies.shared_http_dependencies_notifications_utils.get_email_service`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `CandidateInviteRequest`
- Request example:
```json
{
  "candidateName": "example",
  "inviteEmail": "user@example.com"
}
```
- Success responses:
  - `200`: Successful Response (schema: `CandidateInviteResponse`)
- Error responses:
  - `409`: Conflict (schema: `CandidateInviteErrorResponse`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "candidateSessionId": 1,
  "token": "example",
  "inviteUrl": "example",
  "outcome": "created"
}
```

### `PATCH /api/trials/{trial_id}/scenario/active`
- Summary: Update Active Scenario Version
- Description: Update active scenario metadata and assignment fields for the trial.
- Auth: Talent Partner bearer token
- Operation ID: `update_active_scenario_version_api_trials__trial_id__scenario_active_patch`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `ScenarioActiveUpdateRequest`
- Request example:
```json
{
  "storylineMd": "example",
  "taskPromptsJson": {},
  "rubricJson": {}
}
```
- Success responses:
  - `200`: Successful Response (schema: `ScenarioActiveUpdateResponse`)
- Error responses:
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Trial not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "trialId": 1,
  "scenario": {
    "id": 1,
    "versionIndex": 1,
    "status": "example"
  }
}
```

### `POST /api/trials/{trial_id}/scenario/regenerate`
- Summary: Regenerate Scenario Version
- Description: Request a regenerated scenario version for a trial and return the created job reference.
- Auth: Talent Partner bearer token
- Operation ID: `regenerate_scenario_version_api_trials__trial_id__scenario_regenerate_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `ScenarioRegenerateResponse`)
- Error responses:
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Trial not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
  - `429`: Scenario regeneration rate limit exceeded. (schema: `-`)
- Success example (`200`):
```json
{
  "scenarioVersionId": 1,
  "jobId": "example",
  "status": "example"
}
```

### `PATCH /api/trials/{trial_id}/scenario/{scenario_version_id}`
- Summary: Patch Scenario Version
- Description: Patch editable scenario version content and return the updated scenario payload.
- Auth: Talent Partner bearer token
- Operation ID: `patch_scenario_version_api_trials__trial_id__scenario__scenario_version_id__patch`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
  - | `scenario_version_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `ScenarioVersionPatchRequest`
- Request example:
```json
{
  "storylineMd": "example",
  "taskPrompts": [
    {
      "dayIndex": 1,
      "title": "example",
      "description": "example"
    }
  ],
  "rubric": {}
}
```
- Success responses:
  - `200`: Successful Response (schema: `ScenarioVersionPatchResponse`)
- Error responses:
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Trial or scenario version not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "scenarioVersionId": 1,
  "status": "example"
}
```

### `POST /api/trials/{trial_id}/scenario/{scenario_version_id}/approve`
- Summary: Approve Scenario Version
- Description: Approve a scenario version and promote it for active trial usage.
- Auth: Talent Partner bearer token
- Operation ID: `approve_scenario_version_api_trials__trial_id__scenario__scenario_version_id__approve_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
  - | `scenario_version_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `ScenarioApproveResponse`)
- Error responses:
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Trial or scenario version not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "trialId": 1,
  "status": "draft",
  "activeScenarioVersionId": 1,
  "scenario": {
    "id": 1,
    "versionIndex": 1,
    "status": "example"
  }
}
```

### `POST /api/trials/{trial_id}/terminate`
- Summary: Terminate Trial
- Description: Terminate an active trial and enqueue workspace cleanup jobs for associated candidate workspaces.
- Auth: Talent Partner bearer token
- Operation ID: `terminate_trial_api_trials__trial_id__terminate_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `trial_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `TrialLifecycleRequest`
- Request example:
```json
{
  "confirm": true
}
```
- Success responses:
  - `200`: Successful Response (schema: `TrialTerminateResponse`)
- Error responses:
  - `400`: Termination confirmation missing. (schema: `-`)
  - `403`: Talent Partner access required. (schema: `-`)
  - `404`: Trial not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "trialId": 1,
  "status": "draft"
}
```

### `GET /api/submissions`
- Summary: List Submissions Route
- Description: List submissions visible to the talent_partner with optional filters.
- Auth: Talent Partner bearer token
- Operation ID: `list_submissions_route_api_submissions_get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - None
- Query params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `candidateSessionId` | no | `Candidatesessionid` | `-` | - |
  - | `taskId` | no | `Taskid` | `-` | - |
  - | `limit` | no | `Limit` | `-` | - |
  - | `offset` | no | `integer` | `0` | - |
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `Talent PartnerSubmissionListOut`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "items": [
    {
      "submissionId": 1,
      "candidateSessionId": 1,
      "taskId": 1,
      "dayIndex": 1,
      "type": "example",
      "submittedAt": "2026-01-01T00:00:00Z"
    }
  ]
}
```

### `GET /api/submissions/{submission_id}`
- Summary: Get Submission Detail Route
- Description: Return talent_partner-facing detail for a submission.
- Auth: Talent Partner bearer token
- Operation ID: `get_submission_detail_route_api_submissions__submission_id__get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `submission_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `Talent PartnerSubmissionDetailOut`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "submissionId": 1,
  "candidateSessionId": 1,
  "task": {
    "taskId": 1,
    "dayIndex": 1,
    "type": "example"
  },
  "submittedAt": "2026-01-01T00:00:00Z"
}
```

### `POST /api/tasks/{task_id}/codespace/init`
- Summary: Init Codespace Route
- Description: Provision or return a GitHub Codespace workspace for a task.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `init_codespace_route_api_tasks__task_id__codespace_init_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_github_client`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: `CodespaceInitRequest`
- Request example:
```json
{
  "githubUsername": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `CodespaceInitResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "repoFullName": "example",
  "repoUrl": "example",
  "codespaceUrl": "example",
  "workspaceId": "example"
}
```

### `GET /api/tasks/{task_id}/codespace/status`
- Summary: Codespace Status Route
- Description: Return Codespace details and last known test status for a task.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `codespace_status_route_api_tasks__task_id__codespace_status_get`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `CodespaceStatusResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "repoFullName": "example",
  "repoUrl": "example",
  "workspaceId": "example"
}
```

### `GET /api/tasks/{task_id}/draft`
- Summary: Get Task Draft Route
- Description: Return the saved draft payload for a candidate task in the current session context.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `get_task_draft_route_api_tasks__task_id__draft_get`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `TaskDraftResponse`)
- Error responses:
  - `404`: Draft or task not found. (schema: `-`)
  - `409`: Task draft is finalized. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "taskId": 1,
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### `PUT /api/tasks/{task_id}/draft`
- Summary: Put Task Draft Route
- Description: Create or update a candidate task draft while enforcing active-window and finalization constraints.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `put_task_draft_route_api_tasks__task_id__draft_put`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: `TaskDraftUpsertRequest`
- Request example:
```json
{
  "contentText": "example",
  "contentJson": {}
}
```
- Success responses:
  - `200`: Successful Response (schema: `TaskDraftUpsertResponse`)
- Error responses:
  - `404`: Task not found. (schema: `-`)
  - `409`: Task draft is finalized. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "taskId": 1,
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### `GET /api/tasks/{task_id}/handoff/status`
- Summary: Handoff Status Route
- Description: Return the current recording/transcript status for handoff tasks in the candidate session.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `handoff_status_route_api_tasks__task_id__handoff_status_get`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `app.shared.http.dependencies.shared_http_dependencies_storage_media_utils.get_media_storage_provider`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `HandoffStatusResponse`)
- Error responses:
  - `403`: Candidate session access denied. (schema: `-`)
  - `404`: Task or handoff recording not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "recording": {
    "recordingId": "example",
    "status": "example"
  },
  "transcript": {
    "status": "example"
  }
}
```

### `POST /api/tasks/{task_id}/handoff/upload/complete`
- Summary: Complete Handoff Upload Route
- Description: Finalize a previously initialized handoff upload and bind recording metadata to the submission.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `complete_handoff_upload_route_api_tasks__task_id__handoff_upload_complete_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `app.shared.http.dependencies.shared_http_dependencies_storage_media_utils.get_media_storage_provider`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: `HandoffUploadCompleteRequest`
- Request example:
```json
{
  "recordingId": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `HandoffUploadCompleteResponse`)
- Error responses:
  - `403`: Candidate session access denied. (schema: `-`)
  - `404`: Task or upload record not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "recordingId": "example",
  "status": "example"
}
```

### `POST /api/tasks/{task_id}/handoff/upload/init`
- Summary: Init Handoff Upload Route
- Description: Initialize candidate handoff recording upload and return signed upload instructions.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `init_handoff_upload_route_api_tasks__task_id__handoff_upload_init_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `app.shared.http.dependencies.shared_http_dependencies_storage_media_utils.get_media_storage_provider`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: `HandoffUploadInitRequest`
- Request example:
```json
{
  "contentType": "example",
  "sizeBytes": 1
}
```
- Success responses:
  - `200`: Successful Response (schema: `HandoffUploadInitResponse`)
- Error responses:
  - `403`: Candidate session access denied. (schema: `-`)
  - `404`: Task or candidate session not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "recordingId": "example",
  "uploadUrl": "example",
  "expiresInSeconds": 1
}
```

### `POST /api/tasks/{task_id}/run`
- Summary: Run Task Tests Route
- Description: Dispatch GitHub Actions tests for a candidate task.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `run_task_tests_route_api_tasks__task_id__run_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_actions_runner`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_github_client`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: `RunTestsRequest`
- Request example:
```json
{
  "workflowInputs": {},
  "branch": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `RunTestsResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "status": "example"
}
```

### `GET /api/tasks/{task_id}/run/{run_id}`
- Summary: Get Run Result Route
- Description: Poll a previously-triggered workflow run.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `get_run_result_route_api_tasks__task_id__run__run_id__get`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_actions_runner`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_github_client`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
  - | `run_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `RunTestsResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "status": "example"
}
```

### `POST /api/tasks/{task_id}/submit`
- Summary: Submit Task Route
- Description: Submit a task, optionally running GitHub tests for code/debug types.
- Auth: Candidate bearer token (`candidate:access`) plus `x-candidate-session-id`
- Operation ID: `submit_task_route_api_tasks__task_id__submit_post`
- Dependency auth signals: `app.shared.auth.principal.shared_auth_principal_dependencies_utils.get_principal`, `app.shared.auth.shared_auth_candidate_access_utils.require_candidate_principal`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils.candidate_session_from_headers`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_actions_runner`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_github_client`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `task_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `x-candidate-session-id` | no | `X-Candidate-Session-Id` | `-` | - |
- Request schema: `SubmissionCreateRequest`
- Request example:
```json
{
  "contentText": "example",
  "reflection": "example",
  "branch": "example"
}
```
- Success responses:
  - `201`: Successful Response (schema: `SubmissionCreateResponse`)
- Error responses:
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`201`):
```json
{
  "submissionId": 1,
  "taskId": 1,
  "candidateSessionId": 1,
  "submittedAt": "2026-01-01T00:00:00Z",
  "progress": {
    "completed": 1,
    "total": 1
  },
  "isComplete": true
}
```

### `GET /health`
- Summary: Health Check
- Description: Lightweight liveness probe for process and routing health.
- Auth: None
- Operation ID: `health_check_health_get`
- Dependency auth signals: None
- Path params: 
  - None
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `-`)
- Error responses:
  - `500`: Process is unhealthy. (schema: `-`)
- Success example (`200`):
```json
"example"
```

