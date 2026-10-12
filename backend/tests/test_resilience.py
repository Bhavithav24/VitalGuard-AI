from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from auth_helpers import authenticate_test_client


def valid_payload(index: int):
    return {
        "patient_id": f"DEMO-LOAD-{index:03d}",
        "age": 58,
        "heart_rate": 82 + (index % 5),
        "spo2": 98,
        "systolic_bp": 122,
        "diastolic_bp": 78,
        "temperature": 37.0,
        "respiratory_rate": 16,
    }


def patient_payload(index: int):
    return {
        "patient_id": f"DEMO-LOAD-{index:03d}",
        "external_identifier": f"VG-LOAD-{index:03d}",
        "display_name": f"Load Test Patient {index:03d}",
        "age": 58,
        "sex": "U",
        "unit": "Test Ward",
        "bed": f"T-{index:03d}",
    }


def ingestion_record(index: int, *, source_mode="historical_replay"):
    return {
        "source_system": "historical-replay",
        "source_mode": source_mode,
        "source_event_id": f"resilience-{index:03d}",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "observation": valid_payload(index),
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


def test_burst_predictions_fail_closed_and_history_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "burst.sqlite3"))
    with TestClient(app) as client:
        authenticate_test_client(client)
        results = [client.post("/api/v1/risk/predict", json=valid_payload(i)) for i in range(25)]
        assert all(response.status_code == 503 for response in results)

        page = client.get("/api/v1/observations", params={"limit": 10})
        assert page.status_code == 200
        assert page.json()["count"] == 0
        assert page.json()["next_before_id"] is None

        metrics = client.get("/api/v1/ops/metrics")
        assert metrics.status_code == 200
        assert metrics.json()["request_count"] >= 28


def test_observation_survives_application_restart(tmp_path, monkeypatch):
    db_path = tmp_path / "restart.sqlite3"
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(db_path))
    record = ingestion_record(77)

    with TestClient(app) as first_client:
        authenticate_test_client(first_client)
        created_patient = first_client.post("/api/v1/patients", json=patient_payload(77))
        assert created_patient.status_code == 201
        created = first_client.post("/api/v1/ingestion/batch", json={"records": [record]})
        assert created.status_code == 200
        assert created.json()["accepted"] == 1
        observation_id = created.json()["items"][0]["observation_id"]

    with TestClient(app) as restarted_client:
        authenticate_test_client(restarted_client)
        history = restarted_client.get(
            "/api/v1/observations",
            params={"patient_id": "DEMO-LOAD-077", "limit": 10},
        )
        assert history.status_code == 200
        assert history.json()["count"] == 1
        assert history.json()["items"][0]["id"] == observation_id
        assert history.json()["items"][0]["source_mode"] == "historical_replay"


def test_invalid_burst_does_not_create_observations(tmp_path, monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH", str(tmp_path / "invalid-burst.sqlite3"))
    with TestClient(app) as client:
        authenticate_test_client(client)
        invalid = ingestion_record(88)
        invalid["observation"]["spo2"] = 140
        responses = [client.post("/api/v1/ingestion/batch", json={"records": [invalid]}) for _ in range(10)]
        assert all(response.status_code == 200 for response in responses)
        assert all(response.json()["rejected"] == 1 for response in responses)
        history = client.get("/api/v1/observations", params={"limit": 10})
        assert history.status_code == 200
        assert history.json()["count"] == 0
