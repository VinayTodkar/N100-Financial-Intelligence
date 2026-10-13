import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app, DB_PATH

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_company_list_endpoint():
    response = client.get("/api/companies?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 5


def test_company_profile_exists():
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT company_id FROM companies LIMIT 1"
        ).fetchone()
    assert row is not None
    response = client.get(f"/api/companies/{row[0]}/profile")
    assert response.status_code == 200
    assert response.json()["company_id"] == row[0]


def test_missing_company_returns_404():
    response = client.get("/api/companies/999999999/profile")
    assert response.status_code == 404


def test_market_cap_does_not_fabricate_values():
    response = client.get("/api/market-cap")
    assert response.status_code == 200
    data = response.json()
    if not data.get("available", True):
        assert data["data"] == []


def test_tearsheet_download_is_pdf():
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT company_id FROM companies LIMIT 1"
        ).fetchone()
    assert row is not None
    response = client.get(
        f"/api/companies/{row[0]}/tearsheet/download"
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")


def test_openapi_spec_has_api_paths():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/companies" in paths
    assert "/api/screener" in paths
