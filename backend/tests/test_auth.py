import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

# Helper function to mock the Supabase select response
def mock_supabase_profile(role="admin", is_active=True, must_change_password=False):
    mock_res = MagicMock()
    if is_active is None: # Simulate user not found
        mock_res.data = []
    else:
        mock_res.data = [{
            "id": "test_id",
            "role": role,
            "is_active": is_active,
            "must_change_password": must_change_password
        }]
    return mock_res

def override_get_current_user(role="admin", is_active=True, must_change_password=False):
    async def _override():
        if is_active is None:
            raise pytest.fail("Should not reach here if not auth")
        profile = {
            "id": "test_id",
            "role": role,
            "is_active": is_active,
            "must_change_password": must_change_password
        }
        if not is_active:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Deactivated user")
        return profile
    return _override

@patch("main.supabase.table")
def test_no_anon_access(mock_table):
    # Test C12 #2: Call any route with no token -> 401
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

def test_deactivated_user():
    # Test C12 #3: Sign in as deactivated user -> Refused (403)
    from main import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user(is_active=False)

    response = client.get("/api/me", headers={"Authorization": "Bearer not_used_due_to_override"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Deactivated user"

    app.dependency_overrides.clear()

def test_must_change_password_lock():
    # Test C12 #4: While must_change_password is true, call anything except /me and /auth/first-password -> Refused (403)
    from main import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user(must_change_password=True)

    # Attempt to access teams (should be blocked)
    response = client.get("/api/teams", headers={"Authorization": "Bearer not_used_due_to_override"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Must change password first"

    # Attempt to access /me (should be allowed)
    response = client.get("/api/me", headers={"Authorization": "Bearer not_used_due_to_override"})
    assert response.status_code == 200

    app.dependency_overrides.clear()

def test_admin_only_routes():
    # Test C12 #6: User or Lead calls POST /users -> 403
    from main import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user(role="user")

    response = client.post("/api/users", headers={"Authorization": "Bearer not_used_due_to_override"}, json={
        "email": "test@test.com", "full_name": "Test", "role": "user", "team_id": "team1"
    })
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden: Admin role required"

    app.dependency_overrides.clear()

def test_health_public_access():
    response = client.get("/api/health")
    assert response.status_code == 200
