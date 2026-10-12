from fastapi.testclient import TestClient

from app.main import app
from auth_helpers import authenticate_test_client


def _payload(patient_id: str = "PATIENT-TEST-001"):
    return {
        "patient_id": patient_id,
        "external_identifier": f"EXT-{patient_id}",
        "display_name": "Patient Test",
        "age": 42,
        "sex": "F",
        "unit": "Test Ward",
        "bed": "T-01",
    }


def test_patient_crud_and_list_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "patients.sqlite3"))
    with TestClient(app) as client:
        authenticate_test_client(client)
        created = client.post("/api/v1/patients", json=_payload())
        assert created.status_code == 201
        assert created.json()["patient_id"] == "PATIENT-TEST-001"
        assert created.json()["active"] is True

        listed = client.get("/api/v1/patients")
        assert listed.status_code == 200
        assert any(item["patient_id"] == "PATIENT-TEST-001" for item in listed.json())

        fetched = client.get("/api/v1/patients/PATIENT-TEST-001")
        assert fetched.status_code == 200

        updated = client.patch(
            "/api/v1/patients/PATIENT-TEST-001",
            json={"display_name": "Updated Patient", "bed": "T-02"},
        )
        assert updated.status_code == 200
        assert updated.json()["display_name"] == "Updated Patient"
        assert updated.json()["bed"] == "T-02"

        deactivated = client.post("/api/v1/patients/PATIENT-TEST-001/deactivate")
        assert deactivated.status_code == 200
        assert deactivated.json()["active"] is False

        active_only = client.get("/api/v1/patients")
        assert active_only.status_code == 200
        assert all(item["patient_id"] != "PATIENT-TEST-001" for item in active_only.json())

        history = client.get("/api/v1/patients", params={"active": "false"})
        assert history.status_code == 200
        assert any(item["patient_id"] == "PATIENT-TEST-001" for item in history.json())


def test_patient_identifier_conflicts_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "patient-conflicts.sqlite3"))
    with TestClient(app) as client:
        authenticate_test_client(client)
        assert client.post("/api/v1/patients", json=_payload("PATIENT-TEST-002")).status_code == 201
        duplicate_id = client.post("/api/v1/patients", json=_payload("PATIENT-TEST-002"))
        assert duplicate_id.status_code == 409

        duplicate_external = _payload("PATIENT-TEST-003")
        duplicate_external["external_identifier"] = "EXT-PATIENT-TEST-002"
        response = client.post("/api/v1/patients", json=duplicate_external)
        assert response.status_code == 409
