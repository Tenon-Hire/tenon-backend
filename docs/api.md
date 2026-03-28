# API Reference

Generated from FastAPI OpenAPI plus dependency-based auth mapping.
Generated at: 2026-03-27T14:41:43.988295+00:00
Total endpoints: 46

## Endpoint Index

- `POST /api/admin/candidate_sessions/{candidate_session_id}/reset`: Reset Candidate Session
- `POST /api/admin/jobs/{job_id}/requeue`: Requeue Job
- `POST /api/admin/media/purge`: Purge Media Retention
- `POST /api/admin/simulations/{simulation_id}/scenario/use_fallback`: Use Simulation Fallback
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
- `GET /api/candidate_sessions/{candidate_session_id}/fit_profile`: Get Fit Profile Route
- `POST /api/candidate_sessions/{candidate_session_id}/fit_profile/generate`: Generate Fit Profile Route
- `POST /api/github/webhooks`: Receive Github Webhook
- `GET /api/jobs/{job_id}`: Get Job Status
- `POST /api/recordings/{recording_id}/delete`: Delete Recording Route
- `GET /api/simulations`: List Simulations
- `POST /api/simulations`: Create Simulation
- `GET /api/simulations/{simulation_id}`: Get Simulation Detail
- `PUT /api/simulations/{simulation_id}`: Update Simulation
- `POST /api/simulations/{simulation_id}/activate`: Activate Simulation
- `GET /api/simulations/{simulation_id}/candidates`: List Simulation Candidates
- `GET /api/simulations/{simulation_id}/candidates/compare`: List Simulation Candidates Compare
- `POST /api/simulations/{simulation_id}/candidates/{candidate_session_id}/invite/resend`: Resend Candidate Invite
- `POST /api/simulations/{simulation_id}/invite`: Create Candidate Invite
- `PATCH /api/simulations/{simulation_id}/scenario/active`: Update Active Scenario Version
- `POST /api/simulations/{simulation_id}/scenario/regenerate`: Regenerate Scenario Version
- `PATCH /api/simulations/{simulation_id}/scenario/{scenario_version_id}`: Patch Scenario Version
- `POST /api/simulations/{simulation_id}/scenario/{scenario_version_id}/approve`: Approve Scenario Version
- `POST /api/simulations/{simulation_id}/terminate`: Terminate Simulation
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
- Auth: Bearer token for demo admin allowlist (requires `TENON_DEMO_MODE=true`)
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
- Auth: Bearer token for demo admin allowlist (requires `TENON_DEMO_MODE=true`)
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
- Auth: Bearer token for demo admin allowlist (requires `TENON_DEMO_MODE=true`)
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

### `POST /api/admin/simulations/{simulation_id}/scenario/use_fallback`
- Summary: Use Simulation Fallback
- Description: Apply a fallback scenario version to a simulation when generated content must be overridden in demo mode.
- Auth: Bearer token for demo admin allowlist (requires `TENON_DEMO_MODE=true`)
- Operation ID: `use_simulation_fallback_api_admin_simulations__simulation_id__scenario_use_fallback_post`
- Dependency auth signals: `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_admin_demo_utils.require_demo_mode_admin`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `SimulationFallbackRequest`
- Request example:
```json
{
  "scenarioVersionId": 1,
  "reason": "example"
}
```
- Success responses:
  - `200`: Successful Response (schema: `SimulationFallbackResponse`)
- Error responses:
  - `400`: Fallback request is invalid. (schema: `-`)
  - `403`: Admin access required. (schema: `-`)
  - `404`: Demo mode disabled or simulation not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "simulationId": 1,
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
- Description: Return the authenticated recruiter profile for the caller.
- Auth: Recruiter bearer token
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
    "simulationId": 1,
    "simulationTitle": "example",
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
  "simulation": {
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
  "simulation": {
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

### `GET /api/candidate_sessions/{candidate_session_id}/fit_profile`
- Summary: Get Fit Profile Route
- Description: Return fit-profile generation status and latest report payload for a recruiter-visible candidate session.
- Auth: Recruiter bearer token
- Operation ID: `get_fit_profile_route_api_candidate_sessions__candidate_session_id__fit_profile_get`
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
  - `200`: Successful Response (schema: `FitProfileStatusResponse`)
- Error responses:
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Candidate session not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "status": "not_started"
}
```

### `POST /api/candidate_sessions/{candidate_session_id}/fit_profile/generate`
- Summary: Generate Fit Profile Route
- Description: Queue or compute fit-profile artifacts for a candidate session visible to the authenticated recruiter.
- Auth: Recruiter bearer token
- Operation ID: `generate_fit_profile_route_api_candidate_sessions__candidate_session_id__fit_profile_generate_post`
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
  - `202`: Successful Response (schema: `FitProfileGenerateResponse`)
- Error responses:
  - `403`: Recruiter access required. (schema: `-`)
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

### `GET /api/simulations`
- Summary: List Simulations
- Description: List simulations for recruiter dashboard (scoped to current user).
- Auth: Recruiter bearer token
- Operation ID: `list_simulations_api_simulations_get`
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
  - `200`: Successful Response (schema: `Response List Simulations Api Simulations Get`)
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

### `POST /api/simulations`
- Summary: Create Simulation
- Description: Create a simulation and seed default tasks.
- Auth: Recruiter bearer token
- Operation ID: `create_simulation_api_simulations_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - None
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `SimulationCreate`
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
  - `201`: Successful Response (schema: `SimulationCreateResponse`)
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

### `GET /api/simulations/{simulation_id}`
- Summary: Get Simulation Detail
- Description: Return a simulation detail view for recruiters.
- Auth: Recruiter bearer token
- Operation ID: `get_simulation_detail_api_simulations__simulation_id__get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `SimulationDetailResponse`)
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

### `PUT /api/simulations/{simulation_id}`
- Summary: Update Simulation
- Description: Update mutable simulation configuration.
- Auth: Recruiter bearer token
- Operation ID: `update_simulation_api_simulations__simulation_id__put`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `SimulationUpdate`
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
  - `200`: Successful Response (schema: `SimulationDetailResponse`)
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

### `POST /api/simulations/{simulation_id}/activate`
- Summary: Activate Simulation
- Description: Transition a simulation into the active state once recruiter confirms readiness.
- Auth: Recruiter bearer token
- Operation ID: `activate_simulation_api_simulations__simulation_id__activate_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `SimulationLifecycleRequest`
- Request example:
```json
{
  "confirm": true
}
```
- Success responses:
  - `200`: Successful Response (schema: `SimulationActivateResponse`)
- Error responses:
  - `400`: Activation confirmation missing. (schema: `-`)
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Simulation not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "simulationId": 1,
  "status": "draft"
}
```

### `GET /api/simulations/{simulation_id}/candidates`
- Summary: List Simulation Candidates
- Description: List candidate sessions for a simulation (recruiter-only).
- Auth: Recruiter bearer token
- Operation ID: `list_simulation_candidates_api_simulations__simulation_id__candidates_get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
- Query params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `includeTerminated` | no | `boolean` | `False` | - |
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `Response List Simulation Candidates Api Simulations  Simulation Id  Candidates Get`)
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
    "hasFitProfile": true
  }
]
```

### `GET /api/simulations/{simulation_id}/candidates/compare`
- Summary: List Simulation Candidates Compare
- Description: Return side-by-side candidate progress and scoring signals for a recruiter-owned simulation.
- Auth: Recruiter bearer token
- Operation ID: `list_simulation_candidates_compare_api_simulations__simulation_id__candidates_compare_get`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `SimulationCandidatesCompareResponse`)
- Error responses:
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Simulation not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "simulationId": 1
}
```

### `POST /api/simulations/{simulation_id}/candidates/{candidate_session_id}/invite/resend`
- Summary: Resend Candidate Invite
- Description: Resend an existing candidate invite email for a recruiter-owned simulation session.
- Auth: Recruiter bearer token
- Operation ID: `resend_candidate_invite_api_simulations__simulation_id__candidates__candidate_session_id__invite_resend_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_notifications_utils.get_email_service`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
  - | `candidate_session_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `-`)
- Error responses:
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Simulation or candidate session not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
"example"
```

### `POST /api/simulations/{simulation_id}/invite`
- Summary: Create Candidate Invite
- Description: Create a candidate_session invite token for a simulation (recruiter-only).
- Auth: Recruiter bearer token
- Operation ID: `create_candidate_invite_api_simulations__simulation_id__invite_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `app.shared.http.dependencies.shared_http_dependencies_github_native_utils.get_github_client`, `app.shared.http.dependencies.shared_http_dependencies_notifications_utils.get_email_service`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
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

### `PATCH /api/simulations/{simulation_id}/scenario/active`
- Summary: Update Active Scenario Version
- Description: Update active scenario metadata and assignment fields for the simulation.
- Auth: Recruiter bearer token
- Operation ID: `update_active_scenario_version_api_simulations__simulation_id__scenario_active_patch`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
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
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Simulation not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "simulationId": 1,
  "scenario": {
    "id": 1,
    "versionIndex": 1,
    "status": "example"
  }
}
```

### `POST /api/simulations/{simulation_id}/scenario/regenerate`
- Summary: Regenerate Scenario Version
- Description: Request a regenerated scenario version for a simulation and return the created job reference.
- Auth: Recruiter bearer token
- Operation ID: `regenerate_scenario_version_api_simulations__simulation_id__scenario_regenerate_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `ScenarioRegenerateResponse`)
- Error responses:
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Simulation not found. (schema: `-`)
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

### `PATCH /api/simulations/{simulation_id}/scenario/{scenario_version_id}`
- Summary: Patch Scenario Version
- Description: Patch editable scenario version content and return the updated scenario payload.
- Auth: Recruiter bearer token
- Operation ID: `patch_scenario_version_api_simulations__simulation_id__scenario__scenario_version_id__patch`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
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
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Simulation or scenario version not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "scenarioVersionId": 1,
  "status": "example"
}
```

### `POST /api/simulations/{simulation_id}/scenario/{scenario_version_id}/approve`
- Summary: Approve Scenario Version
- Description: Approve a scenario version and promote it for active simulation usage.
- Auth: Recruiter bearer token
- Operation ID: `approve_scenario_version_api_simulations__simulation_id__scenario__scenario_version_id__approve_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
  - | `scenario_version_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: None
- Success responses:
  - `200`: Successful Response (schema: `ScenarioApproveResponse`)
- Error responses:
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Simulation or scenario version not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "simulationId": 1,
  "status": "draft",
  "activeScenarioVersionId": 1,
  "scenario": {
    "id": 1,
    "versionIndex": 1,
    "status": "example"
  }
}
```

### `POST /api/simulations/{simulation_id}/terminate`
- Summary: Terminate Simulation
- Description: Terminate an active simulation and enqueue workspace cleanup jobs for associated candidate workspaces.
- Auth: Recruiter bearer token
- Operation ID: `terminate_simulation_api_simulations__simulation_id__terminate_post`
- Dependency auth signals: `app.shared.auth.dependencies.shared_auth_dependencies_current_user_utils.get_current_user`, `app.shared.database.get_session`, `fastapi.security.http.unknown`
- Path params: 
  - | Name | Required | Type | Default | Description |
  - |---|---:|---|---|---|
  - | `simulation_id` | yes | `integer` | `-` | - |
- Query params: 
  - None
- Header params: 
  - None
- Request schema: `SimulationLifecycleRequest`
- Request example:
```json
{
  "confirm": true
}
```
- Success responses:
  - `200`: Successful Response (schema: `SimulationTerminateResponse`)
- Error responses:
  - `400`: Termination confirmation missing. (schema: `-`)
  - `403`: Recruiter access required. (schema: `-`)
  - `404`: Simulation not found. (schema: `-`)
  - `422`: Validation Error (schema: `HTTPValidationError`)
- Success example (`200`):
```json
{
  "simulationId": 1,
  "status": "draft"
}
```

### `GET /api/submissions`
- Summary: List Submissions Route
- Description: List submissions visible to the recruiter with optional filters.
- Auth: Recruiter bearer token
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
  - `200`: Successful Response (schema: `RecruiterSubmissionListOut`)
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
- Description: Return recruiter-facing detail for a submission.
- Auth: Recruiter bearer token
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
  - `200`: Successful Response (schema: `RecruiterSubmissionDetailOut`)
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

