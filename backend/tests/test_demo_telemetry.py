from fastapi.testclient import TestClient

from app.demo_telemetry import _ensure_demo_patients
from app.main import app
from auth_helpers import authenticate_test_client


def test_demo_telemetry_does_not_reactivate_deactivated_patient(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "demo.sqlite3"))
    with TestClient(app) as client:
        authenticate_test_client(client)
        active = _ensure_demo_patients()
        assert active == {"DEMO-001", "DEMO-002", "DEMO-003", "DEMO-004"}

        response = client.post("/api/v1/patients/DEMO-001/deactivate")
        assert response.status_code == 200

        active_after = _ensure_demo_patients()
        assert "DEMO-001" not in active_after
        assert {"DEMO-002", "DEMO-003", "DEMO-004"} <= active_after
