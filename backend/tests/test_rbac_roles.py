import pytest
from fastapi.testclient import TestClient
from app.main import app

HASH="pbkdf2_sha256$210000$ODFe0akr--OGxcqsk4gygQ$aFcuHYhvwRSWs6cGLgrBAv931ThLm8x_knGymjIf7eY"
PASSWORD="VitalGuardDemo2026!"

def payload(patient_id="RBAC-001"):
    return {"patient_id":patient_id,"age":58,"heart_rate":82,"spo2":98,"systolic_bp":122,"diastolic_bp":78,"temperature":37.0,"respiratory_rate":16}

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv("VITALGUARD_DB_PATH",str(tmp_path/"rbac.sqlite3"))
    monkeypatch.setenv("VITALGUARD_AUTH_SECRET","test-only-secret-that-is-at-least-32-chars")
    monkeypatch.setenv("VITALGUARD_AUTH_USERS_JSON",
        '[{"username":"admin","password_hash":"%s","role":"admin","enabled":true,"patient_prefixes":["*"]},'
        '{"username":"clinician","password_hash":"%s","role":"clinician","enabled":true,"patient_prefixes":["RBAC-"]},'
        '{"username":"nurse","password_hash":"%s","role":"nurse","enabled":true,"patient_prefixes":["RBAC-"]}]' % (HASH,HASH,HASH))
    monkeypatch.delenv("VITALGUARD_AUTH_USERNAME",raising=False)
    monkeypatch.delenv("VITALGUARD_AUTH_PASSWORD",raising=False)
    with TestClient(app) as c:
        yield c

def token(client,username):
    r=client.post("/api/v1/auth/login",json={"username":username,"password":PASSWORD})
    assert r.status_code==200,r.text
    assert r.json()["role"]==username
    return r.json()["access_token"]

def test_all_three_roles_login_and_report_permissions(client):
    for role in ("admin","clinician","nurse"):
        t=token(client,role)
        r=client.get("/api/v1/auth/roles",headers={"Authorization":"Bearer "+t})
        assert r.status_code==200
        assert set(r.json()["roles"])=={"admin","clinician","nurse"}
        assert r.json()["current_role"]==role

def test_nurse_is_read_only_for_prediction_and_patient_mutation(client):
    t=token(client,"nurse"); h={"Authorization":"Bearer "+t}
    assert client.get("/api/v1/observations",headers=h).status_code==200
    assert client.post("/api/v1/risk/predict",json=payload(),headers=h).status_code==403
    assert client.post("/api/v1/patients",json={"patient_id":"RBAC-002","external_identifier":"EXT-002","display_name":"Patient","age":40,"sex":"F","unit":"ICU","bed":"2"},headers=h).status_code==403

def test_clinician_can_predict_and_manage_patients_but_not_users(client):
    t=token(client,"clinician"); h={"Authorization":"Bearer "+t}
    assert client.post("/api/v1/risk/predict",json=payload(),headers=h).status_code==200
    assert client.post("/api/v1/patients",json={"patient_id":"RBAC-003","external_identifier":"EXT-003","display_name":"Patient","age":40,"sex":"F","unit":"ICU","bed":"3"},headers=h).status_code==201
    assert client.get("/api/v1/auth/users",headers=h).status_code==403

def test_admin_can_manage_users(client):
    t=token(client,"admin")
    assert client.get("/api/v1/auth/users",headers={"Authorization":"Bearer "+t}).status_code==200
