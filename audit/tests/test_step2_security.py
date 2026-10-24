import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app, get_current_user, require_admin

client = TestClient(app)

def override_user(role="admin", user_id="mock_id", team_id=None, is_active=True):
    async def _override():
        if not is_active:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Deactivated user")
        return {"id": user_id, "role": role, "is_active": is_active, "must_change_password": False, "team_id": team_id}
    return _override

@patch("main.supabase.table")
def test_mass_assignment(mock_table):
    # Try to inject `role`, `is_active`, `must_change_password`, and `team_id` when editing a task
    app.dependency_overrides[get_current_user] = override_user(role="admin")

    mock_execute = MagicMock()
    # Mock finding the task
    mock_execute.execute.return_value.data = [{"id": "t1", "status": "pending", "assigned_by": "mock_id", "assigned_to": "u1"}]
    mock_table.return_value.select.return_value.eq.return_value = mock_execute

    # Try updating the task with massive injection
    res = client.patch("/api/tasks/t1", headers={"Authorization": "Bearer fake"}, json={
        "title": "New Title",
        "role": "admin", # Injected field
        "status": "approved", # Injected field
        "reviewed_by": "hacker", # Injected field
        "is_active": False # Injected field
    })

    assert res.status_code == 200
    # Because UpdateTaskRequest uses Pydantic's exclude_unset=True, extra fields are dropped.
    # We assert that the update method was called, but how can we ensure the injected fields were dropped?
    # By intercepting the mock call!
    mock_update = mock_table.return_value.update
    called_args, _ = mock_update.call_args
    update_dict = called_args[0]

    assert "title" in update_dict
    assert "role" not in update_dict
    assert "status" not in update_dict
    assert "reviewed_by" not in update_dict
    assert "is_active" not in update_dict

    app.dependency_overrides.clear()

@patch("main.supabase.table")
def test_idor_task_history(mock_table):
    # User tries to fetch history for a task assigned to someone else
    app.dependency_overrides[get_current_user] = override_user(role="user", user_id="hacker_id")

    mock_execute = MagicMock()
    # Mock finding the task, but assigned to victim_id
    mock_execute.execute.return_value.data = [{"id": "t1", "assigned_by": "admin", "assigned_to": "victim_id", "team_id": "teamA"}]
    mock_table.return_value.select.return_value.eq.return_value = mock_execute

    res = client.get("/api/tasks/t1/history", headers={"Authorization": "Bearer fake"})

    # Because it calls get_task() internally which scopes via assigned_to, it should 404 (Obfuscated)
    assert res.status_code == 404
    assert res.json()["detail"] == "Task not found"

    app.dependency_overrides.clear()
