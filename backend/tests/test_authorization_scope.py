import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from app.alert_service import create_alert
from app.live_events import LiveEventHub
from app.main import app


HASH = "pbkdf2_sha256$210000$ODFe0akr--OGxcqsk4gygQ$aFcuHYhvwRSWs6cGLgrBAv931ThLm8x_knGymjIf7eY"


@pytest.fixture
def scoped_client(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "scope.sqlite3"))
    monkeypatch.setenv("VITALGUARD_AUTH_SECRET", "test-only-secret-that-is-at-least-32-chars")
    monkeypatch.setenv(
        "VITALGUARD_AUTH_USERS_JSON",
        '[{"username":"scoped","password_hash":"%s","role":"clinician","enabled":true,"patient_prefixes":["DEMO-TEAM-A-"]}]'
        % HASH,
    )
    monkeypatch.delenv("VITALGUARD_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("VITALGUARD_AUTH_PASSWORD", raising=False)
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"username": "scoped", "password": "VitalGuardDemo2026!"})
        assert response.status_code == 200
        client.headers.update({"Authorization": "Bearer " + response.json()["access_token"]})
        yield client


def test_observation_quality_enforces_patient_scope(scoped_client):
    denied = scoped_client.get("/api/v1/observations/quality", params={"patient_id": "DEMO-OTHER-001"})
    assert denied.status_code == 403


def test_alert_actions_enforce_patient_scope(scoped_client):
    alert = create_alert(
        patient_id="DEMO-OTHER-001",
        event_key="scope-test-alert",
        severity="high",
        title="Scope test",
        details={"demo_only": True},
    )
    assert alert is not None
    response = scoped_client.post(f"/api/v1/alerts/{alert['id']}/acknowledge", json={})
    assert response.status_code == 403
    audit = scoped_client.get(f"/api/v1/alerts/{alert['id']}/audit")
    assert audit.status_code == 403


def test_escalation_preview_does_not_expose_out_of_scope_alerts(scoped_client):
    allowed = create_alert(
        patient_id="DEMO-TEAM-A-001",
        event_key="scope-test-allowed",
        severity="high",
        title="Allowed",
        details={"demo_only": True},
    )
    denied = create_alert(
        patient_id="DEMO-OTHER-002",
        event_key="scope-test-denied",
        severity="high",
        title="Denied",
        details={"demo_only": True},
    )
    assert allowed and denied
    response = scoped_client.get("/api/v1/alerts/escalation-preview")
    assert response.status_code == 200
    assert [item["alert_id"] for item in response.json()["items"]] == [allowed["id"]]


def test_realtime_events_are_filtered_by_patient_scope():
    class FakeWebSocket:
        def __init__(self):
            self.events = []

        async def send_json(self, event):
            self.events.append(event)

    async def scenario():
        hub = LiveEventHub()
        allowed = FakeWebSocket()
        hub._clients[allowed] = "DEMO-TEAM-A-"
        await hub.broadcast({"type": "observation.created", "patient_id": "DEMO-OTHER-001"})
        assert allowed.events == []
        await hub.broadcast({"type": "observation.created", "patient_id": "DEMO-TEAM-A-001"})
        assert len(allowed.events) == 1

    asyncio.run(scenario())


def test_unscoped_observation_history_is_filtered(scoped_client):
    allowed = scoped_client.post(
        "/api/v1/risk/predict",
        json={
            "patient_id": "DEMO-TEAM-A-001",
            "age": 58,
            "heart_rate": 82,
            "spo2": 98,
            "systolic_bp": 122,
            "diastolic_bp": 78,
            "temperature": 37,
            "respiratory_rate": 16,
        },
    )
    assert allowed.status_code == 200
    response = scoped_client.get("/api/v1/observations")
    assert response.status_code == 200
    assert all(item["patient_id"].startswith("DEMO-TEAM-A-") for item in response.json()["items"])


def test_unscoped_alert_listing_is_filtered(scoped_client):
    allowed = create_alert(
        patient_id="DEMO-TEAM-A-003",
        event_key="scope-test-list-allowed",
        severity="high",
        title="Allowed list alert",
        details={"demo_only": True},
    )
    denied = create_alert(
        patient_id="DEMO-OTHER-003",
        event_key="scope-test-list-denied",
        severity="high",
        title="Denied list alert",
        details={"demo_only": True},
    )
    assert allowed and denied
    response = scoped_client.get("/api/v1/alerts")
    assert response.status_code == 200
    assert all(item["patient_id"].startswith("DEMO-TEAM-A-") for item in response.json()["items"])
    assert denied["id"] not in [item["id"] for item in response.json()["items"]]
