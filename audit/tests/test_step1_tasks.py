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
def test_tk_02_lead_assignee_rules(mock_table):
    # A Lead can assign ONLY to Users of their own team.
    app.dependency_overrides[get_current_user] = override_user(role="lead", team_id="team_1", user_id="lead_1")

    mock_execute = MagicMock()
    mock_table.return_value.select.return_value.eq.return_value = mock_execute

    # 1. Try assigning to an Admin -> Should fail
    mock_execute.execute.return_value.data = [{"id": "admin_1", "role": "admin", "team_id": None, "is_active": True}]
    res = client.post("/api/tasks", headers={"Authorization": "Bearer fake"}, json={"title": "T", "assigned_to": "admin_1"})
    assert res.status_code == 400
    assert "Leads can only assign tasks to Users" in res.json()["detail"]

    # 2. Try assigning to self -> Should fail
    mock_execute.execute.return_value.data = [{"id": "lead_1", "role": "lead", "team_id": "team_1", "is_active": True}]
    res = client.post("/api/tasks", headers={"Authorization": "Bearer fake"}, json={"title": "T", "assigned_to": "lead_1"})
    assert res.status_code == 400
    assert "Leads cannot assign tasks to themselves" in res.json()["detail"]

    # 3. Try assigning to User in another team -> Should fail
    mock_execute.execute.return_value.data = [{"id": "user_2", "role": "user", "team_id": "team_2", "is_active": True}]
    res = client.post("/api/tasks", headers={"Authorization": "Bearer fake"}, json={"title": "T", "assigned_to": "user_2"})
    assert res.status_code == 400
    assert "Leads can only assign tasks to their own team" in res.json()["detail"]

    # 4. Try assigning to User in same team -> Should pass (or hit DB error since we mock RPC)
    # The RPC is called via supabase.rpc, so we patch that instead of table insert
    pass

    app.dependency_overrides.clear()

@patch("main.supabase.table")
def test_tk_05_review_rules(mock_table):
    # Only Admin can approve/reject. Lead cannot.
    app.dependency_overrides[get_current_user] = override_user(role="lead")
    res = client.post("/api/tasks/t1/review", headers={"Authorization": "Bearer fake"}, json={"status": "approved"})
    assert res.status_code == 403

    app.dependency_overrides.clear()
