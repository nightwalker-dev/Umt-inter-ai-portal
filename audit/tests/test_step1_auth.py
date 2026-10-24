import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# This is a read-only audit. We are testing the API contract and authorization matrix.
from main import app, get_current_user, require_admin, get_guarded_user

client = TestClient(app)

def mock_override_get_current_user(role="admin", is_active=True, must_change_password=False, team_id=None, user_id="mock_id"):
    async def _override():
        if not is_active:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Deactivated user")
        return {"id": user_id, "role": role, "is_active": is_active, "must_change_password": must_change_password, "team_id": team_id}
    return _override

@patch("main.supabase")
def test_auth_02_signup_disabled(mock_supabase):
    # Direct signup call is refused (we check if there is an endpoint for it)
    # The app has POST /api/users, but that's admin only. There is no signup endpoint.
    res = client.post("/api/signup", json={"email": "test@test.com", "password": "password"})
    assert res.status_code == 404 # Endpoint doesn't exist

@patch("main.supabase")
def test_auth_04_first_login_forces_password(mock_supabase):
    app.dependency_overrides[get_current_user] = mock_override_get_current_user(must_change_password=True)

    # Should be locked
    res = client.get("/api/dashboard", headers={"Authorization": "Bearer fake"})
    assert res.status_code == 403
    assert "Must change password first" in res.json()["detail"]

    # Should be allowed
    res = client.get("/api/me", headers={"Authorization": "Bearer fake"})
    assert res.status_code == 200

    app.dependency_overrides.clear()
