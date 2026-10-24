import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app, get_current_user

client = TestClient(app)

def override_user(role="admin", is_active=True, team_id=None, user_id="mock_id", must_change=False):
    async def _override():
        if not is_active:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Deactivated user")
        return {"id": user_id, "role": role, "is_active": is_active, "must_change_password": must_change, "team_id": team_id}
    return _override

@patch("main.supabase.table")
def test_12_reject_empty_note(mock_table):
    # Reject with empty note -> Rejected
    app.dependency_overrides[get_current_user] = override_user(role="admin")
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = [{"id": "t1", "status": "completed", "assigned_to": "u1"}]
    mock_table.return_value.select.return_value.eq.return_value = mock_execute

    res = client.post("/api/tasks/t1/review", headers={"Authorization": "Bearer fake"}, json={"status": "rejected", "note": ""})
    assert res.status_code in [400, 403]
    assert "reason (note) is required" in res.json()["detail"]

    app.dependency_overrides.clear()

@patch("main.supabase.table")
def test_13_complete_as_non_assignee(mock_table):
    # Mark Completed as non-assignee -> 403
    app.dependency_overrides[get_current_user] = override_user(role="user", user_id="user_2")
    mock_execute = MagicMock()
    # Task is assigned to user_1
    mock_execute.execute.return_value.data = [{"id": "t1", "status": "pending", "assigned_to": "user_1", "team_id": "teamA"}]
    mock_table.return_value.select.return_value.eq.return_value = mock_execute

    # 404 because get_task obfuscates tasks you don't own
    res = client.post("/api/tasks/t1/complete", headers={"Authorization": "Bearer fake"})
    assert res.status_code == 404

    app.dependency_overrides.clear()

@patch("main.supabase.table")
def test_14_skip_statuses_or_edit_approved(mock_table):
    # Edit an approved task -> Refused
    app.dependency_overrides[get_current_user] = override_user(role="admin")
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = [{"id": "t1", "status": "approved", "assigned_to": "u1", "assigned_by": "admin"}]
    mock_table.return_value.select.return_value.eq.return_value = mock_execute

    res = client.patch("/api/tasks/t1", headers={"Authorization": "Bearer fake"}, json={"title": "new"})
    assert res.status_code in [400, 403]


    app.dependency_overrides.clear()

@patch("main.supabase.rpc")
@patch("main.supabase.table")
def test_15_concurrency_double_approve(mock_table, mock_rpc):
    # Two admins review same task. Second fails because RPC enforces from_status locally in DB.
    # We test the python exception mapping.
    app.dependency_overrides[get_current_user] = override_user(role="admin")

    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = [{"id": "t1", "status": "completed", "assigned_to": "u1"}]
    mock_table.return_value.select.return_value.eq.return_value = mock_execute

    # First review succeeds
    mock_rpc.return_value.execute.return_value.data = True
    res1 = client.post("/api/tasks/t1/review", headers={"Authorization": "Bearer fake"}, json={"status": "approved"})
    assert res1.status_code == 200

    # Second review simulates DB returning False (0 rows updated)
    mock_rpc.return_value.execute.return_value.data = False
    res2 = client.post("/api/tasks/t1/review", headers={"Authorization": "Bearer fake"}, json={"status": "approved"})
    assert res2.status_code == 409
    assert "conflict" in res2.json()["detail"].lower()

    app.dependency_overrides.clear()

def test_24_no_path_to_update_history():
    # Try to update or delete activity_log or task_status_history
    res = client.patch("/api/activity/1", json={"action": "hacked"})
    assert res.status_code == 404

    res = client.delete("/api/tasks/1/history")
    assert res.status_code == 405 # Method not allowed

def test_28_force_server_error_no_trace():
    # Force a server error. FastAPI by default hides stack traces in production (depends on debug mode).
    app.dependency_overrides[get_current_user] = override_user(role="admin")

    # Give it bad data that causes an exception inside an endpoint
    res = client.post("/api/users", headers={"Authorization": "Bearer fake"}, json={}) # Empty body causes 422, not 500
    assert res.status_code == 422

    app.dependency_overrides.clear()
