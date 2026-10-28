import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.cli import bootstrap_admin, create_synthetic_fixtures, seed_default_environment

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    fixtures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../fixtures/synthetic-backups"))
    seed_default_environment(fixtures_dir)

def test_health_endpoints():
    r1 = client.get("/api/v1/health/live")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"

    r2 = client.get("/api/v1/health/ready")
    assert r2.status_code == 200
    assert r2.json()["status"] == "ready"

def test_auth_login_and_me():
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@sentinel.local", "password": "SentinelAdmin2026!"}
    )
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    assert token_data["role"] == "admin"

    # Test /me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@sentinel.local"

def test_sources_and_discovery():
    # Login
    auth_res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@sentinel.local", "password": "SentinelAdmin2026!"}
    )
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List sources
    sources_res = client.get("/api/v1/sources", headers=headers)
    assert sources_res.status_code == 200
    sources = sources_res.json()
    assert len(sources) >= 1
    source_id = sources[0]["id"]

    # Discover artifacts
    disc_res = client.post(f"/api/v1/sources/{source_id}/discover", headers=headers)
    assert disc_res.status_code == 200
    artifacts = disc_res.json()
    assert len(artifacts) >= 5

    # Trigger verification on valid_app_backup.zip
    valid_artifact = next(a for a in artifacts if a["file_name"] == "valid_app_backup.zip")
    verify_res = client.post(
        f"/api/v1/artifacts/{valid_artifact['id']}/verify",
        json={"job_type": "full"},
        headers=headers
    )
    assert verify_res.status_code == 200
    job = verify_res.json()
    assert job["status"] in ["verified", "verified_with_warnings"]
    assert len(job["results"]) >= 3
    assert len(job["recovery_tests"]) >= 1
    assert job["recovery_tests"][0]["status"] == "passed"

def test_tamper_evident_audit_log():
    auth_res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@sentinel.local", "password": "SentinelAdmin2026!"}
    )
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify audit chain integrity
    audit_res = client.get("/api/v1/audit/verify-chain", headers=headers)
    assert audit_res.status_code == 200
    assert audit_res.json()["status"] == "valid"
    assert audit_res.json()["total_records"] > 0
