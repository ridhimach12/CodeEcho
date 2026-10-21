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

def test_extract_features_endpoint():
    response = client.post(
        "/api/v1/extract-features",
        json={
            "deleted_code": "return val",
            "added_code": "if val is None:\n    raise ValueError('null val')\nreturn val",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "added_none_guard" in data["detected_shifts"]
    assert "added_explicit_raise" in data["detected_shifts"]
    assert data["embedding_dimension"] > 0
    assert len(data["vector_preview"]) == 5
