from fastapi.testclient import TestClient
import pytest
from app.main import app
from auth_helpers import authenticate_test_client

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "live.sqlite3"))
    with TestClient(app) as test_client:
        authenticate_test_client(test_client)
        yield test_client

def test_websocket_receives_observation_only_after_ingestion(client):
    ticket = client.post("/api/v1/auth/ws-ticket").json()["ticket"]
    with client.websocket_connect(f"/api/v1/live?ticket={ticket}") as websocket:
        connected = websocket.receive_json()
        assert connected["type"] == "connected"
        from datetime import datetime, timezone
        response = client.post("/api/v1/ingestion/batch", json={"records": [{
            "source_system": "synthetic-demo", "source_mode": "historical_replay", "source_event_id": "ws-event-001",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "observation": {"patient_id":"DEMO-WS-001","age":58,"heart_rate":82,"spo2":98,"systolic_bp":122,"diastolic_bp":78,"temperature":37,"respiratory_rate":16},
            "units": {"age":"years","heart_rate":"bpm","spo2":"percent","systolic_bp":"mmHg","diastolic_bp":"mmHg","temperature":"degC","respiratory_rate":"breaths/min"}}]})
        assert response.status_code == 200
        event = websocket.receive_json()
        assert event["type"] == "observation.created"
        assert event["event_id"] == response.json()["items"][0]["observation_id"]
        assert event["patient_id"] == "DEMO-WS-001"
        assert event["source_mode"] == "historical_replay"

def test_websocket_heartbeat(client):
    ticket = client.post("/api/v1/auth/ws-ticket").json()["ticket"]
    with client.websocket_connect(f"/api/v1/live?ticket={ticket}") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        websocket.send_text("ping")
        assert websocket.receive_json()["type"] == "pong"
