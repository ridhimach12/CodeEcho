from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CodeEcho"
    assert "docs" in data

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data

def test_validate_repo_valid():
    response = client.post(
        "/api/v1/validate-repo",
        json={"repo_url": "https://github.com/pallets/click"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["owner"] == "pallets"
    assert data["repo"] == "click"

def test_validate_repo_invalid():
    response = client.post(
        "/api/v1/validate-repo",
        json={"repo_url": "https://gitlab.com/not/github"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "supported" in data["message"].lower()
