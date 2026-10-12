from fastapi.testclient import TestClient
from app.main import app
from auth_helpers import authenticate_test_client


def test_legacy_simulation_endpoint_is_removed(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "simulator.sqlite3"))
    with TestClient(app) as client:
        authenticate_test_client(client)
        response = client.post("/api/v1/demo/observations", json={"scenario":"stable","step":0})
    assert response.status_code == 404


def test_historical_replay_is_the_explicit_ingestion_path(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "replay.sqlite3"))
    with TestClient(app) as client:
        authenticate_test_client(client)
        response = client.post("/api/v1/ingestion/batch", json={"records":[{
            "source_system":"synthetic-demo","source_mode":"historical_replay","source_event_id":"replay-001",
            "observed_at":datetime.now(timezone.utc).isoformat(),
            "observation":{"patient_id":"DEMO-REPLAY-001","age":58,"heart_rate":82,"spo2":98,"systolic_bp":122,"diastolic_bp":78,"temperature":37,"respiratory_rate":16},
            "units":{"age":"years","heart_rate":"bpm","spo2":"percent","systolic_bp":"mmHg","diastolic_bp":"mmHg","temperature":"degC","respiratory_rate":"breaths/min"}}]})
    assert response.status_code == 200
    assert response.json()["accepted"] == 1
