from contextlib import asynccontextmanager
import os
import uuid
import threading
import time
from collections import Counter
from fastapi import FastAPI, Query, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from .model import MODEL_VERSION, explain, predict_probability, risk_level
from .model_evaluation import coefficient_contributions, evaluate_synthetic_holdout
from .validation_diagnostics import evaluate_synthetic_calibration_and_subgroups
from .explanation_validation import validate_additive_explanation
from .news2 import score_news2
from .schemas import NEWS2Input, RiskPrediction, VitalInput
from .timeline_routes import router as timeline_router
from .trend_routes import router as trend_router
from .alert_routes import router as alert_router
from .alert_service import create_alert
from .data_quality import assess_observations
from .live_events import hub
from .storage import database_health, initialize_storage, list_observations, save_observation
from .auth import router as auth_router, authenticate_principal, require_roles, require_patient_access, patient_scope_prefixes, _consume_ws_ticket, validate_access_token
from .ingestion_routes import router as ingestion_router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_storage()
    await hub.start()
    try:
        yield
    finally:
        await hub.stop()

app = FastAPI(title="VitalGuard AI Risk Engine", version="0.8.0",
    description="VitalGuard AI clinical monitoring prototype API. No live clinical source is bundled; only authorized ingestion and explicit historical replay are accepted.", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(ingestion_router)
app.include_router(alert_router)
app.include_router(timeline_router)
app.include_router(trend_router)
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_origins = os.getenv("CORS_ORIGINS", ",".join(_default_origins))
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in _origins.split(",") if origin.strip()],
    allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Process-local operational counters. Never store query strings, patient IDs, or request bodies.
_metrics_lock = threading.Lock()
_request_count = 0
_status_counts: Counter[str] = Counter()
_route_counts: Counter[str] = Counter()
_latency_total_ms = 0.0
_latency_max_ms = 0.0

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Record privacy-safe process metrics and attach baseline security headers."""
    global _request_count, _latency_total_ms, _latency_max_ms
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    route = request.scope.get("route")
    route_label = getattr(route, "path", "unmatched")
    route_label = "/".join("{param}" if segment.startswith("{") and segment.endswith("}") else segment for segment in route_label.split("/"))
    with _metrics_lock:
        _request_count += 1
        _status_counts[str(response.status_code)] += 1
        _route_counts[route_label] += 1
        _latency_total_ms += elapsed_ms
        _latency_max_ms = max(_latency_max_ms, elapsed_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Request-ID"] = str(uuid.uuid4())
    return response

async def _publish_observation(patient_id: str, values: dict, result: RiskPrediction, saved: dict) -> None:
    await hub.broadcast({"type": "observation.created", "event_id": saved["id"],
        "patient_id": patient_id, "created_at": saved["created_at"], "observation": values,
        "prediction": result.model_dump(), "demo_only": True})

def _maybe_create_alert(patient_id: str, score: int, level: str, observation_id: int, values: dict):
    if score < 65:
        return None
    return create_alert(patient_id=patient_id, event_key=f"observation:{observation_id}:elevated-risk",
        severity="critical" if level == "critical" else "high", title=f"{level.title()} research risk signal",
        details={"observation_id": observation_id, "risk_score": score, "risk_level": level, "vitals": values, "demo_only": True})

@app.get("/")
def root():
    return {"service": "VitalGuard AI Risk Engine", "status": "ok", "docs": "/docs", "health": "/health", "demo_only": True}

@app.get("/health")
def health():
    try:
        database = database_health()
        return {"status": "ok", "model_version": MODEL_VERSION, "database": database, "websocket": "available", "demo_only": True}
    except Exception:
        raise HTTPException(status_code=503, detail="Database health check failed")

@app.get("/api/v1/ops/readiness")
def operational_readiness(principal: dict = Depends(authenticate_principal)):
    """Authenticated, secret-free operational readiness snapshot for the demo."""
    try:
        database = database_health()
        database_status = "ok"
    except Exception:
        database = {"status": "unavailable"}
        database_status = "unavailable"
    auth_configured = bool(os.getenv("VITALGUARD_AUTH_SECRET", "").strip()) and (
        bool(os.getenv("VITALGUARD_AUTH_USERS_JSON", "").strip()) or
        (bool(os.getenv("VITALGUARD_AUTH_USERNAME", "").strip()) and
         bool(os.getenv("VITALGUARD_AUTH_PASSWORD", "").strip() or os.getenv("VITALGUARD_AUTH_PASSWORD_HASH", "").strip()))
    )
    ready = database_status == "ok" and auth_configured
    return {
        "status": "ready" if ready else "degraded",
        "checks": {
            "api": "ok",
            "database": database_status,
            "auth_configured": auth_configured,
            "model_loaded": True,
            "validated_ml_available": False,
            "websocket_transport": hub.transport,
        },
        "database_backend": database.get("backend", "unknown"),
        "model_version": MODEL_VERSION,
        "demo_only": True,
        "clinically_validated": False,
        "notes": [
            "Backend-authoritative data; no clinical-use readiness is implied.",
            "Real-time transport uses shared Redis/Valkey Pub/Sub when REDIS_URL is configured; REST history remains the recovery path.",
        ],
    }


@app.get("/api/v1/ops/metrics")
def operational_metrics(principal: dict = Depends(require_roles("admin", "clinician"))):
    """Return bounded-cardinality, process-local metrics without request data."""
    with _metrics_lock:
        count = _request_count
        return {
            "request_count": count,
            "status_counts": dict(_status_counts),
            "route_counts": dict(_route_counts),
            "latency_ms": {
                "count": count,
                "mean": round(_latency_total_ms / count, 2) if count else 0.0,
                "max": round(_latency_max_ms, 2),
            },
            "scope": "current_process_since_startup",
            "demo_only": True,
            "note": "Process-local counters reset on restart and are not a durable monitoring system.",
        }


@app.websocket("/api/v1/live")
async def live_socket(websocket: WebSocket, ticket: str | None = Query(default=None, min_length=20, max_length=256)):
    try:
        if not ticket:
            raise HTTPException(status_code=401, detail="WebSocket ticket required")
        access_token = _consume_ws_ticket(ticket)
        principal = validate_access_token(access_token)
    except HTTPException:
        await websocket.close(code=1008, reason="Authentication required")
        return
    await hub.serve(websocket, principal["scope"])

@app.get("/api/v1/model/info")
def model_info(principal: dict = Depends(authenticate_principal)):
    return {"name": "VitalGuard synthetic risk classifier", "model_version": MODEL_VERSION,
        "algorithm": "StandardScaler + LogisticRegression",
        "features": ["age", "heart_rate", "spo2", "systolic_bp", "diastolic_bp", "temperature", "respiratory_rate"],
        "training_data": "generated synthetic observations only", "demo_only": True, "clinically_validated": False}

@app.post("/api/v1/scores/news2")
def calculate_news2(payload: NEWS2Input, principal: dict = Depends(require_roles("admin", "clinician"))):
    """Calculate parameter points for a fictional NEWS2 example; not clinical guidance."""
    return score_news2(payload.model_dump(exclude={"patient_id", "scale2_authorized"}))

@app.get("/api/v1/model/evaluation")
def model_evaluation(principal: dict = Depends(authenticate_principal)):
    return evaluate_synthetic_holdout()

@app.get("/api/v1/model/validation-diagnostics")
def model_validation_diagnostics(principal: dict = Depends(authenticate_principal)):
    """Synthetic-only calibration and age-band diagnostics; never clinical evidence."""
    return evaluate_synthetic_calibration_and_subgroups()

@app.post("/api/v1/risk/predict", response_model=RiskPrediction)
def predict(_payload: VitalInput, _principal: dict = Depends(require_roles("admin", "clinician"))):
    raise HTTPException(
        status_code=503,
        detail="No clinically validated ML model is configured. Use authorized ingestion; NEWS2 is available separately when complete clinical inputs are supplied.",
    )

@app.post("/api/v1/risk/explain")
def explain_risk(_payload: VitalInput, _principal: dict = Depends(require_roles("admin", "clinician", "nurse"))):
    raise HTTPException(
        status_code=503,
        detail="Model explanations are unavailable because no clinically validated ML model is configured.",
    )

@app.get("/api/v1/observations")
def observation_history(patient_id: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=50, ge=1, le=100), before_id: int | None = Query(default=None, ge=1), principal: dict = Depends(authenticate_principal)):
    if patient_id:
        require_patient_access(patient_id, principal)
    records = list_observations(patient_id=patient_id, limit=limit, before_id=before_id, patient_prefixes=patient_scope_prefixes(principal))
    next_cursor = records[-1]["id"] if len(records) == limit else None
    return {"items": records, "count": len(records), "limit": limit, "next_before_id": next_cursor,
        "demo_only": True, "disclaimer": "Backend-persisted observations. Historical replay may contain explicitly labelled research data; live observations require an authorized source."}

@app.get("/api/v1/observations/quality")
def observation_quality(patient_id: str | None = Query(default=None, min_length=1, max_length=64),
    stale_after_seconds: int = Query(default=300, ge=30, le=86400),
    limit: int = Query(default=100, ge=1, le=100), principal: dict = Depends(authenticate_principal)):
    if patient_id:
        require_patient_access(patient_id, principal)
    records = list_observations(
        patient_id=patient_id,
        limit=limit,
        patient_prefixes=None if patient_id else patient_scope_prefixes(principal),
    )
    return assess_observations(records, stale_after_seconds=stale_after_seconds)
