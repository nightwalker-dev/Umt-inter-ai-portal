import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app, get_current_user

client = TestClient(app)

def override_user(role="admin", is_active=True, team_id=None, user_id="mock_id"):
    async def _override():
        return {"id": user_id, "role": role, "is_active": is_active, "must_change_password": False, "team_id": team_id}
    return _override

@patch("main.supabase.table")
def test_auth_07_role_checks_admin_only(mock_table):
    # Test POST /api/users
    app.dependency_overrides[get_current_user] = override_user(role="user")
    res = client.post("/api/users", headers={"Authorization": "Bearer fake"}, json={"email": "a", "full_name": "b", "role": "user", "team_id": "c"})
    assert res.status_code == 403

    app.dependency_overrides[get_current_user] = override_user(role="lead")
    res = client.post("/api/users", headers={"Authorization": "Bearer fake"}, json={"email": "a", "full_name": "b", "role": "user", "team_id": "c"})
    assert res.status_code == 403

    app.dependency_overrides.clear()
