"""Controlled demo telemetry source for the deployed demonstration environment.

This is not a clinical source. It creates clearly identified demo patients and emits
time-varying monitor-style observations through the same durable ingestion store and
WebSocket broadcast path used by authorized live sources. It is disabled unless the
explicit demo feature flag is enabled.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from .auth import require_roles
from .ingestion_store import persist_ingested_observation
from .live_events import hub
from .schemas import RiskPrediction, VitalInput
from .storage import _engine
from .storage_schema import patients

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

DEMO_PATIENTS = [
    {"patient_id": "DEMO-001", "external_identifier": "VG-DEMO-001", "display_name": "Demo Patient 01", "age": 42, "sex": "F", "unit": "Demo Ward A", "bed": "A-01"},
    {"patient_id": "DEMO-002", "external_identifier": "VG-DEMO-002", "display_name": "Demo Patient 02", "age": 57, "sex": "M", "unit": "Demo Ward A", "bed": "A-02"},
    {"patient_id": "DEMO-003", "external_identifier": "VG-DEMO-003", "display_name": "Demo Patient 03", "age": 68, "sex": "F", "unit": "Demo Ward B", "bed": "B-01"},
    {"patient_id": "DEMO-004", "external_identifier": "VG-DEMO-004", "display_name": "Demo Patient 04", "age": 31, "sex": "M", "unit": "Demo Ward B", "bed": "B-02"},
]

def _ensure_demo_patients() -> None:
    engine = _engine()
    try:
        now = datetime.now(timezone.utc)
        with engine.begin() as connection:
            for patient in DEMO_PATIENTS:
                existing = connection.execute(select(patients).where(patients.c.patient_id == patient["patient_id"])).mappings().first()
                if existing is None:
                    connection.execute(patients.insert().values(**patient, active=True, created_at=now, updated_at=now))
                elif not existing["active"]:
                    connection.execute(patients.update().where(patients.c.patient_id == patient["patient_id"]).values(active=True, deactivated_at=None, updated_at=now))
    finally:
        engine.dispose()

def _vitals(profile: int, step: int, age: int) -> dict:
    # Deterministic monitor-style variation; no random clinical values are generated.
    phase = step % 12
    shifts = [0, 1, 0, -1, 1, 2, 1, 0, -1, 0, 1, 0]
    shift = shifts[(phase + profile) % len(shifts)]
    base = [
        {"heart_rate": 78, "spo2": 98, "systolic_bp": 122, "diastolic_bp": 78, "temperature": 36.8, "respiratory_rate": 15},
        {"heart_rate": 88, "spo2": 96, "systolic_bp": 130, "diastolic_bp": 82, "temperature": 37.1, "respiratory_rate": 18},
        {"heart_rate": 96, "spo2": 94, "systolic_bp": 116, "diastolic_bp": 74, "temperature": 37.5, "respiratory_rate": 21},
        {"heart_rate": 72, "spo2": 99, "systolic_bp": 118, "diastolic_bp": 76, "temperature": 36.6, "respiratory_rate": 14},
    ][profile]
    return {"patient_id": DEMO_PATIENTS[profile]["patient_id"], "age": age,
            **{k: round(v + shift, 1) if isinstance(v, float) else v + shift for k, v in base.items()},
            "consciousness": "alert", "supplemental_oxygen": False, "spo2_scale": 1, "scale2_authorized": False}

@router.post("/telemetry/tick")
async def telemetry_tick(principal: dict = Depends(require_roles("admin"))):
    if os.getenv("VITALGUARD_DEMO_TELEMETRY_ENABLED", "").strip().lower() != "true":
        raise HTTPException(status_code=404, detail="Demo telemetry is disabled")
    _ensure_demo_patients()
    now = datetime.now(timezone.utc)
    step = int(now.timestamp() // 60)
    emitted = []
    units = {"age": "years", "heart_rate": "bpm", "spo2": "percent", "systolic_bp": "mmHg", "diastolic_bp": "mmHg", "temperature": "degC", "respiratory_rate": "breaths/min"}
    for profile, patient in enumerate(DEMO_PATIENTS):
        values = _vitals(profile, step, patient["age"])
        vital = VitalInput.model_validate(values)
        prediction = RiskPrediction(
            patient_id=patient["patient_id"], risk_score=None, risk_level="unavailable",
            model_probability=None, factors=[], model_version="unavailable",
            news2=None, demo_only=False, ml_available=False,
            disclaimer="No clinically validated ML model is configured for live observations. This demonstration source supplies monitor-style telemetry only.",
        )
        event_id = f"demo-monitor-{step}-{patient['patient_id']}"
        payload = {"source_system": "bedside-monitor-demo", "source_mode": "live", "source_event_id": event_id,
                   "observed_at": now.isoformat(), "observation": vital.model_dump(), "units": units}
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        persisted = persist_ingested_observation(
            source_system="bedside-monitor-demo", source_mode="live", source_event_id=event_id,
            patient_id=patient["patient_id"], observed_at=now, units=units, payload_hash=payload_hash,
            inputs=vital.model_dump(exclude={"patient_id"}), prediction=prediction.model_dump(),
        )
        if persisted["status"] in {"accepted", "duplicate"}:
            emitted.append({"patient_id": patient["patient_id"], "status": persisted["status"], "observation_id": persisted["observation_id"]})
        if persisted["status"] == "accepted":
            response = prediction.model_copy(update={"observation_id": persisted["observation_id"], "created_at": now.isoformat()})
            await hub.broadcast({
                "type": "observation.created", "event_id": persisted["observation_id"],
                "patient_id": patient["patient_id"], "observed_at": now.isoformat(),
                "observation": vital.model_dump(exclude={"patient_id"}), "prediction": response.model_dump(),
                "source_system": "bedside-monitor-demo", "source_mode": "live",
            })
    return {"status": "ok", "source_system": "bedside-monitor-demo", "source_mode": "live", "patients": len(DEMO_PATIENTS), "emitted": emitted}
