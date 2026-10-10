# VitalGuard AI — Delivery roadmap and verified scope

> Synthetic data only. This is a software prototype, not a clinically validated medical device or clinical decision-support system.

## Delivered phases

### Phase 1 — Synthetic observation ingestion
- Deterministic stable, worsening, and recovering fictional scenarios.
- Validated ingestion endpoint: `POST /api/v1/demo/observations`.
- Persists the generated observation and synthetic model result.

### Phase 2 — Storage adapter
- SQLAlchemy adapter supports local SQLite and PostgreSQL via private `DATABASE_URL`.
- Schema creation/migration helpers and history indexes.
- **Not complete for production:** a hosted PostgreSQL instance has not been provisioned/connected in the current deployment; SQLite remains the default unless configured.

### Phase 3 — Live event delivery
- WebSocket endpoint: `/api/v1/live`.
- Observation and alert events broadcast after persistence.
- Frontend connection state, heartbeat and reconnect backoff.
- The event hub is in-process and intended for a single backend instance.

### Phase 4 — Alert lifecycle
- Persistent synthetic alerts with deduplication keys.
- Open, acknowledged and resolved states.
- Audit trail for creation and state transitions.

### Phase 5 — Live dashboard alert operations
- Backend alert inbox in Alert Center.
- Refresh, status filters, acknowledge and resolve controls.
- Connection state visible in the app shell.

### Phase 6 — Observation data quality
- `GET /api/v1/observations/quality` classifies recent records as fresh, stale, incomplete or unknown.
- Dashboard panel displays observation age and missing required fields.
- Scope is limited to a bounded history page; it cannot detect devices that never sent a reading.

### Phase 7 — Model evaluation transparency
- `GET /api/v1/model/evaluation` returns deterministic stratified synthetic holdout metrics and a confusion matrix.
- `POST /api/v1/risk/explain` returns standardized logistic-regression coefficient contributions.
- These metrics only measure agreement with generated heuristic labels. Contributions are not SHAP or causal explanations.

### Phase 8 — Explainability workbench
- Settings form sends fictional vitals to the contribution endpoint without saving a prediction.
- Displays the synthetic score and signed coefficient contributions.

### Phase 9 — Persisted history UI
- Dashboard shows recent backend predictions, model versions, timestamps, scores and a patient filter.

### Phase 10 — Release smoke checks
- `npm run smoke:api` exercises health, model metadata, CORS, prediction persistence, synthetic evaluation, explanations, quality status and alert lifecycle/audit.

## Remaining work before any real-world use

1. Provision a managed PostgreSQL database, configure secrets in Render, and verify data survival across restart/redeploy. Define retention, backup, restore, and migration procedures.
2. Implement proper identity and role-based authorization before any sensitive or multi-user workflow. The current demo actor is not authentication.
3. Add durable cross-instance event delivery if scaling beyond one backend instance.
4. Add production-grade observability, request limits, security review, dependency remediation, and operational incident procedures.
5. Keep local synthetic patient lists/charts/analytics visibly separate from backend-persisted observations. Not all dashboard views consume the backend API.
6. Do not claim NEWS2 compliance, SHAP, clinical accuracy, or patient deterioration prediction until implemented from reviewed specifications and evaluated on appropriately authorized, representative data with suitable governance.

## Safety boundary

Never use real patient data. Missing or stale observations are unknown, not normal. Synthetic model metrics do not establish clinical performance, calibration, or safety. This prototype must not be used for diagnosis, triage, or treatment decisions.
