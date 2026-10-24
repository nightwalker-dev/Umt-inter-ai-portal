import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_no_anon_access():
    # Attempting to access an endpoint that should be protected
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

def test_health_public_access():
    response = client.get("/api/health")
    assert response.status_code == 200

def test_cors_headers():
    response = client.options("/api/health", headers={"Origin": "http://malicious.com", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in response.headers or response.headers["access-control-allow-origin"] != "http://malicious.com"
