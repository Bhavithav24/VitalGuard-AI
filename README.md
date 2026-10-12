# VitalGuard AI — Patient Monitoring Prototype

> **DEMO ONLY · CONTROLLED REAL-TIME DEMO TELEMETRY · NOT FOR CLINICAL USE**
>
> VitalGuard AI is a software prototype for patient-observation monitoring, review workflows, NEWS2 reference scoring and risk-signal visualisation. The deployed demonstration uses a controlled backend telemetry source that creates demo patient records and continuously emits monitor-style observations through the same persistence and WebSocket path used by authorized ingestion. It is not a clinical device feed and must not be used for patient care.

## What is currently implemented

- React + TypeScript + Vite frontend with Dashboard, Patients, Alerts, Analytics and Settings.
- FastAPI backend with authenticated APIs and server-enforced RBAC for **admin**, **clinician** and **nurse** roles.
- PostgreSQL/SQLite storage adapter with ordered migrations, patient CRUD, observation provenance and idempotent ingestion.
- Protected WebSocket live-event delivery with ticket-based authentication, reconnect handling and optional shared Redis/Valkey Pub/Sub.
- Controlled real-time demo telemetry for four demo patients. The telemetry is deterministic, persisted by the backend and emitted once per minute; it is intentionally presented as a demo source rather than a real clinical device.
- Observation data-quality monitoring, backend observation history, patient timelines, descriptive trends and alert lifecycle/audit workflows.
- NEWS2 parameter scoring reference implementation with explicit completeness and safety checks.
- Historical replay can use the included research-only model. Live observations fail closed to **ML unavailable** because no clinically validated ML model is configured.
- Settings includes the research model/evaluation workbench, NEWS2 calculator and live telemetry source status. Admins can manually trigger a demo telemetry tick.
- No browser-generated random vital signs, no frontend clinical source of truth and no restored "Start Simulation" workflow.

## Requirements

- Node.js 20+ (Node.js 22 recommended)
- npm 10+
- Python 3.11+ (3.12 used by CI)

## Quick start

Frontend:

```bash
npm ci
cp .env.example .env
npm run dev
```

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

The frontend normally runs at `http://localhost:5173`; the backend at `http://localhost:8000`.

## Verification

```bash
npm run lint
npm test
npm run build
PYTHONPATH=backend pytest backend/tests -q
```

Only describe a command as passing after it has actually completed successfully against the current source.

## Environment configuration

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Optional FastAPI base URL; production points to the deployed backend. |
| `VITE_APP_VERSION` | Frontend version label. |
| `DATABASE_URL` | Backend PostgreSQL connection string. |
| `VITALGUARD_DB_PATH` | Local SQLite path used for development/tests when PostgreSQL is not configured. |
| `CORS_ORIGINS` | Allowed frontend origins. |
| `VITALGUARD_DEMO_TELEMETRY_ENABLED` | Enables the controlled deployed demo telemetry loop. Keep disabled for environments that require an external authorized source only. |
| `VITALGUARD_LIVE_SOURCE_TOKEN` | Server-side token for authorized external live ingestion. |
| `REDIS_URL` | Optional Redis/Valkey Pub/Sub transport for multi-instance WebSocket fan-out. |

Secrets belong only in backend/Render environment settings.

## Real-time demo telemetry

The deployed demonstration has a controlled source named `bedside-monitor-demo`. It maintains four demo patients and emits a new observation every minute.

The flow is:

```text
controlled demo source
        ↓
validated ingestion
        ↓
PostgreSQL persistence
        ↓
NEWS2 reference calculation
        ↓
WebSocket event
        ↓
frontend dashboard / patient history / quality views
```

The observations are not browser-generated and do not come from a real bedside device. They are deliberately deterministic and bounded so that the demo is repeatable and does not pretend to have a clinical device connection.

The admin-only Settings action **Emit telemetry now** uses the same backend path and is useful for demonstrating the real-time update flow without waiting for the next minute.

## Risk and model boundary

The included research model is a StandardScaler + LogisticRegression classifier trained on generated research data. It is **not XGBoost, not clinically validated and not a clinical risk model**.

Therefore:

- historical replay may display the research model with an explicit research-only disclaimer;
- live/demo telemetry stores `risk_score=null` and displays **ML unavailable**;
- no live clinical risk score is fabricated just to make the dashboard look populated;
- NEWS2 is displayed separately when complete inputs are available and is still a reference implementation requiring local clinical verification;
- SHAP/clinical explainability is not claimed when a validated live model is unavailable.

## Patient and alert workflows

Protected patient APIs support creation, listing, detail, update and deactivation while preserving historical observations.

Alert lifecycle is server-authoritative:

```text
open → acknowledged → assigned → resolved
```

Each transition is audited. Patient scope and role permissions are enforced by the backend.

## Deployment

Current deployed services for the Bhavithav24 project:

- Frontend: `vitalguard-ai-bhavithav.onrender.com`
- Backend: `vitalguard-risk-api-bhavithav.onrender.com`
- PostgreSQL: Render-managed project database

The deployment is a demonstration/staging environment. Production clinical use remains blocked until real authorized identity, real device/data integration, clinical validation, privacy/security/compliance review, durable backups and appropriate hosting are completed and verified.

## Project layout

```text
backend/app/
  main.py                 FastAPI application and lifecycle
  auth.py                 Authentication, roles and patient scope
  patient_routes.py       Patient CRUD
  ingestion_routes.py     Validated observation ingestion
  demo_telemetry.py       Controlled real-time demo source
  live_events.py          Authenticated WebSocket fan-out
  storage.py              SQLite/PostgreSQL storage adapter
  migrations.py           Ordered database migrations
  alert_service.py        Alert lifecycle and audit persistence
  alert_routes.py         Alert API
  news2.py                NEWS2 reference scoring
  model.py                Research-only synthetic model
  timeline_routes.py      Patient timeline API
  trend_routes.py         Descriptive trend API

src/
  pages/                  Dashboard, Patients, Alerts, Analytics, Settings
  components/             UI, charts, monitoring and workflow panels
  services/               API, authentication and WebSocket clients
  store/                  Backend-authoritative application state

backend/tests/
  patient, auth/RBAC, ingestion, WebSocket, alert, migration,
  data-quality, NEWS2, resilience and persistence coverage
```

## Release gates still requiring verification

The engineering implementation is substantially complete, but these are **verification gates**, not reasons to fake completion:

1. GitHub Actions CI/E2E must finish successfully for the latest commit.
2. Render must finish the latest backend/frontend deployments.
3. Hosted PostgreSQL persistence must be verified directly; the Render database currently requires the appropriate access/allowlist path for an external direct query.
4. Final browser verification should confirm login, four demo patients, fresh telemetry, WebSocket updates, patient detail/history, alert lifecycle and responsive UI.

Until those gates are confirmed, the project should be described as a deployed demonstration/staging prototype rather than a production clinical system.
