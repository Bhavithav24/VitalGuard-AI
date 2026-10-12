from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from auth_helpers import authenticate_test_client


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "ingestion.sqlite3"))
    with TestClient(app) as test_client:
        authenticate_test_client(test_client)
        created=test_client.post("/api/v1/patients",json={"patient_id":"DEMO-INGEST-001","external_identifier":"EXT-DEMO-INGEST-001","display_name":"Ingestion Test Patient","age":58,"sex":"M","unit":"Test","bed":"T-01"})
        assert created.status_code == 201
        yield test_client


def item(event_id="source-event-001", **updates):
    payload = {
        "source_system": "synthetic-demo",
        "source_mode": "historical_replay",
        "source_event_id": event_id,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "observation": {
            "patient_id": "DEMO-INGEST-001",
            "age": 58,
            "heart_rate": 82,
            "spo2": 98,
            "systolic_bp": 122,
            "diastolic_bp": 78,
            "temperature": 37.0,
            "respiratory_rate": 16,
        },
        "units": {
            "age": "years",
            "heart_rate": "bpm",
            "spo2": "percent",
            "systolic_bp": "mmHg",
            "diastolic_bp": "mmHg",
            "temperature": "degC",
            "respiratory_rate": "breaths/min",
        },
    }
    payload.update(updates)
    return payload


def test_batch_ingestion_accepts_valid_record_and_persists_provenance(client):
    response = client.post("/api/v1/ingestion/batch", json={"records": [item()]})
    assert response.status_code == 200
    body = response.json()
    assert (body["accepted"], body["duplicates"], body["rejected"]) == (1, 0, 0)
    record = body["items"][0]
    assert record["status"] == "accepted"
    assert record["observation_id"] > 0
    assert record["source_event_id"] == "source-event-001"
    assert record["source_mode"] == "historical_replay"
    history = client.get("/api/v1/observations", params={"patient_id": "DEMO-INGEST-001"}).json()
    prediction = history["items"][0]["prediction"]
    assert prediction["demo_only"] is True
    assert prediction["ml_available"] is True
    assert prediction["disclaimer"].startswith("Historical replay research signal only")


def test_batch_ingestion_is_idempotent_for_same_source_event(client):
    payload = {"records": [item()]}
    first = client.post("/api/v1/ingestion/batch", json=payload)
    second = client.post("/api/v1/ingestion/batch", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["items"][0]["observation_id"] == second.json()["items"][0]["observation_id"]
    assert second.json()["duplicates"] == 1
    assert second.json()["accepted"] == 0


def test_batch_ingestion_keeps_valid_records_when_peer_is_invalid(client):
    valid = item("valid-event")
    invalid = item("invalid-event", units={"heart_rate": "beats"})
    response = client.post("/api/v1/ingestion/batch", json={"records": [valid, invalid]})
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 1
    assert body["rejected"] == 1
    assert body["items"][1]["status"] == "rejected"
    assert body["items"][1]["errors"]


@pytest.mark.parametrize("change", [
    {"observation": {"patient_id": "DEMO-INGEST-001", "age": 58, "heart_rate": -1, "spo2": 98,
        "systolic_bp": 122, "diastolic_bp": 78, "temperature": 37, "respiratory_rate": 16}},
    {"observed_at": "2026-10-11T10:00:00"},
    {"source_system": "hospital feed"},
])
def test_batch_ingestion_rejects_invalid_source_or_observation_metadata(client, change):
    response = client.post("/api/v1/ingestion/batch", json={"records": [item("bad-event", **change)]})
    assert response.status_code == 200
    assert response.json()["rejected"] == 1
    assert response.json()["items"][0]["status"] == "rejected"


def test_batch_ingestion_creates_alert_for_high_risk_observation(client):
    payload=item("high-risk-event",observation={**item()["observation"],"spo2":82,"heart_rate":145,"respiratory_rate":28})
    response=client.post("/api/v1/ingestion/batch",json={"records":[payload]})
    assert response.status_code==200
    assert response.json()["accepted"]==1
    alerts=client.get("/api/v1/alerts").json()["items"]
    assert any(a["patient_id"]=="DEMO-INGEST-001" and a["severity"] in {"high","critical"} for a in alerts)


def test_live_ingestion_requires_authorized_source_token(client, monkeypatch):
    monkeypatch.delenv("VITALGUARD_LIVE_SOURCE_TOKEN", raising=False)
    payload = item("live-event", source_mode="live")
    response = client.post("/api/v1/ingestion/batch", json={"records": [payload]})
    assert response.status_code == 200
    assert response.json()["rejected"] == 1
    assert response.json()["items"][0]["status"] == "rejected"


def test_live_ingestion_with_authorized_source_never_generates_synthetic_ml(client, monkeypatch):
    monkeypatch.setenv("VITALGUARD_LIVE_SOURCE_TOKEN", "test-live-source-token")
    payload = item("authorized-live-event", source_mode="live")
    response = client.post("/api/v1/ingestion/batch", headers={"X-Source-Token": "test-live-source-token"}, json={"records": [payload]})
    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    history = client.get("/api/v1/observations", params={"patient_id": "DEMO-INGEST-001"}).json()
    prediction = history["items"][0]["prediction"]
    assert prediction["risk_score"] is None
    assert prediction["risk_level"] == "unavailable"
    assert prediction["model_probability"] is None
    assert prediction["ml_available"] is False
    assert prediction["demo_only"] is False
