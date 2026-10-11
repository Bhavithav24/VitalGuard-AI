import os
import subprocess
import sys
import uuid

import pytest

from app.storage import initialize_storage, save_observation


@pytest.mark.postgres
def test_postgres_persists_across_processes():
    if not os.getenv("DATABASE_URL", "").startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        pytest.skip("PostgreSQL persistence test requires DATABASE_URL")

    initialize_storage()
    patient_id = f"DEMO-PERSIST-{uuid.uuid4().hex[:12]}"
    prediction = {
        "patient_id": patient_id,
        "risk_score": 42,
        "risk_level": "low",
        "model_probability": 0.42,
        "factors": {},
        "model_version": "persistence-test",
    }
    saved = save_observation(
        patient_id,
        {
            "age": 58,
            "heart_rate": 82,
            "spo2": 98,
            "systolic_bp": 122,
            "diastolic_bp": 78,
            "temperature": 37,
            "respiratory_rate": 16,
        },
        prediction,
    )

    code = """
import os
from app.storage import initialize_storage, list_observations
initialize_storage()
rows = list_observations(patient_id=os.environ["PERSIST_PATIENT_ID"], limit=10)
assert any(row["id"] == int(os.environ["PERSIST_OBSERVATION_ID"]) for row in rows)
"""
    env = os.environ.copy()
    env["PERSIST_PATIENT_ID"] = patient_id
    env["PERSIST_OBSERVATION_ID"] = str(saved["id"])
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
